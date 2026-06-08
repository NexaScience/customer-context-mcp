"""In-memory store for generated briefs and evidence."""

from __future__ import annotations

from threading import RLock
from typing import Optional

from .types import Evidence, MeetingBrief


class BriefStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._briefs: dict[str, MeetingBrief] = {}
        self._evidence: dict[str, Evidence] = {}

    def put_brief(self, brief: MeetingBrief) -> None:
        with self._lock:
            self._briefs[brief.id] = brief
            for ev in brief.evidence:
                self._evidence[ev.id] = ev

    def get_brief(self, brief_id: str) -> Optional[MeetingBrief]:
        with self._lock:
            return self._briefs.get(brief_id)

    def latest_brief(self) -> Optional[MeetingBrief]:
        with self._lock:
            if not self._briefs:
                return None
            return max(self._briefs.values(), key=lambda b: b.updated_at)

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        with self._lock:
            return self._evidence.get(evidence_id)


STORE = BriefStore()
