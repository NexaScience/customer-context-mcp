"""LLM helpers — Anthropic-backed brief generation and Q&A."""

from __future__ import annotations

import json
import logging
from typing import Any

from .config import CONFIG
from .types import Evidence

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    pass


def _client():
    if not CONFIG.anthropic_api_key:
        raise LLMUnavailable("ANTHROPIC_API_KEY is not set")
    try:
        import anthropic  # type: ignore
    except ImportError as e:
        raise LLMUnavailable(f"anthropic package not installed: {e}") from e
    return anthropic.Anthropic(api_key=CONFIG.anthropic_api_key)


def _evidence_block(evidence: list[Evidence]) -> str:
    lines: list[str] = []
    for e in evidence:
        lines.append(
            f"- [{e.id}] ({e.source}) {e.title}"
            + (f" — {e.timestamp}" if e.timestamp else "")
            + f"\n  {e.excerpt}"
        )
    return "\n".join(lines) or "(no evidence)"


BRIEF_SYSTEM = (
    "You are a sales / CS analyst. Given evidence retrieved from Notion, Slack and Google "
    "Drive about a single customer, you must produce a structured meeting-prep brief in "
    "JSON. Every risk, opportunity, action and timeline entry must cite evidence_ids that "
    "exist in the provided evidence list. If a section has no support in the evidence, "
    "return an empty list rather than fabricating. Respond with JSON only — no prose."
)

BRIEF_SCHEMA_HINT = {
    "summary": "string (3-4 sentences, executive summary)",
    "meeting_objective": "string",
    "risk_level": "high | medium | low",
    "key_topics": [
        {"title": "string", "sources": ["notion|slack|google_drive", "..."]}
    ],
    "risks": [
        {"title": "string", "severity": "high|medium|low", "evidence_ids": ["..."]}
    ],
    "opportunities": [{"title": "string", "evidence_ids": ["..."]}],
    "suggested_questions": [{"text": "string", "rationale": "string"}],
    "recommended_actions": [{"title": "string", "owner": "string|null"}],
    "timeline": [
        {
            "date": "YYYY-MM-DD",
            "source": "notion|slack|google_drive",
            "title": "string",
            "summary": "string",
            "evidence_id": "string",
        }
    ],
}


def generate_brief_json(
    customer_name: str,
    aliases: list[str],
    meeting_date: str | None,
    objective: str | None,
    evidence: list[Evidence],
) -> dict[str, Any]:
    client = _client()
    user = (
        f"Customer: {customer_name}\n"
        f"Aliases: {', '.join(aliases) if aliases else '(none)'}\n"
        f"Meeting date: {meeting_date or '(unspecified)'}\n"
        f"Meeting objective: {objective or '(unspecified)'}\n\n"
        f"Evidence (use these evidence_ids when citing):\n{_evidence_block(evidence)}\n\n"
        f"Return JSON with this shape:\n{json.dumps(BRIEF_SCHEMA_HINT, indent=2)}"
    )
    msg = client.messages.create(
        model=CONFIG.anthropic_model,
        max_tokens=4000,
        system=BRIEF_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return _parse_json(text)


QA_SYSTEM = (
    "You are answering follow-up questions about a customer meeting brief. Use only the "
    "supplied evidence to answer. If the answer cannot be supported by the evidence, say "
    "so. Be concise and cite evidence_ids inline as [id]."
)


def answer_question(question: str, brief_json: dict[str, Any], evidence: list[Evidence]) -> str:
    client = _client()
    user = (
        f"Brief summary: {brief_json.get('summary', '')}\n"
        f"Objective: {brief_json.get('meeting_objective', '')}\n\n"
        f"Evidence:\n{_evidence_block(evidence)}\n\n"
        f"Question: {question}"
    )
    msg = client.messages.create(
        model=CONFIG.anthropic_model,
        max_tokens=1024,
        system=QA_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


DRAFT_SYSTEM = (
    "You are drafting professional, concise customer-facing or internal messages from a "
    "meeting brief. Use only facts supported by the evidence. Match the requested purpose. "
    "Return the message body only — no preamble."
)

PURPOSE_INSTRUCTIONS = {
    "follow_up_email": (
        "Draft a follow-up email (subject line + body) to send to the customer after the "
        "meeting summarising agreed next steps and open items."
    ),
    "internal_slack_summary": (
        "Draft a short internal Slack message (Japanese OK if context suggests it) "
        "summarising customer status, top risks, and next actions for the account team."
    ),
    "meeting_agenda": (
        "Draft a numbered meeting agenda covering the objective, key topics, open "
        "questions, and decision items."
    ),
}


def draft_message(
    purpose: str, brief_json: dict[str, Any], evidence: list[Evidence]
) -> str:
    client = _client()
    purpose_clean = purpose if purpose in PURPOSE_INSTRUCTIONS else "follow_up_email"
    instruction = PURPOSE_INSTRUCTIONS[purpose_clean]
    user = (
        f"Purpose: {purpose_clean}\n"
        f"Instruction: {instruction}\n\n"
        f"Summary: {brief_json.get('summary', '')}\n"
        f"Objective: {brief_json.get('meeting_objective', '')}\n"
        f"Risks: {json.dumps(brief_json.get('risks', []), ensure_ascii=False)}\n"
        f"Actions: {json.dumps(brief_json.get('recommended_actions', []), ensure_ascii=False)}\n"
        f"Opportunities: {json.dumps(brief_json.get('opportunities', []), ensure_ascii=False)}\n\n"
        f"Evidence:\n{_evidence_block(evidence)}"
    )
    msg = client.messages.create(
        model=CONFIG.anthropic_model,
        max_tokens=1500,
        system=DRAFT_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
