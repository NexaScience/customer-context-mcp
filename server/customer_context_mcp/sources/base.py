"""Shared helpers for data source clients."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from ..types import Period


class SourceError(Exception):
    """Raised when a source call fails in a recoverable way."""


class SourceUnavailable(SourceError):
    """Raised when a source is not configured (missing credentials)."""


PERIOD_DAYS: dict[Period, Optional[int]] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "all": None,
}


def period_to_cutoff(period: Period) -> Optional[datetime]:
    days = PERIOD_DAYS.get(period, 30)
    if days is None:
        return None
    return datetime.now(timezone.utc) - timedelta(days=days)


def shorten(text: str, limit: int = 360) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
