"""
NVIDIA NIM LLM client for Blindfold BI.

- Talks to NVIDIA's OpenAI-compatible endpoint with a model chain taken from settings
  (NVIDIA_MODEL, then NVIDIA_FALLBACK_MODELS). No model IDs are invented here.
- Token-bucket rate limiting to stay inside the free-tier quota.
- Reasoning models: `reasoning_content` is never used as an answer. If the visible content is empty
  (the token budget was spent thinking), the same model is retried once with a larger budget.
- Real usage (model, tokens, queue wait) is reported back to the caller for the run events.
- The plain-text fallback is honest: it summarises the computed figures and says the AI writer is unavailable.
"""

import re
import time
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class TokenBucket:
    """Async token bucket rate limiter for external LLM calls."""

    def __init__(self, rate: float = 10.0, capacity: float = 60.0):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0, timeout: float = 10.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            async with self._lock:
                now = time.time()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

            await asyncio.sleep(0.25)
        return False


class LLMClient:
    """NVIDIA NIM chat client with model fallback and honest telemetry."""

    PLAN_MAX_TOKENS = 1200
    NARRATE_MAX_TOKENS = 3000

    def __init__(self):
        self.api_key = settings.NVIDIA_API_KEY
        self.base_url = settings.NVIDIA_BASE_URL
        self.primary_model = settings.NVIDIA_MODEL
        self.limiter = TokenBucket(rate=0.6, capacity=8.0)  # about 36 requests/minute, small burst
        self.client: Optional[AsyncOpenAI] = None

        if self.api_key and self.api_key.startswith("nvapi-"):
            self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key, timeout=45.0)

        self._planner_prompt = self._load_prompt("planner.md")
        self._narrator_prompt = self._load_prompt("narrator.md")

    # ------------------------------------------------------------------ plumbing
    def _load_prompt(self, filename: str) -> str:
        p = PROMPTS_DIR / filename
        return p.read_text(encoding="utf-8") if p.exists() else ""

    @property
    def models(self) -> List[str]:
        chain = [self.primary_model] + [m.strip() for m in (settings.NVIDIA_FALLBACK_MODELS or "").split(",")]
        seen: List[str] = []
        for m in chain:
            if m and m not in seen:
                seen.append(m)
        return seen

    async def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        usage: Optional[Dict[str, Any]],
        wait_timeout: float = 6.0,
    ) -> Optional[str]:
        """Try each model in the chain; return the visible text, or None if nothing usable came back."""
        if not self.client or settings.LLM_MODE == "off":
            return None

        t_wait = time.time()
        if not await self.limiter.acquire(1.0, timeout=wait_timeout):
            logger.warning("LLM rate limiter engaged; skipping LLM call.")
            if usage is not None:
                usage["error"] = "rate_limited"
            return None
        queue_ms = round((time.time() - t_wait) * 1000, 1)

        messages = [
            {"role": "system", "content": "Reasoning: low\n\n" + system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        last_error: Optional[str] = None
        for model in self.models:
            budget = max_tokens
            for attempt in (1, 2):
                t0 = time.time()
                try:
                    resp = await self.client.chat.completions.create(
                        model=model, messages=messages, temperature=temperature, max_tokens=budget
                    )
                except Exception as exc:  # unknown model, 429, network, auth
                    last_error = f"{model}: {type(exc).__name__}: {exc}"
                    logger.warning("LLM call failed (%s)", last_error)
                    break  # next model
                text = (resp.choices[0].message.content or "").strip()
                if usage is not None:
                    u = getattr(resp, "usage", None)
                    usage["model"] = model
                    usage["tokens_in"] = getattr(u, "prompt_tokens", 0) or 0
                    usage["tokens_out"] = getattr(u, "completion_tokens", 0) or 0
                    usage["queue_ms"] = queue_ms
                    usage["duration_ms"] = round((time.time() - t0) * 1000, 1)
                    usage["attempts"] = attempt
                if text:
                    return text
                budget *= 2  # reasoning consumed the whole budget: retry once with more room
        if usage is not None:
            usage["error"] = last_error or "empty_response"
        return None

    # ------------------------------------------------------------------ planning
    async def plan_query(self, anonymized_query: str, usage: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Ask the model which tool answers the question. Returns {"tool", "parameters", ...} or None."""
        raw = await self._chat(
            self._planner_prompt,
            f"User Question: {anonymized_query}\n\nRespond with valid JSON tool routing.",
            self.PLAN_MAX_TOKENS,
            0.0,
            usage,
            wait_timeout=3.0,
        )
        if not raw:
            return None
        candidate = raw
        if "```" in raw:
            parts = raw.split("```")
            if len(parts) >= 2:
                candidate = parts[1]
                if candidate.lstrip().lower().startswith("json"):
                    candidate = candidate.lstrip()[4:]
        match = re.search(r"\{.*\}", candidate, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) and "tool" in data else None

    # ------------------------------------------------------------------ narration
    @staticmethod
    def _scope_line(tool_data: Dict[str, Any]) -> str:
        facts = tool_data.get("facts", []) or []
        primary = next((f for f in facts if f.get("role") == "primary"), facts[0] if facts else {})
        dims = primary.get("dimensions") or {}
        parts: List[str] = []
        sector, period = dims.get("sector"), dims.get("period")
        if sector:
            label = str(sector).title()
            if str(sector).lower() == "energy":
                label += " (Renewables + Powerline)"
            parts.append(f"sector: {label}")
        if period:
            parts.append(f"period: {period}")
        as_of = (tool_data.get("audit") or {}).get("as_of_date")
        if as_of:
            parts.append(f"data as of {as_of}")
        return "; ".join(parts) or "whole company, all periods"

    @staticmethod
    def _facts_block(tool_data: Dict[str, Any]) -> str:
        lines = []
        for f in tool_data.get("facts", []) or []:
            role = f.get("role", "support")
            tag = {"primary": " [MAIN ANSWER]", "caveat": " [CAVEAT]"}.get(role, "")
            lines.append(f"- [[{f.get('id', '')}]] {f.get('label', '')} = {f.get('display', '')}{tag}")
        return "\n".join(lines) or "No facts were computed."

    async def narrate_tool_result(
        self,
        anonymized_query: str,
        tool_name: str,
        tool_data: Dict[str, Any],
        usage: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Write the answer in plain, friendly English from computed facts. Returns "" if the LLM is unavailable."""
        dq_lines = [
            f"- {d.get('rule_name')}: {d.get('description')}" for d in (tool_data.get("dq") or [])[:4]
        ]
        prompt = (
            f"The user asked: {anonymized_query}\n\n"
            f"Scope of these numbers: {self._scope_line(tool_data)}\n\n"
            f"Computed facts (cite them only as [[F#]]):\n{self._facts_block(tool_data)}\n\n"
            f"Data-quality notes that may affect how to read the numbers:\n"
            f"{chr(10).join(dq_lines) if dq_lines else '- none flagged'}\n\n"
            "Answer the user's question directly and conversationally, following your instructions."
        )
        text = await self._chat(self._narrator_prompt, prompt, self.NARRATE_MAX_TOKENS, 0.3, usage)
        return text or ""

    async def repair_narration(
        self,
        anonymized_query: str,
        draft_prose: str,
        offending_spans: List[str],
        tool_data: Dict[str, Any],
        usage: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """One targeted rewrite when the verifier found numbers that are not backed by a fact."""
        offending = "\n".join(f"- '{s}'" for s in offending_spans) or "- (none listed)"
        prompt = (
            f"The user asked: {anonymized_query}\n\n"
            f"Scope of these numbers: {self._scope_line(tool_data)}\n\n"
            f"Computed facts (cite them only as [[F#]]):\n{self._facts_block(tool_data)}\n\n"
            f"Your previous draft:\n{draft_prose}\n\n"
            f"These parts of it contained numbers that are not backed by a fact:\n{offending}\n\n"
            "Rewrite the answer so every number is a [[F#]] reference, keeping the same friendly, direct tone. "
            "Remove any claim you cannot support with a fact."
        )
        return await self._chat(self._narrator_prompt, prompt, self.NARRATE_MAX_TOKENS, 0.2, usage)

    # ------------------------------------------------------------------ honest fallback
    def _synthesize_local(self, tool_name: str, tool_data: Dict[str, Any]) -> str:
        """
        Used only when the AI writer is unavailable. Plain summary of the computed figures, no boilerplate advice.
        """
        facts = [f for f in (tool_data.get("facts") or []) if isinstance(f, dict)]
        by_id = {f.get("id"): f.get("display") for f in facts}
        template = tool_data.get("template", "") or ""
        for fid, disp in by_id.items():
            template = template.replace(f"[[{fid}]]", str(disp))

        scope = self._scope_line(tool_data)
        lines: List[str] = []
        lines.append(template.strip() or "Here are the figures I computed.")
        lines.append(f"(Scope: {scope}.)")

        support = [f for f in facts if f.get("role") == "support"][:5]
        if support:
            lines.append("What's behind it:\n" + "\n".join(f"- {f['label']}: {f['display']}" for f in support))

        caveats = [f for f in facts if f.get("role") == "caveat" and str(f.get("value") or 0) not in ("0", "0.0")]
        dq = (tool_data.get("dq") or [])[:3]
        notes = [f"- {f['label']}: {f['display']}" for f in caveats] + [f"- {d.get('description')}" for d in dq]
        if notes:
            lines.append("Worth knowing:\n" + "\n".join(notes))

        lines.append("(The AI writer isn't available right now, so this is a plain summary of the computed figures.)")
        return "\n\n".join(lines)

    # Legacy compatibility wrapper
    async def generate_response(self, user_query: str, tool_name: str, tool_data: Dict[str, Any]) -> str:
        text = await self.narrate_tool_result(user_query, tool_name, tool_data)
        return text or self._synthesize_local(tool_name, tool_data)


llm_client = LLMClient()
