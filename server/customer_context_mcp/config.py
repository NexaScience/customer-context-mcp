"""Centralised env-driven config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def _env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name, default)
    if val is None or val == "":
        return None
    return val


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None = _env("ANTHROPIC_API_KEY")
    anthropic_model: str = _env("ANTHROPIC_MODEL", "claude-opus-4-7") or "claude-opus-4-7"

    notion_token: str | None = _env("NOTION_TOKEN")

    slack_bot_token: str | None = _env("SLACK_BOT_TOKEN")
    slack_channels: tuple[str, ...] = tuple(
        c.strip() for c in (_env("SLACK_CHANNELS") or "").split(",") if c.strip()
    )

    google_credentials_file: str = _env("GOOGLE_CREDENTIALS_FILE", "./credentials.json") or "./credentials.json"
    google_token_file: str = _env("GOOGLE_TOKEN_FILE", "./token.json") or "./token.json"

    host: str = _env("HOST", "127.0.0.1") or "127.0.0.1"
    port: int = int(_env("PORT", "8787") or "8787")
    allowed_origins: tuple[str, ...] = tuple(
        o.strip() for o in (_env("ALLOWED_ORIGINS") or "").split(",") if o.strip()
    )
    mcp_allowed_hosts: tuple[str, ...] = tuple(
        h.strip() for h in (_env("MCP_ALLOWED_HOSTS") or "").split(",") if h.strip()
    )


CONFIG = Config()
