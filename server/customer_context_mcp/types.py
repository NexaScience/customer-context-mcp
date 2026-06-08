"""Shared data models for customer-context-mcp."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Source = Literal["notion", "slack", "google_drive"]
Period = Literal["7d", "30d", "90d", "all"]
Severity = Literal["high", "medium", "low"]


class Evidence(BaseModel):
    id: str
    source: Source
    title: str
    excerpt: str
    url: Optional[str] = None
    timestamp: Optional[str] = None


class Risk(BaseModel):
    title: str
    severity: Severity = "medium"
    evidence_ids: list[str] = Field(default_factory=list)


class Opportunity(BaseModel):
    title: str
    evidence_ids: list[str] = Field(default_factory=list)


class Question(BaseModel):
    text: str
    rationale: Optional[str] = None


class Action(BaseModel):
    title: str
    owner: Optional[str] = None


class TimelineEvent(BaseModel):
    date: str
    source: Source
    title: str
    summary: Optional[str] = None
    evidence_id: Optional[str] = None


class KeyTopic(BaseModel):
    title: str
    sources: list[Source] = Field(default_factory=list)


class MeetingBrief(BaseModel):
    id: str
    customer_name: str
    customer_aliases: list[str] = Field(default_factory=list)
    meeting_date: Optional[str] = None
    objective: Optional[str] = None
    period: Period = "30d"
    summary: str = ""
    meeting_objective: str = ""
    key_topics: list[KeyTopic] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)
    suggested_questions: list[Question] = Field(default_factory=list)
    recommended_actions: list[Action] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    sources_count: int = 0
    risk_level: Severity = "medium"
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SearchResult(BaseModel):
    evidence: list[Evidence] = Field(default_factory=list)
