"""FastAPI app — hosts the Remote MCP endpoint and the iframe MCP App.

Endpoints:
  - /mcp/*  : MCP Streamable HTTP transport  (for Claude Desktop / Remote MCP)
  - /api/*  : thin REST wrappers used by the iframe app
  - /       : static files of the iframe app (built Vite output at ../app/dist)
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..config import CONFIG
from ..server import mcp
from ..store import STORE
from ..tools import (
    ask_meeting_brief,
    draft_customer_message,
    generate_meeting_brief,
    get_evidence_detail,
    search_customer_context,
)
from ..types import Period, Source

log = logging.getLogger(__name__)

APP_DIST = Path(__file__).resolve().parents[3] / "app" / "dist"


@contextlib.asynccontextmanager
async def _lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(lifespan=_lifespan)


_allowed = {
    f"http://127.0.0.1:{CONFIG.port}",
    f"http://localhost:{CONFIG.port}",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
}
_allowed.update(CONFIG.allowed_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_allowed),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


# ---------- Remote MCP (Streamable HTTP) ----------
app.mount("/mcp", mcp.streamable_http_app())


# ---------- REST endpoints for the iframe ----------
class SearchBody(BaseModel):
    customer_name: str
    customer_aliases: list[str] = Field(default_factory=list)
    period: Period = "30d"
    sources: list[Source] | None = None


class BriefBody(BaseModel):
    customer_name: str
    customer_aliases: list[str] = Field(default_factory=list)
    meeting_date: str | None = None
    objective: str | None = None
    period: Period = "30d"


class AskBody(BaseModel):
    brief_id: str
    question: str
    evidence_scope: list[Source] | None = None


class DraftBody(BaseModel):
    brief_id: str
    purpose: str


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "anthropic": bool(CONFIG.anthropic_api_key),
        "notion": bool(CONFIG.notion_token),
        "slack": bool(CONFIG.slack_bot_token),
        "google_drive": Path(CONFIG.google_credentials_file).exists(),
    }


@app.post("/api/search")
def api_search(body: SearchBody) -> dict[str, Any]:
    return search_customer_context(
        customer_name=body.customer_name,
        customer_aliases=body.customer_aliases,
        period=body.period,
        sources=body.sources,
    )


@app.post("/api/brief")
def api_brief(body: BriefBody) -> dict[str, Any]:
    return generate_meeting_brief(
        customer_name=body.customer_name,
        customer_aliases=body.customer_aliases,
        meeting_date=body.meeting_date,
        objective=body.objective,
        period=body.period,
    )


@app.get("/api/brief/{brief_id}")
def api_brief_get(brief_id: str) -> dict[str, Any]:
    brief = STORE.get_brief(brief_id)
    if brief is None:
        raise HTTPException(404, "brief not found")
    return brief.model_dump()


@app.get("/api/brief")
def api_brief_latest() -> dict[str, Any]:
    brief = STORE.latest_brief()
    if brief is None:
        raise HTTPException(404, "no brief yet")
    return brief.model_dump()


@app.post("/api/ask")
def api_ask(body: AskBody) -> dict[str, Any]:
    return ask_meeting_brief(
        brief_id=body.brief_id,
        question=body.question,
        evidence_scope=body.evidence_scope,
    )


@app.get("/api/evidence/{evidence_id:path}")
def api_evidence(evidence_id: str) -> dict[str, Any]:
    out = get_evidence_detail(evidence_id)
    if "error" in out:
        raise HTTPException(404, out["error"])
    return out


@app.post("/api/draft")
def api_draft(body: DraftBody) -> dict[str, Any]:
    out = draft_customer_message(brief_id=body.brief_id, purpose=body.purpose)
    if "error" in out:
        raise HTTPException(404, out["error"])
    return out


# ---------- Iframe static files (must be mounted last so /api and /mcp win) ----------
if APP_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(APP_DIST), html=True), name="iframe-app")
