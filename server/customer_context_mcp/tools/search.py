"""search_customer_context tool."""

from __future__ import annotations

import logging
from typing import Iterable

from ..sources import SourceUnavailable
from ..sources import notion as notion_src
from ..sources import slack as slack_src
from ..sources import google_drive as gdrive_src
from ..types import Evidence, Period, Source

log = logging.getLogger(__name__)

_SEARCHERS = {
    "notion": notion_src.search,
    "slack": slack_src.search,
    "google_drive": gdrive_src.search,
}


def search_customer_context(
    customer_name: str,
    customer_aliases: list[str] | None = None,
    period: Period = "30d",
    sources: Iterable[Source] | None = None,
) -> dict:
    """Run all configured source searches in parallel-ish (sequentially, but cheap)
    and aggregate Evidence.
    """
    selected = list(sources or ("notion", "slack", "google_drive"))
    evidence: list[Evidence] = []
    errors: dict[str, str] = {}
    for src in selected:
        fn = _SEARCHERS.get(src)
        if not fn:
            continue
        try:
            items = fn(customer_name, customer_aliases or [], period)
            evidence.extend(items)
        except SourceUnavailable as e:
            log.info("source %s unavailable: %s", src, e)
            errors[src] = str(e)
        except Exception as e:  # noqa: BLE001
            log.exception("source %s failed", src)
            errors[src] = f"{type(e).__name__}: {e}"
    evidence.sort(key=lambda ev: ev.timestamp or "", reverse=True)
    return {
        "customer_name": customer_name,
        "customer_aliases": customer_aliases or [],
        "period": period,
        "evidence": [e.model_dump() for e in evidence],
        "errors": errors,
    }
