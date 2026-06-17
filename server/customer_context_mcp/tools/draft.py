"""draft_customer_message tool."""

from __future__ import annotations

from ..llm import LLMUnavailable, draft_message
from ..store import STORE


def draft_customer_message(brief_id: str, purpose: str) -> dict:
    brief = STORE.get_brief(brief_id)
    if brief is None:
        return {"error": f"brief not found: {brief_id}"}
    try:
        text = draft_message(
            purpose=purpose,
            brief_json=brief.model_dump(),
            evidence=brief.evidence,
        )
    except LLMUnavailable as e:
        return {"brief_id": brief_id, "purpose": purpose, "error": str(e)}
    return {"brief_id": brief_id, "purpose": purpose, "draft": text}
