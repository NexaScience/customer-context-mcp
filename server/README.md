# customer-context-mcp (server)

MCP server + HTTP bridge for the Customer Context Meeting Prep Assistant.

## Install

Dependencies are managed with [uv](https://docs.astral.sh/uv/) and pinned in
`uv.lock`.

```bash
cd server
uv sync
```

## Run

HTTP API + serves the iframe app statically (production build expected at `../app/dist`):

```bash
uv run customer-context-mcp http --host 127.0.0.1 --port 8787
```

MCP stdio server (for Claude Desktop / Claude Code):

```bash
uv run customer-context-mcp mcp
```

## Environment

See `../.env.example` for required credentials.
