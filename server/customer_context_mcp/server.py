"""FastMCP server exposing the 5 customer-context tools.

The same ``mcp`` instance powers both transports:
  - stdio  : ``customer-context-mcp mcp``         (local Claude Desktop / Code)
  - HTTP   : mounted at ``/mcp`` by ``api/app.py`` (Remote MCP)
"""

from __future__ import annotations

import json
from typing import Iterable

from fastmcp import FastMCP
from fastmcp.apps.config import AppConfig, ResourceCSP
from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.mime import UI_MIME_TYPE
from mcp.types import TextContent

from .tools import (
    ask_meeting_brief as _ask,
    draft_customer_message as _draft,
    generate_meeting_brief as _brief,
    get_evidence_detail as _evidence,
    search_customer_context as _search,
)
from .types import Period, Source
from .ui_app import build_brief_ui_resource
from .widget import WIDGET_URI, render_brief_widget_html

mcp = FastMCP("customer-context-mcp")


# ---------------------------------------------------------------------------
# MCP App resource — the iframe shell rendered by ChatGPT Apps and any other
# mcp-apps-aware host. The brief data arrives at run-time as the tool's
# structured_content via a ``ui/notifications/tool-result`` postMessage; this
# resource holds only the HTML shell + JS listener.
# ---------------------------------------------------------------------------


@mcp.resource(
    WIDGET_URI,
    name="customer-context-meeting-brief-widget",
    description="Iframe shell that renders the meeting brief dashboard.",
    mime_type=UI_MIME_TYPE,
    app=AppConfig(
        # The widget has no remote subresources, no outbound fetch, and no
        # nested iframes — the CSP locks the iframe down accordingly.
        csp=ResourceCSP(
            connect_domains=[],
            resource_domains=[],
            frame_domains=[],
        ),
        prefers_border=True,
    ),
)
def meeting_brief_widget() -> str:
    return render_brief_widget_html()


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


@mcp.tool(
    # MCP Apps extension — advertises the iframe shell registered above.
    # FastMCP serialises this into _meta.ui.resourceUri (the standard key)
    # and ChatGPT Apps also honours _meta["openai/outputTemplate"] as an
    # OpenAI-specific compatibility alias for the same URI.
    app=AppConfig(resource_uri=WIDGET_URI),
    meta={"openai/outputTemplate": WIDGET_URI},
)
def generate_meeting_brief(
    customer_name: str,
    customer_aliases: list[str] | None = None,
    meeting_date: str | None = None,
    objective: str | None = None,
    period: Period = "30d",
) -> ToolResult:
    """Run search_customer_context and produce a structured meeting brief via LLM.

    The tool result carries three payloads so both MCP Apps (ChatGPT) and the
    legacy mcp-ui inline pattern (Claude / mcp-ui-aware hosts) can render the
    same brief:

    - ``structured_content`` — the brief as a JSON object. ChatGPT delivers
      this to the iframe at run-time via ``ui/notifications/tool-result``.
    - ``content[0]`` (``TextContent``) — the same brief as a JSON string for
      hosts that read tool output as text.
    - ``content[1]`` (``UIResource``) — a fully self-contained HTML
      dashboard for mcp-ui clients that render inline ``ui://`` resources
      (no postMessage needed).

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
    return ToolResult(
        content=[
            TextContent(type="text", text=_dump(brief)),
            build_brief_ui_resource(brief),
        ],
        structured_content=brief,
    )


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
