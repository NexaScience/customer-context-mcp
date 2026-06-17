"""Notion source — searches pages by customer name and extracts excerpts."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from ..config import CONFIG
from ..types import Evidence, Period
from .base import SourceUnavailable, period_to_cutoff, shorten

log = logging.getLogger(__name__)


def _client():
    if not CONFIG.notion_token:
        raise SourceUnavailable("NOTION_TOKEN is not set")
    try:
        from notion_client import Client  # type: ignore
    except ImportError as e:
        raise SourceUnavailable(f"notion-client not installed: {e}") from e
    return Client(auth=CONFIG.notion_token)


def _plain_text(rich_text: Iterable[dict]) -> str:
    return "".join(rt.get("plain_text", "") for rt in rich_text or [])


def _block_text(block: dict) -> str:
    btype = block.get("type")
    data = block.get(btype) or {}
    rich = data.get("rich_text") or data.get("text") or []
    return _plain_text(rich)


def _page_title(page: dict) -> str:
    props = page.get("properties") or {}
    for prop in props.values():
        if prop.get("type") == "title":
            return _plain_text(prop.get("title") or [])
    return page.get("id", "Untitled")


def _excerpt_from_blocks(client, page_id: str, max_blocks: int = 12) -> str:
    try:
        resp = client.blocks.children.list(block_id=page_id, page_size=max_blocks)
    except Exception as e:  # noqa: BLE001
        log.warning("notion blocks fetch failed for %s: %s", page_id, e)
        return ""
    parts: list[str] = []
    for block in resp.get("results", []):
        text = _block_text(block)
        if text:
            parts.append(text)
        if sum(len(p) for p in parts) > 600:
            break
    return "\n".join(parts)


def search(
    customer_name: str,
    aliases: list[str] | None = None,
    period: Period = "30d",
    limit: int = 200,
) -> list[Evidence]:
    client = _client()
    queries = [customer_name, *(aliases or [])]
    cutoff = period_to_cutoff(period)
    seen: set[str] = set()
    out: list[Evidence] = []
    for q in queries:
        try:
            resp = client.search(
                query=q,
                filter={"property": "object", "value": "page"},
                page_size=min(limit, 100),  # Notion API caps page_size at 100
            )
        except Exception as e:  # noqa: BLE001
            log.warning("notion search failed for %s: %s", q, e)
            continue
        for page in resp.get("results", []):
            pid = page.get("id")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            last_edited: Optional[str] = page.get("last_edited_time")
            if cutoff and last_edited:
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(last_edited.replace("Z", "+00:00"))
                    if ts < cutoff:
                        continue
                except ValueError:
                    pass
            title = _page_title(page)
            excerpt = _excerpt_from_blocks(client, pid)
            url = page.get("url")
            out.append(
                Evidence(
                    id=f"notion:{pid}",
                    source="notion",
                    title=title or "Untitled",
                    excerpt=shorten(excerpt or title or ""),
                    url=url,
                    timestamp=last_edited,
                )
            )
            if len(out) >= limit:
                return out
    return out
