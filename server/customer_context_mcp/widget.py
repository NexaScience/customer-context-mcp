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
     completes** (see modelcontextprotocol/ext-apps `App.connect`, and
     anthropics/claude-ai-mcp#149).
  2. **Tool result** — handles ``ui/notifications/tool-result``, reading
     ``structuredContent`` (falling back to the JSON in ``content[].text``) and
     rendering the meeting-brief dashboard.
  3. **Interactivity** — the "Ask about this customer" box and the suggested
     questions call the server's ``ask_meeting_brief`` tool via ``tools/call``
     (proxied by the host), and "View evidence" links jump to the matching
     entry in the Evidence Drawer.
  4. **Host context** — handles ``ui/notifications/host-context-changed`` to
     react to live theme / style changes, answers host ``ping`` /
     ``ui/resource-teardown`` requests, and reports
     ``ui/notifications/size-changed`` via ``ResizeObserver``.
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
<title>Customer Meeting Brief</title>
<style>
  :root{color-scheme:light dark;
    --bg:var(--color-background-primary,#f7f8fa);
    --card:var(--color-background-secondary,#ffffff);
    --ink:var(--color-text-primary,#0f172a);
    --ink2:var(--color-text-secondary,#64748b);
    --ink3:var(--color-text-tertiary,#94a3b8);
    --line:var(--color-border-primary,#e5e7eb);
    --line2:var(--color-border-secondary,#eef2f6);
    --accent:var(--color-text-info,#2563eb);
    --radius:var(--border-radius-lg,16px);
    --sans:var(--font-sans,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif);}
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:var(--sans);}
  .page{max-width:1500px;margin:0 auto;}
  .empty{color:var(--ink3);font-size:13px;margin:0;}

  /* top bar */
  .topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;
    flex-wrap:wrap;padding:20px 28px;background:var(--card);border-bottom:1px solid var(--line);}
  .topbar h1{margin:0;font-size:28px;font-weight:800;letter-spacing:-0.02em;}
  .topbar .sub{margin-top:2px;font-size:13px;color:var(--ink2);}
  .topbar .sources{display:flex;gap:10px;flex-wrap:wrap;}
  .pill-out{display:inline-flex;align-items:center;padding:6px 14px;border-radius:999px;
    border:1px solid var(--line);background:transparent;font-size:13px;color:var(--ink2);white-space:nowrap;}

  .body{padding:22px 28px 32px;}

  /* customer card */
  .customer{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;
    background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 22px;margin-bottom:18px;}
  .customer h2{margin:0;font-size:22px;font-weight:700;}
  .customer .sub{margin-top:2px;font-size:13px;color:var(--ink2);}
  .customer .pills{display:flex;gap:10px;flex-wrap:wrap;}
  .tag{display:inline-flex;align-items:center;padding:6px 14px;border-radius:999px;border:1px solid var(--line);
    font-size:13px;background:transparent;white-space:nowrap;}
  .tag-risk-high{border-color:#fecaca;color:#b91c1c;}
  .tag-risk-medium{border-color:#fde68a;color:#b45309;}
  .tag-risk-low{border-color:#bbf7d0;color:#15803d;}
  .tag-blue{border-color:#bfdbfe;color:#1d4ed8;}
  .tag-green{border-color:#bbf7d0;color:#15803d;}
  .tag-gray{border-color:var(--line);color:var(--ink2);}

  /* layout grid */
  .grid{display:grid;grid-template-columns:1.9fr 1fr;gap:16px;align-items:start;}
  .col{display:flex;flex-direction:column;gap:16px;min-width:0;}
  .row2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
  /* Collapse the main/side split first, then the inner 2-up pairs. Uses the
     iframe's own width, so the layout adapts to whatever width the host gives. */
  @media (max-width:760px){.grid{grid-template-columns:1fr;}}
  @media (max-width:560px){.row2{grid-template-columns:1fr;}}

  .card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;}
  .card h3{margin:0 0 14px;font-size:17px;font-weight:700;letter-spacing:-0.01em;}
  .card.summary p{margin:0;font-size:14px;line-height:1.7;color:var(--ink);}

  ul.rows{list-style:none;padding:0;margin:0;}
  ul.rows li{padding:9px 0;}
  .topic{display:flex;align-items:center;gap:10px;justify-content:space-between;}
  .topic .name{display:flex;align-items:center;gap:10px;font-size:14px;font-weight:500;min-width:0;}
  .dot{width:8px;height:8px;border-radius:50%;background:var(--accent);flex:0 0 auto;}
  .topic .src{font-size:12px;color:var(--ink3);white-space:nowrap;}

  .risk{display:flex;gap:12px;padding:9px 0;align-items:flex-start;}
  .sev{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;min-width:44px;padding:3px 10px;
    border-radius:999px;font-size:12px;font-weight:600;}
  .sev-high{background:#fee2e2;color:#b91c1c;}
  .sev-medium{background:#fef3c7;color:#b45309;}
  .sev-low{background:#dcfce7;color:#15803d;}
  .risk .rtitle{font-size:14px;font-weight:600;color:var(--ink);}
  .risk .rlink{display:inline-block;margin-top:2px;font-size:13px;color:var(--accent);
    text-decoration:none;cursor:pointer;background:none;border:none;padding:0;}
  .risk .rlink:hover{text-decoration:underline;}

  .opp{display:block;padding:11px 14px;border-radius:10px;background:#f0fdf4;border:1px solid #dcfce7;
    color:#166534;font-size:14px;margin-bottom:10px;}
  ol.actions{margin:0;padding-left:20px;}
  ol.actions li{font-size:14px;line-height:1.6;padding:4px 0;color:var(--ink);}

  .tl{display:flex;gap:14px;padding:6px 0;font-size:14px;}
  .tl .date{color:var(--ink2);white-space:nowrap;font-variant-numeric:tabular-nums;}
  .tl .txt{color:var(--ink);}

  /* sidebar */
  textarea.ask{width:100%;min-height:84px;resize:vertical;border:1px solid var(--line);border-radius:12px;
    padding:12px 14px;font:inherit;font-size:14px;background:var(--bg);color:var(--ink);}
  textarea.ask:focus{outline:2px solid var(--accent);outline-offset:0;border-color:var(--accent);}
  .ask-row{display:flex;justify-content:flex-end;margin-top:12px;}
  .btn{appearance:none;border:none;cursor:pointer;font:inherit;font-weight:600;font-size:14px;
    padding:9px 22px;border-radius:10px;background:#0f172a;color:#fff;}
  .btn:hover{background:#1e293b;}
  .btn:disabled{opacity:.5;cursor:default;}
  .answer{margin-top:14px;font-size:14px;line-height:1.7;white-space:pre-wrap;color:var(--ink);}
  .answer.note{color:var(--ink2);font-size:13px;}

  .suggest{display:block;width:100%;text-align:left;padding:11px 14px;border-radius:10px;border:1px solid var(--line);
    background:var(--bg);color:var(--ink);font:inherit;font-size:13px;margin-bottom:10px;cursor:pointer;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .suggest:hover{border-color:var(--accent);color:var(--accent);}

  ul.evlist{list-style:disc;margin:0;padding-left:20px;}
  ul.evlist li{padding:6px 0;font-size:14px;line-height:1.5;}
  ul.evlist li::marker{color:var(--ink3);}
  ul.evlist li.hi{outline:2px solid var(--accent);outline-offset:3px;border-radius:4px;}
  .src-notion{color:#111827;} .src-slack{color:#4a154b;} .src-google_drive{color:#1a73e8;}
  .ev-src{font-size:12px;font-weight:700;margin-right:6px;}
  .ev-link{color:var(--accent);text-decoration:none;font-weight:600;}
  .ev-link:hover{text-decoration:underline;}
  .ev-ex{display:block;font-size:13px;color:var(--ink2);margin-top:2px;line-height:1.55;}
</style>
</head>
<body>
<div class="page" id="root">
  <div class="body"><p class="empty" id="empty-state">Waiting for meeting brief…</p></div>
</div>
<script>
(function () {
  "use strict";

  // ---------------------------------------------------------------------
  // MCP Apps view-side protocol over postMessage (no SDK dependency).
  // ---------------------------------------------------------------------
  var PROTOCOL_VERSION = "2026-01-26";
  var APP_INFO = {name: "customer-context-meeting-brief", version: "0.2.0"};
  var parentWin = window.parent;
  var nextId = 1;
  var pending = {};          // outbound request id -> callback(result|null)
  var initialized = false;
  var fontsApplied = false;
  var currentBrief = null;

  function post(msg) { try { parentWin.postMessage(msg, "*"); } catch (_) {} }
  function request(method, params, cb) {
    var id = nextId++;
    if (cb) pending[id] = cb;
    post({jsonrpc: "2.0", id: id, method: method, params: params || {}});
  }
  function notify(method, params) { post({jsonrpc: "2.0", method: method, params: params || {}}); }
  function respond(id, result) { post({jsonrpc: "2.0", id: id, result: result || {}}); }
  function respondError(id, code, message) { post({jsonrpc: "2.0", id: id, error: {code: code, message: message}}); }

  // Call a tool on the originating MCP server (proxied by the host).
  function callServerTool(name, args, cb) {
    request("tools/call", {name: name, arguments: args || {}}, cb);
  }
  function parseToolResult(result) {
    if (!result) return null;
    if (result.structuredContent && typeof result.structuredContent === "object") return result.structuredContent;
    var c = result.content;
    if (Array.isArray(c)) {
      for (var i = 0; i < c.length; i++) {
        if (c[i] && c[i].type === "text" && typeof c[i].text === "string") {
          try { return JSON.parse(c[i].text); } catch (_) { return {answer: c[i].text}; }
        }
      }
    }
    return null;
  }

  // ---------------------------------------------------------------------
  // Host theming
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
      if (Object.prototype.hasOwnProperty.call(vars, k) && k.indexOf("--") === 0 && vars[k] != null) {
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
      (insets.top || 0) + "px " + (insets.right || 0) + "px " + (insets.bottom || 0) + "px " + (insets.left || 0) + "px";
  }
  function applyHostContext(ctx) {
    if (!ctx || typeof ctx !== "object") return;
    if (ctx.theme) applyTheme(ctx.theme);
    if (ctx.styles && ctx.styles.variables) applyStyleVariables(ctx.styles.variables);
    if (ctx.styles && ctx.styles.css && ctx.styles.css.fonts) applyFonts(ctx.styles.css.fonts);
    if (ctx.safeAreaInsets) applySafeArea(ctx.safeAreaInsets);
  }

  // ---------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------
  var SOURCE_LABEL = {notion: "Notion", slack: "Slack", google_drive: "Google Drive"};
  var SAFE_SCHEMES = {"http:": 1, "https:": 1, "mailto:": 1};
  var PERIOD_LABEL = {"7d": "7 days", "30d": "30 days", "90d": "90 days", "all": "All time"};

  function esc(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[c];
    });
  }
  function safeUrl(u) {
    if (!u) return null;
    try { var p = new URL(String(u), "https://example.invalid/"); return SAFE_SCHEMES[p.protocol] ? String(u) : null; }
    catch (_) { return null; }
  }
  function srcLabel(s) { return SOURCE_LABEL[s] || s || ""; }
  function sevClass(s) { return ({high:1,medium:1,low:1}[s]) ? s : "medium"; }
  function sevLabel(s) { return ({high:"High",medium:"Med",low:"Low"})[sevClass(s)]; }

  // ---------------------------------------------------------------------
  // Rendering — dashboard layout
  // ---------------------------------------------------------------------
  function renderTopbar(b) {
    var chips = ["notion", "slack", "google_drive"]
      .map(function (s) { return '<span class="pill-out">' + esc(SOURCE_LABEL[s]) + '</span>'; }).join("");
    return '<header class="topbar">'
      + '<div><h1>Customer Meeting Brief</h1><div class="sub">iframe MCP App / Meeting Preparation Assistant</div></div>'
      + '<div class="sources">' + chips + '</div></header>';
  }

  function renderCustomer(b) {
    var meetingBits = [];
    if (b.objective) meetingBits.push(esc(b.objective));
    if (b.meeting_date) meetingBits.push(esc(b.meeting_date));
    var sub = meetingBits.length ? '<div class="sub">Meeting: ' + meetingBits.join(" / ") + '</div>' : "";
    var risk = sevClass(b.risk_level);
    var period = PERIOD_LABEL[b.period] || esc(b.period || "30d");
    var tags = ''
      + '<span class="tag tag-risk-' + risk + '">Risk: ' + esc(({high:"High",medium:"Medium",low:"Low"})[risk]) + '</span>'
      + '<span class="tag tag-blue">Sources: ' + esc(b.sources_count || 0) + ' items</span>'
      + '<span class="tag tag-green">Period: ' + period + '</span>'
      + '<span class="tag tag-gray">Updated now</span>';
    return '<section class="customer"><div><h2>' + esc(b.customer_name || "") + '</h2>' + sub + '</div>'
      + '<div class="pills">' + tags + '</div></section>';
  }

  function cardSummary(b) {
    var body = b.summary ? '<p>' + esc(b.summary) + '</p>' : '<p class="empty">No summary yet.</p>';
    return '<section class="card summary"><h3>Executive Summary</h3>' + body + '</section>';
  }

  function cardKeyTopics(b) {
    var topics = b.key_topics || [];
    var inner = topics.length ? '<ul class="rows">' + topics.map(function (t) {
      var srcs = (t.sources || []).map(srcLabel).join(" / ");
      return '<li class="topic"><span class="name"><span class="dot"></span>' + esc(t.title || "") + '</span>'
        + '<span class="src">' + esc(srcs) + '</span></li>';
    }).join("") + '</ul>' : '<p class="empty">No key topics surfaced.</p>';
    return '<section class="card"><h3>Key Topics</h3>' + inner + '</section>';
  }

  function cardRisks(b) {
    var risks = b.risks || [];
    var inner = risks.length ? '<ul class="rows">' + risks.map(function (r) {
      var ids = (r.evidence_ids || []).filter(Boolean);
      var link = ids.length
        ? '<button class="rlink" data-action="view-evidence" data-ids="' + esc(ids.join(",")) + '">View evidence →</button>'
        : "";
      return '<li class="risk"><span class="sev sev-' + sevClass(r.severity) + '">' + esc(sevLabel(r.severity)) + '</span>'
        + '<span><span class="rtitle">' + esc(r.title || "") + '</span>'
        + (link ? '<br>' + link : '') + '</span></li>';
    }).join("") + '</ul>' : '<p class="empty">No risks flagged.</p>';
    return '<section class="card"><h3>Risks</h3>' + inner + '</section>';
  }

  function cardOpportunities(b) {
    var opps = b.opportunities || [];
    var inner = opps.length ? opps.map(function (o) {
      return '<span class="opp">' + esc(o.title || "") + '</span>';
    }).join("") : '<p class="empty">No opportunities flagged.</p>';
    return '<section class="card"><h3>Opportunities</h3>' + inner + '</section>';
  }

  function cardActions(b) {
    var actions = b.recommended_actions || [];
    var inner = actions.length ? '<ol class="actions">' + actions.map(function (a) {
      var owner = a.owner ? ' <span class="src">@ ' + esc(a.owner) + '</span>' : "";
      return '<li>' + esc(a.title || "") + owner + '</li>';
    }).join("") + '</ol>' : '<p class="empty">No actions recommended.</p>';
    return '<section class="card"><h3>Recommended Actions</h3>' + inner + '</section>';
  }

  function cardTimeline(b) {
    var events = b.timeline || [];
    var inner = events.length ? '<ul class="rows">' + events.map(function (e) {
      var txt = esc(srcLabel(e.source)) + ": " + esc(e.title || "");
      return '<li class="tl"><span class="date">' + esc(e.date || "") + '</span><span class="txt">' + txt + '</span></li>';
    }).join("") + '</ul>' : '<p class="empty">No recent activity captured.</p>';
    return '<section class="card"><h3>Recent Timeline</h3>' + inner + '</section>';
  }

  function cardAsk(b) {
    return '<section class="card"><h3>Ask about this customer</h3>'
      + '<textarea class="ask" id="ask-input" placeholder="この顧客について質問する…"></textarea>'
      + '<div class="ask-row"><button class="btn" id="ask-btn" data-action="ask">Ask</button></div>'
      + '<div class="answer" id="ask-answer"></div></section>';
  }

  function cardSuggested(b) {
    var qs = b.suggested_questions || [];
    if (!qs.length) return '';
    var inner = qs.map(function (q) {
      var text = q.text || "";
      return '<button class="suggest" data-action="suggest" data-q="' + esc(text) + '" title="' + esc(text) + '">'
        + esc(text) + '</button>';
    }).join("");
    return '<section class="card"><h3>Suggested Questions</h3>' + inner + '</section>';
  }

  function cardEvidence(b) {
    var ev = b.evidence || [];
    if (!ev.length) return '<section class="card"><h3>Evidence Drawer</h3><p class="empty">No evidence collected.</p></section>';
    var items = ev.slice(0, 50).map(function (e) {
      var url = safeUrl(e.url);
      var title = esc(e.title || e.id || "");
      var link = url
        ? '<a class="ev-link" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + title + '</a>'
        : '<span class="ev-link">' + title + '</span>';
      var ex = e.excerpt ? '<span class="ev-ex">' + esc(e.excerpt) + '</span>' : '';
      return '<li id="ev-' + esc(e.id || "") + '">'
        + '<span class="ev-src src-' + esc(e.source || "") + '">' + esc(srcLabel(e.source)) + '</span>'
        + link + ex + '</li>';
    }).join("");
    return '<section class="card"><h3>Evidence Drawer</h3><ul class="evlist">' + items + '</ul></section>';
  }

  function render(brief) {
    currentBrief = brief;
    if (!brief) {
      document.getElementById("root").innerHTML = '<div class="body"><p class="empty">No brief received yet.</p></div>';
      return;
    }
    document.getElementById("root").innerHTML =
      renderTopbar(brief)
      + '<div class="body">'
      + renderCustomer(brief)
      + '<div class="grid">'
      +   '<div class="col">'
      +     cardSummary(brief)
      +     '<div class="row2">' + cardKeyTopics(brief) + cardRisks(brief) + '</div>'
      +     '<div class="row2">' + cardOpportunities(brief) + cardActions(brief) + '</div>'
      +     cardTimeline(brief)
      +   '</div>'
      +   '<div class="col">'
      +     cardAsk(brief)
      +     cardSuggested(brief)
      +     cardEvidence(brief)
      +   '</div>'
      + '</div></div>';
    reportSize();
  }

  function extractBrief(params) {
    if (!params) return null;
    if (params.structuredContent && typeof params.structuredContent === "object") return params.structuredContent;
    var content = params.content;
    if (Array.isArray(content)) {
      for (var i = 0; i < content.length; i++) {
        var c = content[i];
        if (c && c.type === "text" && typeof c.text === "string") {
          try { return JSON.parse(c.text); } catch (_) {}
        }
      }
    }
    return null;
  }

  // ---------------------------------------------------------------------
  // Interactivity — Ask box, suggested questions, evidence jump
  // ---------------------------------------------------------------------
  function setAnswer(html, isNote) {
    var el = document.getElementById("ask-answer");
    if (!el) return;
    el.className = "answer" + (isNote ? " note" : "");
    el.innerHTML = html;
    reportSize();
  }

  function submitAsk(question) {
    question = (question || "").trim();
    if (!question) return;
    if (!currentBrief || !currentBrief.id) { setAnswer("ブリーフIDが見つかりません。", true); return; }
    var btn = document.getElementById("ask-btn");
    if (btn) btn.disabled = true;
    setAnswer("回答を生成中…", true);
    callServerTool("ask_meeting_brief", {brief_id: currentBrief.id, question: question}, function (result) {
      if (btn) btn.disabled = false;
      if (result === null) {
        setAnswer("このホストでは追質問機能（サーバーツール呼び出し）が利用できません。", true);
        return;
      }
      var data = parseToolResult(result);
      if (data && typeof data.answer === "string") setAnswer(esc(data.answer));
      else if (data && data.error) setAnswer(esc(String(data.error)), true);
      else setAnswer("回答を取得できませんでした。", true);
    });
  }

  function jumpToEvidence(ids) {
    var first = (ids || "").split(",")[0];
    if (!first) return;
    var el = document.getElementById("ev-" + first);
    if (!el) return;
    el.scrollIntoView({behavior: "smooth", block: "center"});
    (ids || "").split(",").forEach(function (id) {
      var e = document.getElementById("ev-" + id);
      if (e) { e.classList.add("hi"); setTimeout(function () { e.classList.remove("hi"); }, 2200); }
    });
  }

  document.addEventListener("click", function (event) {
    var t = event.target;
    while (t && t !== document.body && !t.getAttribute("data-action")) t = t.parentElement;
    if (!t || t === document.body) return;
    var action = t.getAttribute("data-action");
    if (action === "ask") {
      var input = document.getElementById("ask-input");
      submitAsk(input ? input.value : "");
    } else if (action === "suggest") {
      var q = t.getAttribute("data-q") || "";
      var box = document.getElementById("ask-input");
      if (box) box.value = q;
      submitAsk(q);
    } else if (action === "view-evidence") {
      jumpToEvidence(t.getAttribute("data-ids") || "");
    }
  });

  document.addEventListener("keydown", function (event) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      var input = document.getElementById("ask-input");
      if (input && document.activeElement === input) submitAsk(input.value);
    }
  });

  // ---------------------------------------------------------------------
  // Auto-resize
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
  // Message routing
  // ---------------------------------------------------------------------
  window.addEventListener("message", function (event) {
    if (event.source !== parentWin) return;
    var msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;

    if (msg.id !== undefined && msg.method === undefined) {       // response to our request
      var cb = pending[msg.id];
      if (cb) { delete pending[msg.id]; cb(msg.error ? null : msg.result); }
      return;
    }
    if (msg.id !== undefined && msg.method) {                     // request from host
      if (msg.method === "ping" || msg.method === "ui/resource-teardown") respond(msg.id, {});
      else respondError(msg.id, -32601, "Method not found: " + msg.method);
      return;
    }
    if (msg.method) {                                             // notification from host
      switch (msg.method) {
        case "ui/notifications/tool-result": {
          var brief = extractBrief(msg.params);
          if (brief) render(brief);
          break;
        }
        case "ui/notifications/host-context-changed":
          applyHostContext(msg.params);
          break;
      }
    }
  });

  // ---------------------------------------------------------------------
  // Handshake: ui/initialize -> apply hostContext -> ui/notifications/initialized
  // ---------------------------------------------------------------------
  function connect() {
    request("ui/initialize", {
      appCapabilities: {}, appInfo: APP_INFO, protocolVersion: PROTOCOL_VERSION
    }, function (result) {
      if (result) applyHostContext(result.hostContext);
      notify("ui/notifications/initialized");
      initialized = true;
      setupAutoResize();
      reportSize();
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", connect);
  else connect();
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
