"""Claude-based news sentiment + regime judgment.

Kept light-touch: if the API key is missing, returns a neutral fallback so the
main loop never blocks on LLM outages.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..config import settings
from ..utils.logger import logger

SYSTEM_PROMPT = (
    "You are a macro crypto analyst. Given recent headlines, return strict JSON: "
    '{"sentiment": -1..1, "regime": "BULL|BEAR|RANGE|UNCERTAIN", '
    '"confidence": 0..1, "reasoning": "<=40 words"}. '
    "Do not editorialize. Do not add text outside JSON."
)


@dataclass
class LLMJudgement:
    sentiment: float
    regime: str
    confidence: float
    reasoning: str


def neutral() -> LLMJudgement:
    return LLMJudgement(0.0, "UNCERTAIN", 0.0, "llm unavailable")


async def judge_from_headlines(headlines: list[str]) -> LLMJudgement:
    if not settings.anthropic_api_key or not headlines:
        return neutral()
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        joined = "\n".join(f"- {h}" for h in headlines[:30])
        resp = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": joined}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        payload = json.loads(text)
        return LLMJudgement(
            sentiment=float(payload.get("sentiment", 0)),
            regime=str(payload.get("regime", "UNCERTAIN")),
            confidence=float(payload.get("confidence", 0)),
            reasoning=str(payload.get("reasoning", ""))[:160],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"LLM judge failed, falling back neutral: {exc}")
        return neutral()
