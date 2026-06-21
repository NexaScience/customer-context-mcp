"""LLM helpers — Gemini-backed brief generation and Q&A."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from .config import GEMINI_MODEL, CONFIG
from .types import Evidence

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    pass


def _client():
    if not CONFIG.gemini_api_key:
        raise LLMUnavailable("GEMINI_API_KEY is not set")
    try:
        from google import genai  # type: ignore
    except ImportError as e:
        raise LLMUnavailable(f"google-genai package not installed: {e}") from e
    return genai.Client(api_key=CONFIG.gemini_api_key)


def _generate(
    system: str, contents: str, *, max_tokens: int | None = None, json_mode: bool = False, attempts: int = 3
) -> str:
    """Single-turn Gemini generation with a system instruction.

    ``max_tokens`` caps the *output*; when ``None`` (the default) the model's
    own maximum is used (gemini-3.1-flash-lite: 64K output). Input is bounded
    only by the model's context window (~1M tokens), not by this function.

    Retries transient 5xx errors (e.g. 503 "model is overloaded") with
    exponential backoff, and converts any Gemini API error into
    ``LLMUnavailable`` so callers degrade gracefully instead of crashing the
    MCP session.
    """
    client = _client()
    from google.genai import types  # type: ignore
    from google.genai import errors as genai_errors  # type: ignore

    cfg_kwargs: dict[str, Any] = {"system_instruction": system}
    if max_tokens is not None:
        cfg_kwargs["max_output_tokens"] = max_tokens
    if json_mode:
        cfg_kwargs["response_mime_type"] = "application/json"

    for attempt in range(attempts):
        try:
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(**cfg_kwargs),
            )
            return resp.text or ""
        except genai_errors.ServerError as e:  # 5xx — usually transient overload
            if attempt < attempts - 1:
                log.warning("Gemini 5xx (attempt %d/%d): %s", attempt + 1, attempts, e)
                time.sleep(1.5 * (attempt + 1))
                continue
            raise LLMUnavailable(f"Gemini temporarily unavailable: {e}") from e
        except genai_errors.ClientError as e:  # 4xx — bad key/request, not retryable
            raise LLMUnavailable(f"Gemini request failed: {e}") from e
    raise LLMUnavailable("Gemini unavailable")  # unreachable, satisfies type checker


def _evidence_block(evidence: list[Evidence]) -> str:
    lines: list[str] = []
    for e in evidence:
        lines.append(
            f"- [{e.id}] ({e.source}) {e.title}"
            + (f" — {e.timestamp}" if e.timestamp else "")
            + f"\n  {e.excerpt}"
        )
    return "\n".join(lines) or "(no evidence)"


BRIEF_SYSTEM = (
    "You are a sales / CS analyst. Given evidence retrieved from Notion, Slack and Google "
    "Drive about a single customer, you must produce a structured meeting-prep brief in "
    "JSON. Every risk, opportunity, action and timeline entry must cite evidence_ids that "
    "exist in the provided evidence list. If a section has no support in the evidence, "
    "return an empty list rather than fabricating. Respond with JSON only — no prose. "
    "Write every human-readable string value (summary, meeting_objective, titles, "
    "rationales, owners, timeline summaries) in Japanese (日本語). Keep the JSON keys and "
    "the enum values in English: risk_level / severity must be one of high|medium|low, "
    "and source must be one of notion|slack|google_drive. "
    "Synthesize concisely — do NOT transcribe the evidence. The input may be large, but "
    "the brief must read as a tight summary: the summary field is a 3-5 sentence "
    "executive overview; every title, action, question and timeline entry is a short "
    "scannable phrase (one line, not a paragraph); rationales stay to one sentence. "
    "Surface only the most important items per section (roughly 5-7 max), merging "
    "duplicates and dropping minor noise."
)

BRIEF_SCHEMA_HINT = {
    "summary": "string (3-4 sentences, executive summary)",
    "meeting_objective": "string",
    "risk_level": "high | medium | low",
    "key_topics": [
        {"title": "string", "sources": ["notion|slack|google_drive", "..."]}
    ],
    "risks": [
        {"title": "string", "severity": "high|medium|low", "evidence_ids": ["..."]}
    ],
    "opportunities": [{"title": "string", "evidence_ids": ["..."]}],
    "suggested_questions": [{"text": "string", "rationale": "string"}],
    "recommended_actions": [{"title": "string", "owner": "string|null"}],
    "timeline": [
        {
            "date": "YYYY-MM-DD",
            "source": "notion|slack|google_drive",
            "title": "string",
            "summary": "string",
            "evidence_id": "string",
        }
    ],
}


def generate_brief_json(
    customer_name: str,
    aliases: list[str],
    meeting_date: str | None,
    objective: str | None,
    evidence: list[Evidence],
) -> dict[str, Any]:
    user = (
        f"Customer: {customer_name}\n"
        f"Aliases: {', '.join(aliases) if aliases else '(none)'}\n"
        f"Meeting date: {meeting_date or '(unspecified)'}\n"
        f"Meeting objective: {objective or '(unspecified)'}\n\n"
        f"Evidence (use these evidence_ids when citing):\n{_evidence_block(evidence)}\n\n"
        f"Return JSON with this shape:\n{json.dumps(BRIEF_SCHEMA_HINT, indent=2)}"
    )
    text = _generate(BRIEF_SYSTEM, user, json_mode=True)
    return _parse_json(text)


QA_SYSTEM = (
    "You are answering follow-up questions about a customer meeting brief. Use only the "
    "supplied evidence to answer. If the answer cannot be supported by the evidence, say "
    "so. Be concise and cite evidence_ids inline as [id]. Always answer in Japanese (日本語)."
)


def answer_question(question: str, brief_json: dict[str, Any], evidence: list[Evidence]) -> str:
    user = (
        f"Brief summary: {brief_json.get('summary', '')}\n"
        f"Objective: {brief_json.get('meeting_objective', '')}\n\n"
        f"Evidence:\n{_evidence_block(evidence)}\n\n"
        f"Question: {question}"
    )
    return _generate(QA_SYSTEM, user).strip()


DRAFT_SYSTEM = (
    "You are drafting professional, concise customer-facing or internal messages from a "
    "meeting brief. Use only facts supported by the evidence. Match the requested purpose. "
    "Return the message body only — no preamble. Write the message in Japanese (日本語)."
)

PURPOSE_INSTRUCTIONS = {
    "follow_up_email": (
        "Draft a follow-up email (subject line + body) to send to the customer after the "
        "meeting summarising agreed next steps and open items."
    ),
    "internal_slack_summary": (
        "Draft a short internal Slack message (Japanese OK if context suggests it) "
        "summarising customer status, top risks, and next actions for the account team."
    ),
    "meeting_agenda": (
        "Draft a numbered meeting agenda covering the objective, key topics, open "
        "questions, and decision items."
    ),
}


def draft_message(
    purpose: str, brief_json: dict[str, Any], evidence: list[Evidence]
) -> str:
    purpose_clean = purpose if purpose in PURPOSE_INSTRUCTIONS else "follow_up_email"
    instruction = PURPOSE_INSTRUCTIONS[purpose_clean]
    user = (
        f"Purpose: {purpose_clean}\n"
        f"Instruction: {instruction}\n\n"
        f"Summary: {brief_json.get('summary', '')}\n"
        f"Objective: {brief_json.get('meeting_objective', '')}\n"
        f"Risks: {json.dumps(brief_json.get('risks', []), ensure_ascii=False)}\n"
        f"Actions: {json.dumps(brief_json.get('recommended_actions', []), ensure_ascii=False)}\n"
        f"Opportunities: {json.dumps(brief_json.get('opportunities', []), ensure_ascii=False)}\n\n"
        f"Evidence:\n{_evidence_block(evidence)}"
    )
    return _generate(DRAFT_SYSTEM, user).strip()


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
