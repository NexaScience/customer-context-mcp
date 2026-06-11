"""FastMCP server exposing the 5 customer-context tools.

The same `mcp` instance powers both transports:
  - stdio  : `customer-context-mcp mcp`         (local Claude Desktop / Code)
  - HTTP   : mounted at /mcp by api/app.py      (Remote MCP)
"""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .config import CONFIG
from .tools import (
    ask_meeting_brief as _ask,
    draft_customer_message as _draft,
    generate_meeting_brief as _brief,
    get_evidence_detail as _evidence,
    search_customer_context as _search,
)
from .types import Period, Source

_default_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
_default_origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]

mcp = FastMCP(
    "customer-context-mcp",
    json_response=True,
    stateless_http=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_default_hosts + list(CONFIG.mcp_allowed_hosts),
        allowed_origins=_default_origins + list(CONFIG.allowed_origins),
    ),
)


@mcp.tool()
def search_customer_context(
    customer_name: str,
    customer_aliases: list[str] | None = None,
    period: Period = "30d",
    sources: list[Source] | None = None,
) -> dict:
    """Search Notion, Slack, and Google Drive for customer-related items.

    Returns a list of Evidence objects sorted newest first.
    """
    return _search(
        customer_name=customer_name,
        customer_aliases=customer_aliases,
        period=period,
        sources=sources,
    )


@mcp.tool()
def generate_meeting_brief(
    customer_name: str,
    customer_aliases: list[str] | None = None,
    meeting_date: str | None = None,
    objective: str | None = None,
    period: Period = "30d",
) -> dict:
    """Run search_customer_context, then use the LLM to produce a structured
    customer meeting brief (summary, key topics, risks, opportunities,
    suggested questions, recommended actions, timeline, evidence).
    """
    return _brief(
        customer_name=customer_name,
        customer_aliases=customer_aliases,
        meeting_date=meeting_date,
        objective=objective,
        period=period,
    )


@mcp.tool()
def ask_meeting_brief(
    brief_id: str,
    question: str,
    evidence_scope: list[Source] | None = None,
) -> dict:
    """Answer a follow-up question grounded in a previously generated brief
    and its evidence."""
    return _ask(brief_id=brief_id, question=question, evidence_scope=evidence_scope)


@mcp.tool()
def get_evidence_detail(evidence_id: str) -> dict:
    """Return the full Evidence record for an evidence_id."""
    return _evidence(evidence_id)


DraftPurpose = Literal["follow_up_email", "internal_slack_summary", "meeting_agenda"]


@mcp.tool()
def draft_customer_message(brief_id: str, purpose: DraftPurpose) -> dict:
    """Draft a follow-up email, internal Slack summary, or meeting agenda
    based on the brief."""
    return _draft(brief_id=brief_id, purpose=purpose)
