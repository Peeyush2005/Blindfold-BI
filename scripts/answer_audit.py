#!/usr/bin/env python3
"""
Blindfold BI - Answer Quality & Diversity Audit (Step 0 & Step 6)
Sends the 30 questions in evals/questions.yaml to the API and prints:
  - Table: Question | Tool + Args | Primary Fact | Narration Source | First Sentence
  - Summary KPIs:
      1. Template Rate (% narration_source == "template")
      2. Distinct (tool, args) count
      3. Pairs of different questions that produced identical answers
"""

import sys
import os
import re
import json
import yaml
import httpx
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
backend_dir = PROJECT_ROOT / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
DEFAULT_QUESTIONS_PATH = PROJECT_ROOT / "evals" / "questions.yaml"


def clean_first_sentence(text: str) -> str:
    """Extract clean first narrative sentence, stripping markdown headers and section preambles."""
    if not text:
        return "N/A"
    lines = text.strip().split("\n")
    prose_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            cleaned = re.sub(r"^#+\s*", "", stripped).strip()
            # If after stripping '#' it was just a label like 'Direct Answer', skip it
            if cleaned.lower() in ["direct answer", "answer", "executive summary", "key takeaways", "overview"]:
                continue
            cleaned = re.sub(r"^(?:direct answer|answer|executive summary|key takeaways)[\s:\-]+", "", cleaned, flags=re.IGNORECASE).strip()
            if cleaned:
                prose_lines.append(cleaned)
        elif stripped.startswith("**"):
            cleaned = re.sub(r"^\*{1,3}[^\*]+\*{1,3}\s*[:\-]?\s*", "", stripped).strip()
            if cleaned.lower() in ["direct answer", "answer", "executive summary", "key takeaways", "overview"]:
                continue
            cleaned = re.sub(r"^(?:direct answer|answer|executive summary|key takeaways)[\s:\-]+", "", cleaned, flags=re.IGNORECASE).strip()
            if cleaned:
                prose_lines.append(cleaned)
        else:
            cleaned = re.sub(r"^(?:direct answer|answer|executive summary|key takeaways)[\s:\-]+", "", stripped, flags=re.IGNORECASE).strip()
            if cleaned:
                prose_lines.append(cleaned)

    full_prose = " ".join(prose_lines)
    if not full_prose:
        full_prose = text.replace("\n", " ").strip()

    # Split on first sentence boundary (. followed by space or end)
    match = re.search(r"^(.*?[.!?])(?:\s|$)", full_prose)
    if match:
        return match.group(1).strip()
    return full_prose[:120].strip()


def run_sse_query(client: httpx.Client, api_url: str, question: str, session_id: str) -> Dict[str, Any]:
    """Execute streaming query and collect tool execution and answer data."""
    if api_url in ["inproc", "local"]:
        endpoint = "/api/v1/chat"
    else:
        endpoint = f"{api_url.rstrip('/')}/api/v1/chat"
    payload = {"question": question, "session_id": session_id}

    tools_called: List[Dict[str, Any]] = []
    answer_payload: Optional[Dict[str, Any]] = None
    llm_events: List[Dict[str, Any]] = []

    try:
        with client.stream("POST", endpoint, json=payload, timeout=60.0) as response:
            if response.status_code != 200:
                return {
                    "error": f"HTTP {response.status_code}",
                    "tool": "None",
                    "args": {},
                    "primary_fact": "N/A",
                    "source": "error",
                    "first_sentence": f"API Error HTTP {response.status_code}: {response.read().decode('utf-8')[:80]}",
                    "full_answer": "",
                }

            current_event = None
            for line in response.iter_lines():
                line = line.strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    current_event = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    if current_event == "tool":
                        tools_called.append(data)
                    elif current_event == "llm":
                        llm_events.append(data)
                    elif current_event == "answer":
                        answer_payload = data
    except Exception as exc:
        return {
            "error": str(exc),
            "tool": "None",
            "args": {},
            "primary_fact": "N/A",
            "source": "exception",
            "first_sentence": f"Connection Exception: {str(exc)[:80]}",
            "full_answer": "",
        }

    # Extract Tool & Args
    tool_name = "None"
    tool_args: Dict[str, Any] = {}
    if tools_called:
        primary_tool = tools_called[0]
        tool_name = primary_tool.get("name", "unknown")
        tool_args = primary_tool.get("args", {})
    elif answer_payload and "receipt" in answer_payload:
        tool_name = answer_payload["receipt"].get("query_executed", "SELECT")
        tool_args = answer_payload["receipt"].get("parameters", {})

    # Extract Blocks & Primary Fact
    primary_fact = "N/A"
    full_answer = ""
    source = "template"
    if answer_payload:
        receipt = answer_payload.get("receipt", {})
        source = receipt.get("narration_source", "template")

        blocks = answer_payload.get("blocks", [])
        for block in blocks:
            kind = block.get("kind")
            if kind == "text" and not full_answer:
                full_answer = block.get("content", "")
            elif kind == "kpi" and primary_fact == "N/A":
                label = block.get("label", "Metric")
                display = block.get("display", str(block.get("value", "")))
                primary_fact = f"{label}: {display}"
            elif kind == "table" and primary_fact == "N/A":
                rows = block.get("rows", [])
                cols = block.get("columns", [])
                if rows and cols:
                    primary_fact = f"Table({cols[0]}={rows[0][0]})"

    first_sentence = clean_first_sentence(full_answer)

    return {
        "tool": tool_name,
        "args": tool_args,
        "primary_fact": primary_fact,
        "source": source,
        "first_sentence": first_sentence,
        "full_answer": full_answer,
    }


def main():
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    questions_file = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_QUESTIONS_PATH

    if not questions_file.exists():
        backend_q = PROJECT_ROOT / "backend" / "evals" / "questions.yaml"
        if backend_q.exists():
            questions_file = backend_q
        else:
            print(f"Error: Questions file not found at {questions_file}")
            sys.exit(1)

    with open(questions_file, "r") as f:
        config = yaml.safe_load(f)

    questions = config.get("questions", [])
    if not questions:
        print(f"Error: No questions found in {questions_file}")
        sys.exit(1)

    print(f"\n==========================================================================================", flush=True)
    print(f" BLINDFOLD BI: ANSWER AUDIT (Target: {api_url} | Total Questions: {len(questions)})", flush=True)
    print(f"==========================================================================================\n", flush=True)

    results: List[Dict[str, Any]] = []
    distinct_tool_args = set()
    answers_by_question: Dict[str, str] = {}
    template_count = 0

    session_id = "audit_session_main"

    col_fmt = "{:<3} | {:<32} | {:<28} | {:<22} | {:<10} | {:<40}"
    header = col_fmt.format("#", "Question", "Tool + Key Args", "Primary Fact", "Source", "First Sentence")
    separator = "-" * len(header)
    print(header, flush=True)
    print(separator, flush=True)

    if api_url in ["inproc", "local"]:
        from starlette.testclient import TestClient
        from app.main import app
        from app.data.db import db
        from app.data.adapter import adapter
        from app.core.orchestrator import orchestrator
        db.init_db()
        adapter.load_data()
        orchestrator.init_catalog()
        client_cm = TestClient(app)
    else:
        client_cm = httpx.Client()

    with client_cm as client:
        for idx, q_item in enumerate(questions, 1):
            q_text = q_item["question"]
            is_inherited = q_item.get("context_inherited", False)
            if not is_inherited:
                session_id = f"audit_sess_{idx:02d}"

            res = run_sse_query(client, api_url, q_text, session_id)
            res["id"] = q_item.get("id", f"Q{idx:02d}")
            res["question"] = q_text
            results.append(res)

            # Metrics collection
            if res["source"] == "template":
                template_count += 1

            # Format tool + args for set
            args_serialized = json.dumps(res["args"], sort_keys=True)
            distinct_tool_args.add((res["tool"], args_serialized))

            answers_by_question[q_text] = res["full_answer"].strip()

            # Truncate for pretty table printing
            q_disp = (q_text[:29] + "...") if len(q_text) > 32 else q_text
            tool_disp = f"{res['tool']}({args_serialized})"
            if len(tool_disp) > 28:
                tool_disp = tool_disp[:25] + "..."
            fact_disp = (res['primary_fact'][:19] + "...") if len(res['primary_fact']) > 22 else res['primary_fact']
            first_sent_disp = (res['first_sentence'][:37] + "...") if len(res['first_sentence']) > 40 else res['first_sentence']

            print(col_fmt.format(idx, q_disp, tool_disp, fact_disp, res['source'], first_sent_disp), flush=True)

    # Detect identical answers for different questions
    identical_pairs: List[Tuple[str, str]] = []
    q_list = list(answers_by_question.keys())
    for i in range(len(q_list)):
        for j in range(i + 1, len(q_list)):
            q1, q2 = q_list[i], q_list[j]
            ans1, ans2 = answers_by_question[q1], answers_by_question[q2]
            if ans1 and ans2 and ans1 == ans2:
                identical_pairs.append((q1, q2))

    total_q = len(questions)
    template_rate = (template_count / total_q) * 100.0 if total_q > 0 else 0.0

    print(separator)
    print("\n==========================================================================================")
    print(" SUMMARY METRICS & QUALITY AUDIT REPORT")
    print("==========================================================================================")
    print(f"  1. Total Questions Audited          : {total_q}")
    print(f"  2. Template Rate                    : {template_rate:.1f}% ({template_count}/{total_q}) (Target: < 10% live)")
    print(f"  3. Distinct (Tool, Args) Pairs      : {len(distinct_tool_args)}")
    print(f"  4. Identical Answer Pairs           : {len(identical_pairs)} (Target: 0)")

    if identical_pairs:
        print("\n  [!] Identical Answer Pairs Detected:")
        for p1, p2 in identical_pairs[:5]:
            print(f"      - '{p1}' == '{p2}'")
        if len(identical_pairs) > 5:
            print(f"      ... and {len(identical_pairs) - 5} more.")
    else:
        print("  [✓] Zero identical answers across different questions!")

    print("==========================================================================================\n")

    # Exit code: 0 if 0 identical pairs
    if len(identical_pairs) > 0:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
