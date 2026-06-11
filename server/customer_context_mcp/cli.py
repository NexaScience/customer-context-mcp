"""CLI entry point — stdio MCP server or HTTP (Remote MCP + iframe)."""

from __future__ import annotations

import argparse
import logging

from .config import CONFIG


def main() -> None:
    parser = argparse.ArgumentParser(prog="customer-context-mcp")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_mcp = sub.add_parser("mcp", help="Run MCP stdio server")
    p_mcp.set_defaults(func=_run_mcp)

    p_http = sub.add_parser("http", help="Run HTTP server (Remote MCP + iframe)")
    p_http.add_argument("--host", default=CONFIG.host)
    p_http.add_argument("--port", type=int, default=CONFIG.port)
    p_http.add_argument("--reload", action="store_true")
    p_http.set_defaults(func=_run_http)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args.func(args)


def _run_mcp(_args: argparse.Namespace) -> None:
    from .server import mcp

    mcp.run(transport="stdio")


def _run_http(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run(
        "customer_context_mcp.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
