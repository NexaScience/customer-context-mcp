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


def _excerpt_from_blocks(client, page_id: str, max_blocks: int = 50, budget: int = 20000) -> str:
    try:
        resp = client.blocks.children.list(block_id=page_id, page_size=min(max_blocks, 100))
    except Exception as e:  # noqa: BLE001
        log.warning("notion blocks fetch failed for %s: %s", page_id, e)
        return ""
    parts: list[str] = []
    for block in resp.get("results", []):
        text = _block_text(block)
        if text:
            parts.append(text)
        if sum(len(p) for p in parts) > budget:
            break
    return "\n".join(parts)


def _property_text(prop: dict) -> str:
    """Plain text for any Notion property type (best-effort)."""
    t = prop.get("type")
    if t == "title":
        return _plain_text(prop.get("title") or [])
    if t == "rich_text":
        return _plain_text(prop.get("rich_text") or [])
    if t in ("select", "status"):
        return (prop.get(t) or {}).get("name") or ""
    if t == "multi_select":
        return " ".join(o.get("name", "") for o in (prop.get("multi_select") or []))
    if t == "people":
        return " ".join(p.get("name", "") for p in (prop.get("people") or []) if isinstance(p, dict))
    if t in ("url", "email", "phone_number"):
        return str(prop.get(t) or "")
    if t == "number":
        n = prop.get("number")
        return "" if n is None else str(n)
    if t == "date":
        return (prop.get("date") or {}).get("start") or ""
    if t == "formula":
        f = prop.get("formula") or {}
        ft = f.get("type")
        return str(f.get(ft) or "") if ft else ""
    return ""


def _row_searchable_text(page: dict) -> str:
    parts = [_property_text(p) for p in (page.get("properties") or {}).values()]
    return " \n".join(p for p in parts if p)


def _properties_summary(page: dict) -> str:
    """Compact 'Key: value' summary of the row's non-empty properties."""
    bits = []
    for name, prop in (page.get("properties") or {}).items():
        txt = _property_text(prop)
        if txt and prop.get("type") != "title":
            bits.append(f"{name}: {txt}")
    return " / ".join(bits)


def _discover_database_ids(client, limit: int = 200) -> list[str]:
    """Find every database the integration can see via the search API.

    Any database shared with the integration is picked up, so the structured
    search works without manually configuring database IDs.
    """
    ids: list[str] = []
    cursor = None
    while True:
        kwargs: dict = {
            "filter": {"property": "object", "value": "database"},
            "page_size": 100,
        }
        if cursor:
            kwargs["start_cursor"] = cursor
        try:
            resp = client.search(**kwargs)
        except Exception as e:  # noqa: BLE001
            log.warning("notion database discovery failed: %s", e)
            break
        for obj in resp.get("results", []):
            did = obj.get("id")
            if did and did not in ids:
                ids.append(did)
        if not resp.get("has_more") or len(ids) >= limit:
            break
        cursor = resp.get("next_cursor")
    return ids


def _iter_db_rows(client, database_id: str, page_size: int = 100):
    """Yield database rows newest-first, paginating until exhausted."""
    cursor = None
    while True:
        kwargs = {
            "database_id": database_id,
            "page_size": min(page_size, 100),
            "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        }
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.databases.query(**kwargs)
        for row in resp.get("results", []):
            yield row
        if not resp.get("has_more"):
            return
        cursor = resp.get("next_cursor")


def _search_databases(
    client,
    db_ids: list[str],
    customer_name: str,
    aliases: list[str] | None,
    period: Period,
    limit: int,
) -> list[Evidence]:
    from datetime import datetime

    cutoff = period_to_cutoff(period)
    needles = [n.lower() for n in [customer_name, *(aliases or [])] if n]
    out: list[Evidence] = []
    seen: set[str] = set()

    for db_id in db_ids:
        try:
            rows = _iter_db_rows(client, db_id)
            for page in rows:
                last_edited = page.get("last_edited_time")
                if cutoff and last_edited:
                    try:
                        ts = datetime.fromisoformat(last_edited.replace("Z", "+00:00"))
                        if ts < cutoff:
                            break  # rows are newest-first → the rest are older too
                    except ValueError:
                        pass
                pid = page.get("id")
                if not pid or pid in seen:
                    continue
                hay = _row_searchable_text(page).lower()
                if needles and not any(n in hay for n in needles):
                    continue
                seen.add(pid)
                title = _page_title(page)
                body = _excerpt_from_blocks(client, pid)
                summary = _properties_summary(page)
                excerpt = "\n".join(x for x in (summary, body) if x)
                out.append(
                    Evidence(
                        id=f"notion:{pid}",
                        source="notion",
                        title=title or "Untitled",
                        excerpt=shorten(excerpt or title or ""),
                        url=page.get("url"),
                        timestamp=last_edited,
                    )
                )
                if len(out) >= limit:
                    return out
        except Exception as e:  # noqa: BLE001
            log.warning("notion database query failed for %s: %s", db_id, e)
            continue
    if not out:
        log.info(
            "notion database search returned 0 results — ensure the integration is "
            "shared with the target databases and that the customer name appears in "
            "a row's title or properties."
        )
    return out


def search(
    customer_name: str,
    aliases: list[str] | None = None,
    period: Period = "30d",
    limit: int = 200,
) -> list[Evidence]:
    client = _client()
    # Structured path: every database shared with the integration is
    # auto-discovered and queried (matches title + properties, includes row
    # body). Falls back to the title-only page search API only when no databases
    # are accessible.
    db_ids = _discover_database_ids(client)
    if db_ids:
        return _search_databases(client, db_ids, customer_name, aliases, period, limit)
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
    if not out:
        log.info(
            "notion search returned 0 results — ensure the integration is shared "
            "with the target pages (Page ••• → Connections) and that the customer "
            "name appears in page titles (Notion search matches titles, not body)."
        )
    return out
