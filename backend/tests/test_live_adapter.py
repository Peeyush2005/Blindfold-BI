"""
Proves the live monday.com path end to end, without network access:
a fake monday.com GraphQL server (built from the sample workbooks in the exact shape monday returns:
column ids + titles, `text`/`value` cells, cursor pagination) feeds the real adapter, normalizers, DuckDB
and tools. Then an item is edited "in monday" and the answer must change.
"""
import json
import re

import httpx
import pandas as pd
import pytest

from app.config import settings
from app.data.adapter import DEALS_HEADERS, DEALS_NUMERIC, DataAdapter, WO_HEADERS, WO_NUMERIC
from app.data.duckdb_store import duckdb_store
from app.data.monday_client import MondayClient
from app.tools.registry import registry

PAGE = 100  # force pagination regardless of the page size the client asks for


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:30]


def _to_text(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return ""
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    return str(v)


def _board_from_frame(board_id: str, name: str, df: pd.DataFrame, numeric: list) -> dict:
    headers = list(df.columns)
    name_header, other = headers[0], headers[1:]
    columns = [{"id": "name", "title": "Name", "type": "name"}]
    for h in other:
        columns.append({"id": _slug(h) + f"_{other.index(h)}", "title": h, "type": "numbers" if h in numeric else "text"})
    items = []
    for i, (_, row) in enumerate(df.iterrows()):
        cvs = []
        for idx, h in enumerate(other):
            text = _to_text(row[h])
            ctype = "numbers" if h in numeric else "text"
            cvs.append({
                "id": _slug(h) + f"_{idx}", "type": ctype, "text": text,
                "value": json.dumps(text) if (ctype == "numbers" and text != "") else None,
            })
        items.append({"id": str(1000 + i), "name": _to_text(row[name_header]), "column_values": cvs})
    return {"id": board_id, "name": name, "columns": columns, "items": items}


class FakeMonday:
    """A tiny in-memory monday.com GraphQL server."""

    def __init__(self, deals_raw: pd.DataFrame, wo_raw: pd.DataFrame):
        self.boards = {
            "111": _board_from_frame("111", "Deals", deals_raw, DEALS_NUMERIC),
            "222": _board_from_frame("222", "Work Orders", wo_raw, WO_NUMERIC),
        }
        self.calls = 0
        self.fail_with: str | None = None
        self.drop_column_title: str | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        body = json.loads(request.content)
        query, variables = body["query"], body.get("variables", {})
        assert "mutation" not in query.lower()  # the app must be strictly read-only
        if self.fail_with:
            return httpx.Response(200, json={"errors": [{"message": self.fail_with}]})
        if "next_items_page" in query:
            board_id, offset = variables["cursor"].split(":")
            board = self.boards[board_id]
            start = int(offset)
            chunk = board["items"][start:start + PAGE]
            nxt = f"{board_id}:{start + PAGE}" if start + PAGE < len(board["items"]) else None
            return httpx.Response(200, json={"data": {"next_items_page": {"cursor": nxt, "items": chunk}}})
        board_id = variables["ids"][0]
        board = self.boards.get(board_id)
        if board is None:
            return httpx.Response(200, json={"data": {"boards": []}})
        columns = [c for c in board["columns"] if c["title"] != self.drop_column_title]
        first = board["items"][:PAGE]
        nxt = f"{board_id}:{PAGE}" if len(board["items"]) > PAGE else None
        return httpx.Response(200, json={"data": {"boards": [{
            "id": board["id"], "name": board["name"], "columns": columns,
            "items_page": {"cursor": nxt, "items": first},
        }]}})

    def set_cell(self, board_id: str, item_index: int, title: str, text: str):
        board = self.boards[board_id]
        col = next(c for c in board["columns"] if c["title"] == title)
        for cv in board["items"][item_index]["column_values"]:
            if cv["id"] == col["id"]:
                cv["text"] = text


@pytest.fixture(scope="module")
def raw_frames():
    deals = pd.read_excel(settings.DEALS_EXCEL_PATH, sheet_name=0)
    wo = pd.read_excel(settings.WO_EXCEL_PATH, header=1)
    wo.columns = [str(c).strip() for c in wo.columns]
    return deals, wo


@pytest.fixture
def fake(raw_frames):
    return FakeMonday(*raw_frames)


@pytest.fixture
def adapter_live(fake):
    client = MondayClient(
        api_token="test-token", transport=httpx.MockTransport(fake.handler),
        deals_board_id="111", wo_board_id="222",
    )
    yield DataAdapter(client=client)
    duckdb_store.initialize(force_refresh=True)  # restore the fixture-backed store for other tests


def _open_pipeline():
    r = registry.execute_tool("pipeline_summary", {}).model_dump()
    facts = {f["id"]: f for f in r["facts"]}
    return facts["F1"]["value"], facts["F2"]["value"]


@pytest.mark.anyio
async def test_live_fetch_matches_the_workbook_numbers(adapter_live, fake):
    status = await adapter_live.refresh(force=True)
    assert status["source"] == "monday.com" and status["connected"] is True
    assert status["deals_count"] == 332 and status["work_orders_count"] == 176
    stats = status["stats"]
    assert stats["rows"]["deals_raw"] == 346 and stats["rows"]["deals_removed"] == 14
    assert stats["boards"]["deals"]["pages"] == 4          # 346 items / 100 per page: pagination really ran
    assert stats["boards"]["work_orders"]["pages"] == 2
    value, count = _open_pipeline()
    assert count == 49 and round(value / 1e7, 2) == 68.82


@pytest.mark.anyio
async def test_editing_monday_changes_the_answer(adapter_live, fake):
    await adapter_live.refresh(force=True)
    before_value, before_count = _open_pipeline()

    deals = fake.boards["111"]["items"]
    status_col = next(c for c in fake.boards["111"]["columns"] if c["title"] == "Deal Status")
    idx = next(
        i for i, it in enumerate(deals)
        if any(cv["id"] == status_col["id"] and cv["text"] == "Open" for cv in it["column_values"])
    )
    fake.set_cell("111", idx, "Deal Status", "Dead")           # someone edits the deal in monday.com

    await adapter_live.refresh(force=True)
    after_value, after_count = _open_pipeline()
    assert after_count == before_count - 1
    assert after_value <= before_value


@pytest.mark.anyio
async def test_failed_refresh_keeps_last_good_data_and_says_so(adapter_live, fake):
    await adapter_live.refresh(force=True)
    fake.fail_with = "Not Authenticated"
    status = await adapter_live.refresh(force=True)
    assert status["source"] == "stale_snapshot" and status["is_stale"] is True
    assert "Not Authenticated" in status["error"]
    assert status["has_data"] is True


@pytest.mark.anyio
async def test_no_silent_fallback_when_monday_is_down(monkeypatch, fake):
    monkeypatch.setattr(settings, "ALLOW_FIXTURE_FALLBACK", False)
    fake.fail_with = "Not Authenticated"
    client = MondayClient(api_token="bad", transport=httpx.MockTransport(fake.handler), deals_board_id="111", wo_board_id="222")
    adapter = DataAdapter(client=client)
    status = await adapter.refresh(force=True)
    assert status["source"] == "unavailable" and status["connected"] is False and status["has_data"] is False
    assert "Not Authenticated" in status["error"]


@pytest.mark.anyio
async def test_missing_required_column_is_reported_clearly(monkeypatch, fake):
    monkeypatch.setattr(settings, "ALLOW_FIXTURE_FALLBACK", False)
    fake.drop_column_title = "Deal Status"
    client = MondayClient(api_token="t", transport=httpx.MockTransport(fake.handler), deals_board_id="111", wo_board_id="222")
    adapter = DataAdapter(client=client)
    status = await adapter.refresh(force=True)
    assert status["has_data"] is False
    assert "Deal Status" in status["error"] and "missing required columns" in status["error"]


@pytest.mark.anyio
async def test_unknown_board_id_is_reported_clearly(monkeypatch, fake):
    monkeypatch.setattr(settings, "ALLOW_FIXTURE_FALLBACK", False)
    client = MondayClient(api_token="t", transport=httpx.MockTransport(fake.handler), deals_board_id="999", wo_board_id="222")
    status = await DataAdapter(client=client).refresh(force=True)
    assert status["has_data"] is False and "not found" in status["error"]
