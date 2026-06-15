"""FastMCP server exposing the 5 customer-context tools.

The same ``mcp`` instance powers both transports:
  - stdio  : ``customer-context-mcp mcp``         (local Claude Desktop / Code)
  - HTTP   : mounted at ``/mcp`` by ``api/app.py`` (Remote MCP)
"""

from __future__ import annotations

import json
from typing import Iterable

from fastmcp import FastMCP
from mcp.types import EmbeddedResource, TextContent

from .tools import (
    ask_meeting_brief as _ask,
    draft_customer_message as _draft,
    generate_meeting_brief as _brief,
    get_evidence_detail as _evidence,
    search_customer_context as _search,
)
from .types import Period, Source
from .ui_app import build_brief_ui_resource

mcp = FastMCP("customer-context-mcp")


def _dump(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, default=str, indent=2)


@mcp.tool()
def search_customer_context(
    customer_name: str,
    customer_aliases: list[str] | None = None,
    period: Period = "30d",
    sources: Iterable[Source] | None = None,
) -> str:
    """Search Notion, Slack, and Google Drive for items related to a customer.

    Args:
        customer_name: The customer / company name to search for.
        customer_aliases: Optional alternative names (e.g. JP/EN, parent company).
        period: Lookback window — one of "7d", "30d", "90d", "all".
        sources: Subset of sources to query. Defaults to all three.
    """
    return _dump(
        _search(
            customer_name=customer_name,
            customer_aliases=customer_aliases,
            period=period,
            sources=sources,
        )
    )


@mcp.tool()
def generate_meeting_brief(
    customer_name: str,
    customer_aliases: list[str] | None = None,
    meeting_date: str | None = None,
    objective: str | None = None,
    period: Period = "30d",
) -> list[TextContent | EmbeddedResource]:
    """Run search_customer_context and produce a structured meeting brief via LLM.

    Returns two content items:
      1. ``TextContent`` — the brief as JSON (unchanged from previous behaviour).
      2. ``EmbeddedResource`` — a self-contained HTML dashboard wrapped as an
         MCP App (``ui://`` URI, ``text/html;profile=mcp-app`` MIME). Hosts that
         support mcp-ui render it inline as an iframe; other hosts surface it
         as a normal embedded resource alongside the JSON.

    Args:
        customer_name: The customer / company name.
        customer_aliases: Optional alternative names.
        meeting_date: Upcoming meeting date (free-form string, e.g. "2026-06-20").
        objective: What the meeting is for (e.g. "renewal discussion").
        period: Lookback window for the underlying search.
    """
    brief = _brief(
        customer_name=customer_name,
        customer_aliases=customer_aliases,
        meeting_date=meeting_date,
        objective=objective,
        period=period,
    )
    return [
        TextContent(type="text", text=_dump(brief)),
        build_brief_ui_resource(brief),
    ]


@mcp.tool()
def ask_meeting_brief(
    brief_id: str,
    question: str,
    evidence_scope: list[Source] | None = None,
) -> str:
    """Ask a follow-up question grounded in a previously generated brief.

    Args:
        brief_id: ID returned by ``generate_meeting_brief``.
        question: The follow-up question.
        evidence_scope: Optional subset of sources to restrict the evidence to.
    """
    return _dump(
        _ask(
            brief_id=brief_id,
            question=question,
            evidence_scope=evidence_scope,
        )
    )


@mcp.tool()
def get_evidence_detail(evidence_id: str) -> str:
    """Return the full Evidence record for an ``evidence_id``.

    Args:
        evidence_id: The evidence id as returned in a brief or search result.
    """
    return _dump(_evidence(evidence_id))


@mcp.tool()
def draft_customer_message(brief_id: str, purpose: str) -> str:
    """Draft a follow-up email, internal Slack summary, or meeting agenda.

    Args:
        brief_id: ID returned by ``generate_meeting_brief``.
        purpose: One of "follow_up_email", "internal_slack_summary", "meeting_agenda".
    """
    return _dump(_draft(brief_id=brief_id, purpose=purpose))
