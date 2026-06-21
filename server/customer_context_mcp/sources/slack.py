"""Slack source — scans channel history for customer-related messages.

Uses a bot token only: it enumerates the channels the bot is a member of and
walks their history, filtering messages by the customer name/aliases. This
avoids search.messages, which requires a user token (xoxp-).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..config import CONFIG
from ..types import Evidence, Period
from .base import SourceUnavailable, period_to_cutoff, shorten

log = logging.getLogger(__name__)


def _client():
    token = CONFIG.slack_bot_token
    if not token:
        raise SourceUnavailable("SLACK_BOT_TOKEN is not set")
    try:
        from slack_sdk import WebClient  # type: ignore
    except ImportError as e:
        raise SourceUnavailable(f"slack-sdk not installed: {e}") from e
    return WebClient(token=token)


def _member_channels(client) -> list[dict]:
    """Channels (public + private) the bot has joined."""
    channels: list[dict] = []
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel,private_channel",
            exclude_archived=True,
            limit=200,
            cursor=cursor,
        )
        for c in resp.get("channels", []):
            if c.get("is_member"):
                channels.append(c)
        cursor = (resp.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            return channels


def _matches(text: str, needles: list[str]) -> bool:
    if not needles:
        return True
    low = text.lower()
    return any(n in low for n in needles)


def _permalink(client, channel_id: str, ts: str) -> str | None:
    try:
        resp = client.chat_getPermalink(channel=channel_id, message_ts=ts)
        return resp.get("permalink")
    except Exception:  # noqa: BLE001
        return None


def search(
    customer_name: str,
    aliases: list[str] | None = None,
    period: Period = "30d",
    limit: int = 200,
) -> list[Evidence]:
    client = _client()
    needles = [n.lower() for n in [customer_name, *(aliases or [])] if n]
    cutoff = period_to_cutoff(period)
    oldest = str(cutoff.timestamp()) if cutoff else None

    try:
        channels = _member_channels(client)
    except Exception as e:  # noqa: BLE001
        err = getattr(getattr(e, "response", None), "get", lambda *_: None)("error")
        if err == "missing_scope":
            raise SourceUnavailable(
                "Slack bot token is missing scopes. Grant channels:read and "
                "groups:read (to list channels) plus channels:history and "
                "groups:history (to read messages)."
            ) from e
        log.warning("slack conversations.list failed: %s", e)
        return []

    out: list[Evidence] = []
    for ch in channels:
        channel_id = ch.get("id")
        channel_name = ch.get("name") or "channel"
        cursor = None
        while True:
            try:
                resp = client.conversations_history(
                    channel=channel_id,
                    limit=200,
                    oldest=oldest,
                    cursor=cursor,
                )
            except Exception as e:  # noqa: BLE001
                err = getattr(getattr(e, "response", None), "get", lambda *_: None)("error")
                if err == "missing_scope":
                    raise SourceUnavailable(
                        "Slack bot token is missing the channels:history / "
                        "groups:history scope needed to read messages."
                    ) from e
                log.warning("slack history failed for #%s: %s", channel_name, e)
                break

            for m in resp.get("messages", []):
                if m.get("subtype"):  # skip joins/leaves/system messages
                    continue
                text = m.get("text") or ""
                if not _matches(text, needles):
                    continue
                ts_raw = m.get("ts") or ""
                ts_iso = None
                try:
                    ts_iso = datetime.fromtimestamp(
                        float(ts_raw), tz=timezone.utc
                    ).isoformat()
                except (TypeError, ValueError):
                    pass
                user = m.get("user") or m.get("username") or ""
                title = f"#{channel_name}" + (f" ({user})" if user else "")
                out.append(
                    Evidence(
                        id=f"slack:{channel_id}:{ts_raw}",
                        source="slack",
                        title=title,
                        excerpt=shorten(text),
                        url=_permalink(client, channel_id, ts_raw),
                        timestamp=ts_iso,
                    )
                )
                if len(out) >= limit:
                    return out

            if not resp.get("has_more"):
                break
            cursor = (resp.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break

    if not out:
        log.info(
            "slack scan returned 0 results — make sure the bot is invited to the "
            "relevant channels (/invite @your-bot) and the customer name appears "
            "in message text."
        )
    return out
