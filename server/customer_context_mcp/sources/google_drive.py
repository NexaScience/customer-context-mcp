"""Google Drive source — searches Drive files for customer-related documents."""

from __future__ import annotations

import logging
import os
from typing import Optional

from ..config import GOOGLE_CREDENTIALS_FILE, GOOGLE_TOKEN_FILE
from ..types import Evidence, Period
from .base import SourceUnavailable, period_to_cutoff, shorten

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _credentials():
    try:
        from google.auth.transport.requests import Request  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    except ImportError as e:
        raise SourceUnavailable(f"google libraries not installed: {e}") from e

    creds: Optional["Credentials"] = None
    token_path = GOOGLE_TOKEN_FILE
    creds_path = GOOGLE_CREDENTIALS_FILE

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise SourceUnavailable(
                    f"Google OAuth credentials not found at {creds_path}. "
                    "Download OAuth client (Desktop) credentials and place them there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds


def _service():
    try:
        from googleapiclient.discovery import build  # type: ignore
    except ImportError as e:
        raise SourceUnavailable(f"google-api-python-client not installed: {e}") from e
    creds = _credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _build_query(customer_name: str, aliases: list[str], period: Period) -> str:
    terms = [customer_name, *(aliases or [])]
    safe_terms = [t.replace("'", "\\'") for t in terms if t]
    name_clauses = " or ".join(
        f"(name contains '{t}' or fullText contains '{t}')" for t in safe_terms
    )
    parts = [f"({name_clauses})"] if name_clauses else []
    cutoff = period_to_cutoff(period)
    if cutoff:
        parts.append(f"modifiedTime > '{cutoff.isoformat()}'")
    parts.append("trashed = false")
    return " and ".join(parts)


def search(
    customer_name: str,
    aliases: list[str] | None = None,
    period: Period = "30d",
    limit: int = 10,
) -> list[Evidence]:
    service = _service()
    q = _build_query(customer_name, aliases or [], period)
    try:
        resp = (
            service.files()
            .list(
                q=q,
                pageSize=limit,
                fields=(
                    "files(id,name,mimeType,modifiedTime,webViewLink,description,owners(displayName))"
                ),
                orderBy="modifiedTime desc",
            )
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        log.warning("google drive search failed: %s", e)
        return []
    files = resp.get("files", [])
    out: list[Evidence] = []
    for f in files:
        fid = f.get("id")
        if not fid:
            continue
        excerpt = f.get("description") or ""
        if not excerpt:
            excerpt = _try_excerpt(service, fid, f.get("mimeType", ""))
        title = f.get("name") or "Untitled"
        out.append(
            Evidence(
                id=f"gdrive:{fid}",
                source="google_drive",
                title=title,
                excerpt=shorten(excerpt or title),
                url=f.get("webViewLink"),
                timestamp=f.get("modifiedTime"),
            )
        )
    return out


def _try_excerpt(service, file_id: str, mime: str) -> str:
    """Best-effort plain-text excerpt for Google Docs / plain text."""
    try:
        if mime == "application/vnd.google-apps.document":
            data = service.files().export(fileId=file_id, mimeType="text/plain").execute()
            text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
            return text
        if mime.startswith("text/"):
            data = service.files().get_media(fileId=file_id).execute()
            text = data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else str(data)
            return text
    except Exception as e:  # noqa: BLE001
        log.debug("excerpt fetch failed for %s: %s", file_id, e)
    return ""
