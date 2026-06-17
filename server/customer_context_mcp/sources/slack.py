"""Slack source — uses search.messages to find customer-related threads."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..config import CONFIG
from ..types import Evidence, Period
from .base import SourceUnavailable, period_to_cutoff, shorten

log = logging.getLogger(__name__)


def _client():
    if not CONFIG.slack_bot_token:
        raise SourceUnavailable("SLACK_BOT_TOKEN is not set")
    try:
        from slack_sdk import WebClient  # type: ignore
    except ImportError as e:
        raise SourceUnavailable(f"slack-sdk not installed: {e}") from e
    return WebClient(token=CONFIG.slack_bot_token)


def _build_query(customer_name: str, aliases: list[str], period: Period) -> str:
    names = [customer_name, *(aliases or [])]
    name_clause = " OR ".join(f'"{n}"' for n in names if n)
    parts = [f"({name_clause})"] if name_clause else []
    cutoff = period_to_cutoff(period)
    if cutoff:
        parts.append(f"after:{cutoff.strftime('%Y-%m-%d')}")
    return " ".join(parts)


def search(
    customer_name: str,
    aliases: list[str] | None = None,
    period: Period = "30d",
    limit: int = 200,
) -> list[Evidence]:
    client = _client()
    query = _build_query(customer_name, aliases or [], period)
    try:
        resp = client.search_messages(
            query=query, count=min(limit, 100), sort="timestamp", sort_dir="desc"
        )  # Slack search count caps at 100
    except Exception as e:  # noqa: BLE001
        log.warning("slack search failed: %s", e)
        return []
    messages = (resp.get("messages") or {}).get("matches") or []
    out: list[Evidence] = []
    for m in messages:
        ts_raw = m.get("ts") or ""
        ts_iso = None
        try:
            ts_iso = datetime.fromtimestamp(float(ts_raw), tz=timezone.utc).isoformat()
        except (TypeError, ValueError):
            pass
        channel = (m.get("channel") or {}).get("name") or "channel"
        user = m.get("username") or (m.get("user") or "")
        title = f"#{channel}" + (f" ({user})" if user else "")
        out.append(
            Evidence(
                id=f"slack:{m.get('iid') or ts_raw}",
                source="slack",
                title=title,
                excerpt=shorten(m.get("text") or ""),
                url=m.get("permalink"),
                timestamp=ts_iso,
            )
        )
    return out
