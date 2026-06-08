"""MCP stdio server exposing the 5 tools."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .tools import (
    ask_meeting_brief,
    draft_customer_message,
    generate_meeting_brief,
    get_evidence_detail,
    search_customer_context,
)

log = logging.getLogger(__name__)

server = Server("customer-context-mcp")


TOOLS: list[Tool] = [
    Tool(
        name="search_customer_context",
        description=(
            "Search Notion, Slack, and Google Drive for customer-related items. "
            "Returns a list of Evidence objects sorted newest first."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "customer_aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "period": {
                    "type": "string",
                    "enum": ["7d", "30d", "90d", "all"],
                    "default": "30d",
                },
                "sources": {
                    "type": "array",
                    "items": {"enum": ["notion", "slack", "google_drive"]},
                    "default": ["notion", "slack", "google_drive"],
                },
            },
            "required": ["customer_name"],
        },
    ),
    Tool(
        name="generate_meeting_brief",
        description=(
            "Run search_customer_context, then use the LLM to produce a structured "
            "customer meeting brief (summary, key topics, risks, opportunities, "
            "suggested questions, recommended actions, timeline, evidence)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "customer_aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "meeting_date": {"type": "string"},
                "objective": {"type": "string"},
                "period": {
                    "type": "string",
                    "enum": ["7d", "30d", "90d", "all"],
                    "default": "30d",
                },
            },
            "required": ["customer_name"],
        },
    ),
    Tool(
        name="ask_meeting_brief",
        description=(
            "Answer a follow-up question grounded in a previously generated brief and "
            "its evidence."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "brief_id": {"type": "string"},
                "question": {"type": "string"},
                "evidence_scope": {
                    "type": "array",
                    "items": {"enum": ["notion", "slack", "google_drive"]},
                },
            },
            "required": ["brief_id", "question"],
        },
    ),
    Tool(
        name="get_evidence_detail",
        description="Return the full Evidence record for an evidence_id.",
        inputSchema={
            "type": "object",
            "properties": {"evidence_id": {"type": "string"}},
            "required": ["evidence_id"],
        },
    ),
    Tool(
        name="draft_customer_message",
        description=(
            "Draft a follow-up email, internal Slack summary, or meeting agenda based "
            "on the brief."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "brief_id": {"type": "string"},
                "purpose": {
                    "enum": [
                        "follow_up_email",
                        "internal_slack_summary",
                        "meeting_agenda",
                    ]
                },
            },
            "required": ["brief_id", "purpose"],
        },
    ),
]


@server.list_tools()
async def _list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    arguments = arguments or {}
    try:
        if name == "search_customer_context":
            result = search_customer_context(**arguments)
        elif name == "generate_meeting_brief":
            result = generate_meeting_brief(**arguments)
        elif name == "ask_meeting_brief":
            result = ask_meeting_brief(**arguments)
        elif name == "get_evidence_detail":
            result = get_evidence_detail(**arguments)
        elif name == "draft_customer_message":
            result = draft_customer_message(**arguments)
        else:
            result = {"error": f"unknown tool: {name}"}
    except TypeError as e:
        result = {"error": f"invalid arguments: {e}"}
    except Exception as e:  # noqa: BLE001
        log.exception("tool %s failed", name)
        result = {"error": f"{type(e).__name__}: {e}"}
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]


async def run() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())
