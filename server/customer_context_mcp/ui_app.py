"""MCP Apps renderer for the meeting brief.

Produces a self-contained HTML document and wraps it in an ``EmbeddedResource``
following the mcp-ui convention (``ui://`` URI + ``text/html;profile=mcp-app``
MIME type). Hosts that recognise MCP Apps render this inline as an iframe;
hosts that don't still see the standard MCP embedded-resource content item.

The HTML is fully static — no network calls, no external assets, no JS
frameworks — so the brief is visible inside whichever sandboxed iframe the
host provides.
"""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlparse

from mcp.types import EmbeddedResource, TextResourceContents
from pydantic import AnyUrl

# mcp-ui convention — see https://mcpui.dev. These two constants are the entire
# wire-level contract for "MCP Apps" beyond what mcp.types already provides.
MCP_APP_MIME_TYPE = "text/html;profile=mcp-app"
MCP_APP_URI_PREFIX = "ui://"
_UI_METADATA_PREFIX = "mcpui.dev/ui-"


_SOURCE_LABEL = {
    "notion": "Notion",
    "slack": "Slack",
    "google_drive": "Google Drive",
}

_SEVERITY_COLOR = {
    "high": ("#fee2e2", "#991b1b"),
    "medium": ("#fef3c7", "#92400e"),
    "low": ("#dcfce7", "#166534"),
}


def _esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _safe_url(value: Any) -> str | None:
    # Evidence URLs come from external systems (Notion / Slack / Google Drive).
    # Block javascript: / data: / vbscript: etc. — the HTML is rendered inside
    # the MCP host's iframe and a click on a malicious href would execute in
    # that sandbox.
    if not value:
        return None
    try:
        parsed = urlparse(str(value))
    except Exception:
        return None
    if parsed.scheme.lower() not in {"http", "https", "mailto"}:
        return None
    return str(value)


def _source_chip(source: str) -> str:
    label = _SOURCE_LABEL.get(source, source)
    return (
        '<span style="display:inline-block;padding:2px 8px;margin:0 4px 4px 0;'
        "border-radius:999px;background:#eef2ff;color:#3730a3;font-size:11px;"
        'font-weight:600;letter-spacing:0.02em;">'
        f"{_esc(label)}</span>"
    )


def _severity_badge(severity: str) -> str:
    bg, fg = _SEVERITY_COLOR.get(severity, _SEVERITY_COLOR["medium"])
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
        f"background:{bg};color:{fg};font-size:11px;font-weight:700;"
        f'text-transform:uppercase;letter-spacing:0.06em;">{_esc(severity)}</span>'
    )


def _evidence_refs(ids: list[str], evidence_by_id: dict[str, dict]) -> str:
    if not ids:
        return ""
    chips = []
    for eid in ids:
        ev = evidence_by_id.get(eid)
        if not ev:
            continue
        title = _esc(ev.get("title", eid))
        source = _esc(_SOURCE_LABEL.get(ev.get("source", ""), ev.get("source", "")))
        chips.append(
            '<span style="display:inline-block;margin:2px 4px 0 0;padding:2px 8px;'
            "border:1px solid #e2e8f0;border-radius:6px;background:#f8fafc;"
            f'color:#475569;font-size:11px;">{source} · {title}</span>'
        )
    if not chips:
        return ""
    return f'<div style="margin-top:6px;">{"".join(chips)}</div>'


def _section(title: str, body: str, *, empty: str = "") -> str:
    inner = body if body.strip() else (
        f'<p style="color:#94a3b8;font-size:13px;margin:0;">{_esc(empty)}</p>'
        if empty else ""
    )
    return (
        '<section style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;'
        'padding:16px 18px;margin-bottom:12px;">'
        f'<h2 style="margin:0 0 10px;font-size:13px;font-weight:700;color:#0f172a;'
        'text-transform:uppercase;letter-spacing:0.08em;">'
        f"{_esc(title)}</h2>{inner}</section>"
    )


def _render_header(brief: dict) -> str:
    customer = _esc(brief.get("customer_name", ""))
    aliases = brief.get("customer_aliases") or []
    alias_html = ""
    if aliases:
        alias_html = (
            '<div style="font-size:12px;color:#64748b;margin-top:2px;">'
            f"alias: {_esc(', '.join(aliases))}</div>"
        )
    meta_bits = []
    if brief.get("meeting_date"):
        meta_bits.append(f"Meeting: {_esc(brief['meeting_date'])}")
    if brief.get("objective"):
        meta_bits.append(f"Objective: {_esc(brief['objective'])}")
    meta_bits.append(f"Period: {_esc(brief.get('period', '30d'))}")
    meta_bits.append(f"Sources: {_esc(brief.get('sources_count', 0))}")
    risk_level = brief.get("risk_level", "medium")
    meta_html = (
        '<div style="display:flex;gap:12px;flex-wrap:wrap;font-size:12px;'
        'color:#475569;margin-top:8px;">'
        + "".join(f"<span>{m}</span>" for m in meta_bits)
        + f'<span>Risk: {_severity_badge(risk_level)}</span>'
        + "</div>"
    )
    return (
        '<header style="background:linear-gradient(135deg,#1e293b,#0f172a);'
        "color:#f8fafc;padding:22px 24px;border-radius:14px;margin-bottom:14px;"
        'box-shadow:0 1px 2px rgba(15,23,42,0.04);">'
        f'<div style="font-size:11px;letter-spacing:0.12em;'
        'text-transform:uppercase;color:#94a3b8;">Customer Meeting Brief</div>'
        f'<h1 style="margin:6px 0 0;font-size:24px;font-weight:700;letter-spacing:-0.01em;">'
        f"{customer}</h1>{alias_html}{meta_html}</header>"
    )


def _render_summary(brief: dict) -> str:
    summary = brief.get("summary") or ""
    if not summary:
        return _section("Executive Summary", "", empty="No summary yet.")
    body = (
        '<p style="margin:0;font-size:14px;line-height:1.6;color:#1e293b;">'
        f"{_esc(summary)}</p>"
    )
    if brief.get("meeting_objective"):
        body += (
            '<p style="margin:10px 0 0;font-size:12px;color:#64748b;">'
            f"Objective — {_esc(brief['meeting_objective'])}</p>"
        )
    return _section("Executive Summary", body)


def _render_key_topics(brief: dict) -> str:
    topics = brief.get("key_topics") or []
    if not topics:
        return _section("Key Topics", "", empty="No key topics surfaced.")
    items = []
    for t in topics:
        chips = "".join(_source_chip(s) for s in (t.get("sources") or []))
        items.append(
            '<li style="padding:8px 0;border-bottom:1px solid #f1f5f9;">'
            f'<div style="font-size:14px;color:#0f172a;font-weight:600;">'
            f"{_esc(t.get('title', ''))}</div>{chips}</li>"
        )
    body = f'<ul style="list-style:none;padding:0;margin:0;">{"".join(items)}</ul>'
    return _section("Key Topics", body)


def _render_risks(brief: dict, evidence_by_id: dict[str, dict]) -> str:
    risks = brief.get("risks") or []
    if not risks:
        return _section("Risks", "", empty="No risks flagged.")
    items = []
    for r in risks:
        items.append(
            '<li style="padding:10px 0;border-bottom:1px solid #f1f5f9;">'
            f'<div style="display:flex;justify-content:space-between;gap:8px;">'
            f'<div style="font-size:14px;color:#0f172a;font-weight:600;">'
            f"{_esc(r.get('title', ''))}</div>"
            f"{_severity_badge(r.get('severity', 'medium'))}</div>"
            f"{_evidence_refs(r.get('evidence_ids') or [], evidence_by_id)}</li>"
        )
    body = f'<ul style="list-style:none;padding:0;margin:0;">{"".join(items)}</ul>'
    return _section("Risks", body)


def _render_opportunities(brief: dict, evidence_by_id: dict[str, dict]) -> str:
    opps = brief.get("opportunities") or []
    if not opps:
        return _section("Opportunities", "", empty="No opportunities flagged.")
    items = []
    for o in opps:
        items.append(
            '<li style="padding:10px 0;border-bottom:1px solid #f1f5f9;">'
            f'<div style="font-size:14px;color:#0f172a;font-weight:600;">'
            f"{_esc(o.get('title', ''))}</div>"
            f"{_evidence_refs(o.get('evidence_ids') or [], evidence_by_id)}</li>"
        )
    body = f'<ul style="list-style:none;padding:0;margin:0;">{"".join(items)}</ul>'
    return _section("Opportunities", body)


def _render_questions(brief: dict) -> str:
    qs = brief.get("suggested_questions") or []
    if not qs:
        return _section("Suggested Questions", "", empty="No questions suggested.")
    items = []
    for q in qs:
        rationale = q.get("rationale")
        rat_html = (
            f'<div style="font-size:12px;color:#64748b;margin-top:2px;">'
            f"{_esc(rationale)}</div>"
            if rationale
            else ""
        )
        items.append(
            '<li style="padding:8px 0;border-bottom:1px solid #f1f5f9;">'
            f'<div style="font-size:14px;color:#0f172a;">{_esc(q.get("text", ""))}</div>'
            f"{rat_html}</li>"
        )
    body = f'<ul style="list-style:none;padding:0;margin:0;">{"".join(items)}</ul>'
    return _section("Suggested Questions", body)


def _render_actions(brief: dict) -> str:
    actions = brief.get("recommended_actions") or []
    if not actions:
        return _section("Recommended Actions", "", empty="No actions recommended.")
    items = []
    for a in actions:
        owner = a.get("owner")
        owner_html = (
            f'<span style="font-size:11px;color:#64748b;margin-left:8px;">@ {_esc(owner)}</span>'
            if owner
            else ""
        )
        items.append(
            '<li style="padding:8px 0;border-bottom:1px solid #f1f5f9;">'
            f'<div style="font-size:14px;color:#0f172a;">{_esc(a.get("title", ""))}'
            f"{owner_html}</div></li>"
        )
    body = f'<ul style="list-style:none;padding:0;margin:0;">{"".join(items)}</ul>'
    return _section("Recommended Actions", body)


def _render_timeline(brief: dict) -> str:
    events = brief.get("timeline") or []
    if not events:
        return _section("Recent Timeline", "", empty="No recent activity captured.")
    items = []
    for ev in events:
        summary = ev.get("summary")
        sum_html = (
            f'<div style="font-size:12px;color:#64748b;margin-top:2px;">{_esc(summary)}</div>'
            if summary
            else ""
        )
        items.append(
            '<li style="padding:8px 0;border-bottom:1px solid #f1f5f9;display:flex;gap:10px;">'
            f'<div style="min-width:80px;font-size:11px;color:#64748b;font-variant-numeric:tabular-nums;">'
            f"{_esc(ev.get('date', ''))}</div>"
            f'<div style="flex:1;">'
            f"{_source_chip(ev.get('source', ''))}"
            f'<div style="font-size:14px;color:#0f172a;font-weight:600;">'
            f"{_esc(ev.get('title', ''))}</div>{sum_html}</div></li>"
        )
    body = f'<ul style="list-style:none;padding:0;margin:0;">{"".join(items)}</ul>'
    return _section("Recent Timeline", body)


def _render_evidence(brief: dict) -> str:
    evidence = brief.get("evidence") or []
    if not evidence:
        return ""
    items = []
    for e in evidence[:50]:
        url = _safe_url(e.get("url"))
        title = _esc(e.get("title", e.get("id", "")))
        title_html = (
            f'<a href="{_esc(url)}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#1d4ed8;text-decoration:none;">{title}</a>'
            if url
            else title
        )
        excerpt = e.get("excerpt") or ""
        items.append(
            '<li style="padding:8px 0;border-bottom:1px solid #f1f5f9;">'
            f"{_source_chip(e.get('source', ''))}"
            f'<div style="font-size:13px;color:#0f172a;font-weight:600;">{title_html}</div>'
            f'<div style="font-size:12px;color:#475569;margin-top:2px;line-height:1.5;">'
            f"{_esc(excerpt)}</div></li>"
        )
    body = f'<ul style="list-style:none;padding:0;margin:0;">{"".join(items)}</ul>'
    return _section(f"Evidence ({len(evidence)})", body)


def render_brief_html(brief: dict) -> str:
    """Render a MeetingBrief dict as a self-contained HTML document."""
    evidence_by_id = {e["id"]: e for e in (brief.get("evidence") or []) if "id" in e}
    body = (
        _render_header(brief)
        + _render_summary(brief)
        + _render_key_topics(brief)
        + _render_risks(brief, evidence_by_id)
        + _render_opportunities(brief, evidence_by_id)
        + _render_questions(brief)
        + _render_actions(brief)
        + _render_timeline(brief)
        + _render_evidence(brief)
    )
    # CSP defense-in-depth: no scripts, no remote subresources, no plugins, no
    # framing of other pages. The dashboard is fully static so this is safe.
    csp = (
        "default-src 'none'; "
        "style-src 'unsafe-inline'; "
        "img-src data:; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "frame-ancestors *"
    )
    return (
        "<!DOCTYPE html><html lang=\"en\"><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        f"<title>Meeting Brief — {_esc(brief.get('customer_name', ''))}</title>"
        "<style>"
        "html,body{margin:0;padding:0;background:#f8fafc;color:#0f172a;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;}"
        ".wrap{max-width:880px;margin:0 auto;padding:18px;}"
        "ul li:last-child{border-bottom:none !important;}"
        "</style></head>"
        f'<body><div class="wrap">{body}</div></body></html>'
    )


def build_brief_ui_resource(brief: dict) -> EmbeddedResource:
    """Wrap the rendered HTML as an mcp-ui-compatible EmbeddedResource.

    The MCP host receives an ``EmbeddedResource`` content item whose ``uri``
    starts with ``ui://`` and whose ``mimeType`` is ``text/html;profile=mcp-app``;
    mcp-ui-aware hosts render the HTML as a sandboxed iframe inline with the
    chat. Other hosts simply expose it as a normal embedded resource.
    """
    uri = f"{MCP_APP_URI_PREFIX}customer-context-mcp/meeting-brief/{brief.get('id', 'unknown')}"
    resource = TextResourceContents(
        uri=AnyUrl(uri),
        mimeType=MCP_APP_MIME_TYPE,
        text=render_brief_html(brief),
        _meta={f"{_UI_METADATA_PREFIX}preferred-frame-size": ["920px", "720px"]},
    )
    return EmbeddedResource(type="resource", resource=resource)
