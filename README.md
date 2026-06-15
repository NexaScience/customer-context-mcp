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

`generate_meeting_brief` returns two content items:

1. A `TextContent` with the brief as JSON.
2. An `EmbeddedResource` following the [mcp-ui](https://mcpui.dev) convention —
   URI `ui://customer-context-mcp/meeting-brief/<id>`, MIME type
   `text/html;profile=mcp-app`, containing a self-contained HTML dashboard
   (executive summary, risks, opportunities, suggested questions, recommended
   actions, timeline, evidence).

mcp-ui-aware hosts render this inline as a sandboxed iframe; other MCP hosts
expose it as a regular embedded resource alongside the JSON. The HTML is
fully static — no network calls, no external assets — so it works in any
sandboxed iframe without further configuration.

Implementation lives in [`server/customer_context_mcp/ui_app.py`](server/customer_context_mcp/ui_app.py)
and uses only `mcp.types.EmbeddedResource` + `TextResourceContents` (no
additional dependency).

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
