"""generate_meeting_brief tool."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from ..llm import LLMUnavailable, generate_brief_json
from ..store import STORE
from ..types import (
    Action,
    Evidence,
    KeyTopic,
    MeetingBrief,
    Opportunity,
    Period,
    Question,
    Risk,
    Severity,
    TimelineEvent,
)
from .search import search_customer_context

log = logging.getLogger(__name__)


def _evidence_lookup(evidence: list[Evidence]) -> dict[str, Evidence]:
    return {e.id: e for e in evidence}


def _coerce_brief(
    customer_name: str,
    aliases: list[str],
    meeting_date: str | None,
    objective: str | None,
    period: Period,
    raw: dict[str, Any],
    evidence: list[Evidence],
) -> MeetingBrief:
    valid_ids = {e.id for e in evidence}

    def filter_ids(ids: list[str] | None) -> list[str]:
        return [i for i in (ids or []) if i in valid_ids]

    key_topics = [
        KeyTopic(
            title=str(kt.get("title", "")),
            sources=[s for s in (kt.get("sources") or []) if s in {"notion", "slack", "google_drive"}],
        )
        for kt in (raw.get("key_topics") or [])
        if kt.get("title")
    ]
    risks = [
        Risk(
            title=str(r.get("title", "")),
            severity=_norm_sev(r.get("severity")),
            evidence_ids=filter_ids(r.get("evidence_ids")),
        )
        for r in (raw.get("risks") or [])
        if r.get("title")
    ]
    opportunities = [
        Opportunity(
            title=str(o.get("title", "")),
            evidence_ids=filter_ids(o.get("evidence_ids")),
        )
        for o in (raw.get("opportunities") or [])
        if o.get("title")
    ]
    questions = [
        Question(text=str(q.get("text", "")), rationale=q.get("rationale"))
        for q in (raw.get("suggested_questions") or [])
        if q.get("text")
    ]
    actions = [
        Action(title=str(a.get("title", "")), owner=a.get("owner"))
        for a in (raw.get("recommended_actions") or [])
        if a.get("title")
    ]
    timeline = [
        TimelineEvent(
            date=str(t.get("date", "")),
            source=t.get("source", "notion"),
            title=str(t.get("title", "")),
            summary=t.get("summary"),
            evidence_id=t.get("evidence_id") if t.get("evidence_id") in valid_ids else None,
        )
        for t in (raw.get("timeline") or [])
        if t.get("title")
    ]
    timeline.sort(key=lambda e: e.date, reverse=True)

    return MeetingBrief(
        id=str(uuid.uuid4()),
        customer_name=customer_name,
        customer_aliases=aliases,
        meeting_date=meeting_date,
        objective=objective,
        period=period,
        summary=str(raw.get("summary", "")).strip(),
        meeting_objective=str(raw.get("meeting_objective", objective or "")).strip(),
        key_topics=key_topics,
        risks=risks,
        opportunities=opportunities,
        suggested_questions=questions,
        recommended_actions=actions,
        timeline=timeline,
        evidence=evidence,
        sources_count=len(evidence),
        risk_level=_norm_sev(raw.get("risk_level")),
        updated_at=datetime.utcnow().isoformat(),
    )


def _norm_sev(value: Any) -> Severity:
    v = str(value or "").lower()
    if v in {"high", "critical"}:
        return "high"
    if v in {"low", "info"}:
        return "low"
    return "medium"


def generate_meeting_brief(
    customer_name: str,
    customer_aliases: list[str] | None = None,
    meeting_date: str | None = None,
    objective: str | None = None,
    period: Period = "30d",
) -> dict:
    search_out = search_customer_context(
        customer_name=customer_name,
        customer_aliases=customer_aliases,
        period=period,
    )
    evidence = [Evidence(**e) for e in search_out["evidence"]]
    errors = search_out.get("errors") or {}

    try:
        raw = generate_brief_json(
            customer_name=customer_name,
            aliases=customer_aliases or [],
            meeting_date=meeting_date,
            objective=objective,
            evidence=evidence,
        )
    except LLMUnavailable as e:
        log.warning("LLM unavailable: %s", e)
        raw = {
            "summary": (
                f"LLM unavailable ({e}). Returning raw evidence only — configure "
                "GEMINI_API_KEY to enable analysis."
            ),
            "meeting_objective": objective or "",
            "risk_level": "medium",
            "key_topics": [],
            "risks": [],
            "opportunities": [],
            "suggested_questions": [],
            "recommended_actions": [],
            "timeline": [
                {
                    "date": (e.timestamp or "")[:10],
                    "source": e.source,
                    "title": e.title,
                    "summary": e.excerpt,
                    "evidence_id": e.id,
                }
                for e in evidence[:10]
            ],
        }

    brief = _coerce_brief(
        customer_name=customer_name,
        aliases=customer_aliases or [],
        meeting_date=meeting_date,
        objective=objective,
        period=period,
        raw=raw,
        evidence=evidence,
    )
    STORE.put_brief(brief)
    payload = brief.model_dump()
    payload["errors"] = errors
    return payload
