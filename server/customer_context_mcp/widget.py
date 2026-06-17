"""MCP Apps widget — registered as an MCP resource at a ``ui://`` URI.

Unlike the inline mcp-ui resource (see :mod:`ui_app`), MCP Apps requires the
UI to be a *separate* MCP Resource. The tool only advertises the resource URI
via its ``_meta.ui.resourceUri`` annotation; the brief data is delivered to the
iframe at run-time as the tool's ``structuredContent``.

This module produces the HTML shell that runs inside the iframe. It implements
the MCP Apps view-side protocol (``@modelcontextprotocol/ext-apps``) by hand in
dependency-free vanilla JS so it loads in any sandboxed iframe:

  1. **Handshake** — on load it sends a ``ui/initialize`` JSON-RPC *request* to
     ``window.parent``, applies the returned ``hostContext`` (theme / styles /
     fonts / safe-area), then sends the ``ui/notifications/initialized``
     notification. **Hosts only deliver the tool result after this handshake
     completes** — a passive listener that skips it leaves the iframe blank on
     strict hosts (see modelcontextprotocol/ext-apps `App.connect`, and
     anthropics/claude-ai-mcp#149).
  2. **Tool result** — handles ``ui/notifications/tool-result`` (the primary
     data path), reading ``structuredContent`` (falling back to the JSON in
     ``content[].text``) and rendering the meeting brief.
  3. **Host context** — handles ``ui/notifications/host-context-changed`` to
     react to live theme / style changes, and answers host ``ping`` /
     ``ui/resource-teardown`` requests so the host does not error or time out.
  4. **Auto-resize** — reports ``ui/notifications/size-changed`` via
     ``ResizeObserver`` so the host can size the iframe to the content.

Theming follows the spec: structural surfaces consume host CSS variables
(``--color-*``, ``--font-sans``, ``--border-radius-*``) with the previous
palette as fallbacks, so the brief blends into both light and dark hosts while
still rendering standalone.
"""

from __future__ import annotations

WIDGET_URI = "ui://customer-context-mcp/meeting-brief.html"

# Wire constants mirrored from @modelcontextprotocol/ext-apps (src/spec.types.ts).
_PROTOCOL_VERSION = "2026-01-26"


_WIDGET_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meeting Brief</title>
<style>
  :root{color-scheme:light dark;}
  html,body{margin:0;padding:0;
    background:var(--color-background-primary,#f8fafc);
    color:var(--color-text-primary,#0f172a);
    font-family:var(--font-sans,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif);}
  .wrap{max-width:880px;margin:0 auto;padding:18px;}
  .empty{color:var(--color-text-tertiary,#94a3b8);font-size:13px;margin:0;}
  .header{background:linear-gradient(135deg,#1e293b,#0f172a);color:#f8fafc;
    padding:22px 24px;border-radius:var(--border-radius-xl,14px);margin-bottom:14px;
    box-shadow:var(--shadow-sm,0 1px 2px rgba(15,23,42,0.04));}
  .header .label{font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#94a3b8;}
  .header h1{margin:6px 0 0;font-size:24px;font-weight:700;letter-spacing:-0.01em;}
  .header .alias{font-size:12px;color:#cbd5e1;margin-top:2px;}
  .header .meta{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:#cbd5e1;margin-top:8px;}
  section.card{background:var(--color-background-secondary,#ffffff);
    border:1px solid var(--color-border-primary,#e2e8f0);
    border-radius:var(--border-radius-lg,12px);padding:16px 18px;margin-bottom:12px;}
  section.card h2{margin:0 0 10px;font-size:13px;font-weight:700;
    color:var(--color-text-primary,#0f172a);
    text-transform:uppercase;letter-spacing:0.08em;}
  ul.rows{list-style:none;padding:0;margin:0;}
  ul.rows li{padding:8px 0;border-bottom:1px solid var(--color-border-secondary,#f1f5f9);}
  ul.rows li:last-child{border-bottom:none;}
  .row-title{font-size:14px;color:var(--color-text-primary,#0f172a);font-weight:600;}
  .row-text{font-size:14px;color:var(--color-text-primary,#0f172a);}
  .row-sub{font-size:12px;color:var(--color-text-secondary,#64748b);margin-top:2px;}
  .row-flex{display:flex;justify-content:space-between;gap:8px;align-items:center;}
  .timeline-row{display:flex;gap:10px;}
  .timeline-date{min-width:80px;font-size:11px;color:var(--color-text-secondary,#64748b);
    font-variant-numeric:tabular-nums;}
  .timeline-body{flex:1;}
  .src-chip{display:inline-block;padding:2px 8px;margin:0 4px 4px 0;
    border-radius:999px;background:#eef2ff;color:#3730a3;font-size:11px;
    font-weight:600;letter-spacing:0.02em;}
  .ev-ref{display:inline-block;margin:2px 4px 0 0;padding:2px 8px;
    border:1px solid var(--color-border-primary,#e2e8f0);border-radius:6px;
    background:var(--color-background-tertiary,#f8fafc);
    color:var(--color-text-secondary,#475569);font-size:11px;}
  .sev{display:inline-block;padding:2px 8px;border-radius:999px;
    font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;}
  .sev-high{background:#fee2e2;color:#991b1b;}
  .sev-medium{background:#fef3c7;color:#92400e;}
  .sev-low{background:#dcfce7;color:#166534;}
  .ev-link{color:var(--color-text-info,#1d4ed8);text-decoration:none;}
  .ev-excerpt{font-size:12px;color:var(--color-text-secondary,#475569);margin-top:2px;line-height:1.5;}
  .summary{margin:0;font-size:14px;line-height:1.6;color:var(--color-text-primary,#1e293b);}
</style>
</head>
<body>
<div class="wrap" id="root">
  <p class="empty" id="empty-state">Waiting for meeting brief…</p>
</div>
<script>
(function () {
  "use strict";

  // ---------------------------------------------------------------------
  // MCP Apps view-side protocol over postMessage (no SDK dependency).
  // Mirrors @modelcontextprotocol/ext-apps `App.connect()` + PostMessageTransport.
  // ---------------------------------------------------------------------
  var PROTOCOL_VERSION = "2026-01-26";
  var APP_INFO = {name: "customer-context-meeting-brief", version: "0.1.0"};
  var parentWin = window.parent;
  var nextId = 1;
  var pending = {};          // outbound request id -> callback(result|null)
  var initialized = false;
  var fontsApplied = false;

  function post(msg) {
    try { parentWin.postMessage(msg, "*"); } catch (_) { /* sandboxed */ }
  }
  function request(method, params, cb) {
    var id = nextId++;
    if (cb) pending[id] = cb;
    post({jsonrpc: "2.0", id: id, method: method, params: params || {}});
  }
  function notify(method, params) {
    post({jsonrpc: "2.0", method: method, params: params || {}});
  }
  function respond(id, result) {
    post({jsonrpc: "2.0", id: id, result: result || {}});
  }
  function respondError(id, code, message) {
    post({jsonrpc: "2.0", id: id, error: {code: code, message: message}});
  }

  // ---------------------------------------------------------------------
  // Host theming — apply theme / CSS variables / fonts / safe-area insets.
  // ---------------------------------------------------------------------
  function applyTheme(theme) {
    if (theme !== "light" && theme !== "dark") return;
    var root = document.documentElement;
    root.setAttribute("data-theme", theme);
    root.style.colorScheme = theme;
  }
  function applyStyleVariables(vars) {
    if (!vars || typeof vars !== "object") return;
    var root = document.documentElement;
    for (var k in vars) {
      if (Object.prototype.hasOwnProperty.call(vars, k) &&
          k.indexOf("--") === 0 && vars[k] != null) {
        root.style.setProperty(k, String(vars[k]));
      }
    }
  }
  function applyFonts(fontCss) {
    if (fontsApplied || !fontCss) return;
    fontsApplied = true;
    var s = document.createElement("style");
    s.textContent = String(fontCss);
    document.head.appendChild(s);
  }
  function applySafeArea(insets) {
    if (!insets) return;
    document.body.style.padding =
      (insets.top || 0) + "px " + (insets.right || 0) + "px " +
      (insets.bottom || 0) + "px " + (insets.left || 0) + "px";
  }
  function applyHostContext(ctx) {
    if (!ctx || typeof ctx !== "object") return;
    if (ctx.theme) applyTheme(ctx.theme);
    if (ctx.styles && ctx.styles.variables) applyStyleVariables(ctx.styles.variables);
    if (ctx.styles && ctx.styles.css && ctx.styles.css.fonts) applyFonts(ctx.styles.css.fonts);
    if (ctx.safeAreaInsets) applySafeArea(ctx.safeAreaInsets);
  }

  // ---------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------
  var SOURCE_LABEL = {notion: "Notion", slack: "Slack", google_drive: "Google Drive"};
  var SAFE_SCHEMES = {"http:": 1, "https:": 1, "mailto:": 1};

  function esc(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[c];
    });
  }

  function safeUrl(u) {
    if (!u) return null;
    try {
      var parsed = new URL(String(u), "https://example.invalid/");
      return SAFE_SCHEMES[parsed.protocol] ? String(u) : null;
    } catch (_) { return null; }
  }

  function sourceChip(src) {
    return '<span class="src-chip">' + esc(SOURCE_LABEL[src] || src || "") + '</span>';
  }

  function sevBadge(sev) {
    var cls = "sev-" + (({high:1,medium:1,low:1}[sev]) ? sev : "medium");
    return '<span class="sev ' + cls + '">' + esc(sev || "medium") + '</span>';
  }

  function evRefs(ids, byId) {
    if (!ids || !ids.length) return "";
    var chips = [];
    for (var i = 0; i < ids.length; i++) {
      var ev = byId[ids[i]];
      if (!ev) continue;
      var src = esc(SOURCE_LABEL[ev.source] || ev.source || "");
      chips.push('<span class="ev-ref">' + src + ' · ' + esc(ev.title || ids[i]) + '</span>');
    }
    if (!chips.length) return "";
    return '<div style="margin-top:6px;">' + chips.join("") + '</div>';
  }

  function section(title, bodyHtml, emptyMsg) {
    var inner = (bodyHtml && bodyHtml.trim())
      ? bodyHtml
      : (emptyMsg ? '<p class="empty">' + esc(emptyMsg) + '</p>' : "");
    return '<section class="card"><h2>' + esc(title) + '</h2>' + inner + '</section>';
  }

  function renderHeader(b) {
    var aliases = (b.customer_aliases || []).join(", ");
    var aliasHtml = aliases ? '<div class="alias">alias: ' + esc(aliases) + '</div>' : "";
    var bits = [];
    if (b.meeting_date) bits.push("Meeting: " + esc(b.meeting_date));
    if (b.objective) bits.push("Objective: " + esc(b.objective));
    bits.push("Period: " + esc(b.period || "30d"));
    bits.push("Sources: " + esc(b.sources_count || 0));
    var meta = '<div class="meta">'
      + bits.map(function (m) { return '<span>' + m + '</span>'; }).join("")
      + '<span>Risk: ' + sevBadge(b.risk_level || "medium") + '</span></div>';
    return '<header class="header">'
      + '<div class="label">Customer Meeting Brief</div>'
      + '<h1>' + esc(b.customer_name || "") + '</h1>'
      + aliasHtml + meta
      + '</header>';
  }

  function renderSummary(b) {
    if (!b.summary) return section("Executive Summary", "", "No summary yet.");
    var body = '<p class="summary">' + esc(b.summary) + '</p>';
    if (b.meeting_objective) {
      body += '<p class="row-sub" style="margin:10px 0 0;">Objective — ' + esc(b.meeting_objective) + '</p>';
    }
    return section("Executive Summary", body);
  }

  function renderKeyTopics(b) {
    var topics = b.key_topics || [];
    if (!topics.length) return section("Key Topics", "", "No key topics surfaced.");
    var items = topics.map(function (t) {
      var chips = (t.sources || []).map(sourceChip).join("");
      return '<li><div class="row-title">' + esc(t.title || "") + '</div>' + chips + '</li>';
    });
    return section("Key Topics", '<ul class="rows">' + items.join("") + '</ul>');
  }

  function renderRisks(b, byId) {
    var risks = b.risks || [];
    if (!risks.length) return section("Risks", "", "No risks flagged.");
    var items = risks.map(function (r) {
      return '<li><div class="row-flex">'
        + '<div class="row-title">' + esc(r.title || "") + '</div>'
        + sevBadge(r.severity || "medium")
        + '</div>' + evRefs(r.evidence_ids, byId) + '</li>';
    });
    return section("Risks", '<ul class="rows">' + items.join("") + '</ul>');
  }

  function renderOpportunities(b, byId) {
    var opps = b.opportunities || [];
    if (!opps.length) return section("Opportunities", "", "No opportunities flagged.");
    var items = opps.map(function (o) {
      return '<li><div class="row-title">' + esc(o.title || "") + '</div>'
        + evRefs(o.evidence_ids, byId) + '</li>';
    });
    return section("Opportunities", '<ul class="rows">' + items.join("") + '</ul>');
  }

  function renderQuestions(b) {
    var qs = b.suggested_questions || [];
    if (!qs.length) return section("Suggested Questions", "", "No questions suggested.");
    var items = qs.map(function (q) {
      var rat = q.rationale ? '<div class="row-sub">' + esc(q.rationale) + '</div>' : "";
      return '<li><div class="row-text">' + esc(q.text || "") + '</div>' + rat + '</li>';
    });
    return section("Suggested Questions", '<ul class="rows">' + items.join("") + '</ul>');
  }

  function renderActions(b) {
    var actions = b.recommended_actions || [];
    if (!actions.length) return section("Recommended Actions", "", "No actions recommended.");
    var items = actions.map(function (a) {
      var owner = a.owner ? '<span class="row-sub" style="margin-left:8px;">@ ' + esc(a.owner) + '</span>' : "";
      return '<li><div class="row-text">' + esc(a.title || "") + owner + '</div></li>';
    });
    return section("Recommended Actions", '<ul class="rows">' + items.join("") + '</ul>');
  }

  function renderTimeline(b) {
    var events = b.timeline || [];
    if (!events.length) return section("Recent Timeline", "", "No recent activity captured.");
    var items = events.map(function (e) {
      var sub = e.summary ? '<div class="row-sub">' + esc(e.summary) + '</div>' : "";
      return '<li class="timeline-row">'
        + '<div class="timeline-date">' + esc(e.date || "") + '</div>'
        + '<div class="timeline-body">'
        + sourceChip(e.source)
        + '<div class="row-title">' + esc(e.title || "") + '</div>' + sub
        + '</div></li>';
    });
    return section("Recent Timeline", '<ul class="rows">' + items.join("") + '</ul>');
  }

  function renderEvidence(b) {
    var ev = b.evidence || [];
    if (!ev.length) return "";
    var items = ev.slice(0, 50).map(function (e) {
      var url = safeUrl(e.url);
      var title = esc(e.title || e.id || "");
      var titleHtml = url
        ? '<a class="ev-link" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + title + '</a>'
        : title;
      return '<li>' + sourceChip(e.source)
        + '<div class="row-title">' + titleHtml + '</div>'
        + '<div class="ev-excerpt">' + esc(e.excerpt || "") + '</div></li>';
    });
    return section("Evidence (" + ev.length + ")", '<ul class="rows">' + items.join("") + '</ul>');
  }

  function render(brief) {
    if (!brief) {
      document.getElementById("root").innerHTML
        = '<p class="empty">No brief received yet.</p>';
      return;
    }
    var byId = {};
    (brief.evidence || []).forEach(function (e) { if (e && e.id) byId[e.id] = e; });
    document.getElementById("root").innerHTML =
      renderHeader(brief)
      + renderSummary(brief)
      + renderKeyTopics(brief)
      + renderRisks(brief, byId)
      + renderOpportunities(brief, byId)
      + renderQuestions(brief)
      + renderActions(brief)
      + renderTimeline(brief)
      + renderEvidence(brief);
    reportSize();
  }

  function extractBrief(params) {
    // structuredContent is the primary location; fall back to content[].text JSON.
    if (!params) return null;
    if (params.structuredContent && typeof params.structuredContent === "object") {
      return params.structuredContent;
    }
    var content = params.content;
    if (Array.isArray(content)) {
      for (var i = 0; i < content.length; i++) {
        var c = content[i];
        if (c && c.type === "text" && typeof c.text === "string") {
          try { return JSON.parse(c.text); } catch (_) { /* ignore */ }
        }
      }
    }
    return null;
  }

  // ---------------------------------------------------------------------
  // Auto-resize — report content size so the host fits the iframe.
  // ---------------------------------------------------------------------
  var lastW = -1, lastH = -1;
  function reportSize() {
    var h = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    var w = Math.max(document.body.scrollWidth, document.documentElement.scrollWidth);
    if (h === lastH && w === lastW) return;
    lastH = h; lastW = w;
    notify("ui/notifications/size-changed", {width: w, height: h});
  }
  function setupAutoResize() {
    if (typeof ResizeObserver === "undefined") return;
    var ro = new ResizeObserver(function () { reportSize(); });
    ro.observe(document.body);
    ro.observe(document.documentElement);
  }

  // ---------------------------------------------------------------------
  // Message routing: responses, host requests, host notifications.
  // ---------------------------------------------------------------------
  window.addEventListener("message", function (event) {
    if (event.source !== parentWin) return;
    var msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;

    // Response to one of our outbound requests (id present, no method).
    if (msg.id !== undefined && msg.method === undefined) {
      var cb = pending[msg.id];
      if (cb) { delete pending[msg.id]; cb(msg.error ? null : msg.result); }
      return;
    }

    // Request from the host (id + method) — must answer so it doesn't time out.
    if (msg.id !== undefined && msg.method) {
      if (msg.method === "ping" || msg.method === "ui/resource-teardown") {
        respond(msg.id, {});
      } else {
        respondError(msg.id, -32601, "Method not found: " + msg.method);
      }
      return;
    }

    // Notification from the host (method, no id).
    if (msg.method) {
      switch (msg.method) {
        case "ui/notifications/tool-result": {
          var brief = extractBrief(msg.params);
          if (brief) render(brief);
          break;
        }
        case "ui/notifications/host-context-changed":
          applyHostContext(msg.params);
          break;
        // tool-input / tool-input-partial / tool-cancelled: nothing to do —
        // the brief is delivered via tool-result.
      }
    }
  });

  // ---------------------------------------------------------------------
  // Handshake: ui/initialize -> apply hostContext -> ui/notifications/initialized.
  // ---------------------------------------------------------------------
  function connect() {
    request("ui/initialize", {
      appCapabilities: {},
      appInfo: APP_INFO,
      protocolVersion: PROTOCOL_VERSION
    }, function (result) {
      if (result) applyHostContext(result.hostContext);
      notify("ui/notifications/initialized");
      initialized = true;
      setupAutoResize();
      reportSize();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", connect);
  } else {
    connect();
  }
})();
</script>
</body>
</html>
"""


def render_brief_widget_html() -> str:
    """Return the iframe shell HTML for MCP Apps / mcp-ui-aware hosts.

    The HTML is data-less by design; the brief content arrives at run-time as
    the tool's ``structuredContent`` via the ``ui/notifications/tool-result``
    message that the host sends *after* the iframe completes the MCP Apps
    ``ui/initialize`` handshake.
    """
    return _WIDGET_HTML
