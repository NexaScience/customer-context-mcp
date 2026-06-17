# Customer Context MCP — Meeting Prep Assistant

An MCP server **and** an iframe MCP App that helps sales / CS / AM teams prepare for customer
meetings. Pulls customer-related context from **Notion**, **Slack**, and **Google Drive**,
analyses it with an LLM, and renders an evidence-backed customer brief in the iframe UI.

The MCP server exposes 5 tools. The iframe MCP App is a React dashboard that mirrors those
tools over HTTP so you can demo the experience end-to-end.

```
┌──────────────────────────────────────────────────────────────┐
│ Customer Meeting Brief    iframe MCP App                     │
├──────────────────────────────────────────────────────────────┤
│ Customer / Meeting / Sources / Last Updated                  │
├───────────────────────────────┬──────────────────────────────┤
│ Executive Summary             │ Ask about this customer       │
│ Key Topics    |   Risks       │ Suggested Questions           │
│ Opportunities | Actions       │ Evidence Drawer               │
│ Recent Timeline               │                              │
└───────────────────────────────┴──────────────────────────────┘
```

## Project layout

```
customer-context-mcp/
├── server/                          Python MCP server + HTTP bridge
│   ├── pyproject.toml
│   └── customer_context_mcp/
│       ├── server.py                MCP stdio server
│       ├── api/app.py               FastAPI bridge (serves iframe + tools)
│       ├── cli.py                   `customer-context-mcp {mcp,http}`
│       ├── tools/                   search / brief / ask / evidence / draft
│       ├── sources/                 Notion, Slack, Google Drive
│       └── llm.py                   Anthropic-backed analysis
├── app/                             iframe MCP App (Vite + React + Tailwind)
│   └── src/
│       ├── App.tsx
│       └── components/              Header / Risks / EvidenceDrawer / …
├── .env.example
└── customer_context_mcp_meeting_prep_requirements.md
```

## MCP tools

| Tool | Purpose |
|---|---|
| `search_customer_context` | Notion + Slack + Google Drive search; returns Evidence[] |
| `generate_meeting_brief`  | Runs search, then LLM-structures a meeting brief. Returns JSON **and** an MCP App (see below) |
| `ask_meeting_brief`       | Evidence-grounded follow-up Q&A |
| `get_evidence_detail`     | Returns one Evidence record by id |
| `draft_customer_message`  | Drafts follow-up email / internal Slack summary / agenda |

## MCP Apps (inline iframe)

`generate_meeting_brief` carries **three** payloads so both major MCP-App
regulations render the same brief:

| Payload | Consumer | Shape |
|---|---|---|
| `structured_content` | **ChatGPT Apps** — delivered to the registered widget iframe at run-time via `ui/notifications/tool-result` postMessage | brief JSON |
| `content[0]` (`TextContent`) | Plain MCP clients (no UI rendering) | brief JSON as text |
| `content[1]` (`UIResource`) | **mcp-ui-aware hosts** that render inline `ui://` resources | self-contained HTML dashboard |

The tool also declares the widget on its `_meta`:

```jsonc
{
  "ui": {"resourceUri": "ui://customer-context-mcp/meeting-brief.html"},
  "openai/outputTemplate": "ui://customer-context-mcp/meeting-brief.html"
}
```

…and registers the widget itself as an MCP Resource with MIME
`text/html;profile=mcp-app`. The widget HTML is a self-contained JS shell that
implements the MCP Apps view-side protocol: on load it completes the
`ui/initialize` → `ui/notifications/initialized` handshake (applying the host's
theme / CSS variables / fonts / safe-area from `hostContext`), and **only then**
does the host deliver the brief via `ui/notifications/tool-result`, which the
shell renders from `structuredContent`. It also answers host `ping` /
`ui/resource-teardown` requests and reports `ui/notifications/size-changed` so
the host can fit the iframe to the content. Skipping the handshake leaves the
iframe blank on strict hosts (e.g. ChatGPT).

| Host | Render path |
|---|---|
| **ChatGPT Apps** | Reads `_meta.ui.resourceUri` → fetches the registered `ui://…meeting-brief.html` resource → renders iframe → iframe completes the `ui/initialize` handshake → host delivers `structuredContent` via `ui/notifications/tool-result` → JS shell paints the dashboard |
| **mcp-ui hosts** (e.g. mcp-ui inspector, Claude with mcp-ui) | Sees `content[1]` `UIResource` (already-rendered HTML) inline in the tool result |
| **Plain MCP clients** | Sees `content[0]` `TextContent` JSON as plain output |

### Implementation map

| File | Role |
|---|---|
| [`server/customer_context_mcp/widget.py`](server/customer_context_mcp/widget.py) | Iframe shell HTML + MCP Apps view-side protocol (handshake, host-context theming, tool-result rendering, auto-resize) for ChatGPT Apps |
| [`server/customer_context_mcp/ui_app.py`](server/customer_context_mcp/ui_app.py) | Server-side renderer that produces the inline `UIResource` for mcp-ui hosts (via `mcp_ui_server.create_ui_resource`) |
| [`server/customer_context_mcp/server.py`](server/customer_context_mcp/server.py) | Tool / resource registration via FastMCP's `AppConfig`, `UI_MIME_TYPE`, and `ToolResult` |

## Setup

### 1. Credentials

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY, NOTION_TOKEN, SLACK_BOT_TOKEN
# place Google Drive OAuth client at ./credentials.json
```

Required scopes:

- **Notion**: integration with read access to relevant pages (share the integration with the pages you want searched).
- **Slack** bot scopes: `channels:history`, `channels:read`, `groups:history`, `groups:read`, `im:history`, `mpim:history`, `search:read`, `users:read`.
- **Google Drive**: OAuth 2.0 client of type *Desktop app*. The first run opens a browser to consent and writes `token.json`.

### 2. Server

Python dependencies are managed with [uv](https://docs.astral.sh/uv/) and
pinned in `server/uv.lock`. Install it once with
`curl -LsSf https://astral.sh/uv/install.sh | sh`.

```bash
cd server
uv sync            # creates .venv and installs from uv.lock
```

Subsequent commands use `uv run` so the project venv is picked up
automatically:

```bash
uv run customer-context-mcp --help
```

If you prefer a sourced venv: `source .venv/bin/activate`.

### 3. App (iframe)

```bash
cd app
npm install
npm run build           # outputs to app/dist (served by the HTTP bridge)
```

## Run

### iframe MCP App + HTTP bridge

```bash
cd server
uv run customer-context-mcp http --host 127.0.0.1 --port 8787
# open http://127.0.0.1:8787
```

For app development with HMR:

```bash
# terminal 1
cd server && uv run customer-context-mcp http
# terminal 2
cd app && npm run dev    # http://127.0.0.1:5173, proxies /api to :8787
```

### MCP stdio server (Claude Desktop / Claude Code)

```jsonc
// ~/.config/claude/claude_desktop_config.json or settings.json
{
  "mcpServers": {
    "customer-context": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/customer-context-mcp/server",
        "run",
        "customer-context-mcp",
        "mcp"
      ]
    }
  }
}
```

## Demo prompt

```text
A社との明日の商談に向けて、Notion、Slack、Google Driveの情報をもとに、
状況・懸念点・確認すべき質問・提案すべき内容を整理してください。
```

The MCP host can call `generate_meeting_brief({customer_name: "A社", ...})`. The same data
renders in the iframe MCP App dashboard at the URL above.
