"""ask_meeting_brief tool."""

from __future__ import annotations

from ..llm import LLMUnavailable, answer_question
from ..store import STORE
from ..types import Source


def ask_meeting_brief(
    brief_id: str,
    question: str,
    evidence_scope: list[Source] | None = None,
) -> dict:
    brief = STORE.get_brief(brief_id)
    if brief is None:
        return {"error": f"brief not found: {brief_id}"}

    evidence = brief.evidence
    if evidence_scope:
        scope = set(evidence_scope)
        evidence = [e for e in evidence if e.source in scope]

    try:
        answer = answer_question(
            question=question,
            brief_json=brief.model_dump(),
            evidence=evidence,
        )
    except LLMUnavailable as e:
        return {"brief_id": brief_id, "question": question, "error": str(e)}

    return {
        "brief_id": brief_id,
        "question": question,
        "answer": answer,
        "evidence_ids": [e.id for e in evidence],
    }
