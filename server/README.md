# customer-context-mcp (server)

MCP server + HTTP bridge for the Customer Context Meeting Prep Assistant.

## Install

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

HTTP API + serves the iframe app statically (production build expected at `../app/dist`):

```bash
customer-context-mcp http --host 127.0.0.1 --port 8787
```

MCP stdio server (for Claude Desktop / Claude Code):

```bash
customer-context-mcp mcp
```

## Environment

See `../.env.example` for required credentials.
