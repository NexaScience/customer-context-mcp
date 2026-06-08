"""get_evidence_detail tool."""

from __future__ import annotations

from ..store import STORE


def get_evidence_detail(evidence_id: str) -> dict:
    ev = STORE.get_evidence(evidence_id)
    if ev is None:
        return {"error": f"evidence not found: {evidence_id}"}
    return ev.model_dump()
