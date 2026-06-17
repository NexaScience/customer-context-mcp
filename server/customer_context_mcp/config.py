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


@dataclass(frozen=True)
class Config:
    gemini_api_key: str | None = _env("GEMINI_API_KEY")
    notion_token: str | None = _env("NOTION_TOKEN")
    slack_bot_token: str | None = _env("SLACK_BOT_TOKEN")


CONFIG = Config()
