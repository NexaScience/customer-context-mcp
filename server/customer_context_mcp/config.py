"""Centralised env-driven config.

Only credentials/secrets are read from the environment. Operational defaults
(model id, HTTP host/port, file paths) are hardcoded constants below — change
them in source rather than via env vars.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

GEMINI_MODEL = "gemini-3.1-flash-lite"
HTTP_HOST = "127.0.0.1"
HTTP_PORT = 8787
GOOGLE_CREDENTIALS_FILE = "./credentials.json"
GOOGLE_TOKEN_FILE = "./token.json"


def _env(name: str) -> str | None:
    val = os.environ.get(name)
    if val is None or val == "":
        return None
    return val


def _env_list(name: str) -> tuple[str, ...]:
    raw = _env(name)
    if not raw:
        return ()
    return tuple(p.strip() for p in raw.replace(",", " ").split() if p.strip())


@dataclass(frozen=True)
class Config:
    gemini_api_key: str | None = _env("GEMINI_API_KEY")
    notion_token: str | None = _env("NOTION_TOKEN")
    # Notion databases (IDs from the DB URL) to query structurally — rows are
    # matched on title + all property values, with body included. When empty,
    # the Notion source falls back to the title-only search API.
    notion_database_ids: tuple[str, ...] = _env_list("NOTION_DATABASE_IDS")
    # search.messages requires a Slack *user* token (xoxp-) with search:read.
    # A bot token (xoxb-) cannot call search; it is only a fallback.
    slack_user_token: str | None = _env("SLACK_USER_TOKEN")
    slack_bot_token: str | None = _env("SLACK_BOT_TOKEN")


CONFIG = Config()
