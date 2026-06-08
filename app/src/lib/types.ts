export type SourceKind = "notion" | "slack" | "google_drive";
export type Severity = "high" | "medium" | "low";
export type Period = "7d" | "30d" | "90d" | "all";

export interface Evidence {
  id: string;
  source: SourceKind;
  title: string;
  excerpt: string;
  url?: string | null;
  timestamp?: string | null;
}

export interface KeyTopic {
  title: string;
  sources: SourceKind[];
}

export interface Risk {
  title: string;
  severity: Severity;
  evidence_ids: string[];
}

export interface Opportunity {
  title: string;
  evidence_ids: string[];
}

export interface Question {
  text: string;
  rationale?: string | null;
}

export interface Action {
  title: string;
  owner?: string | null;
}

export interface TimelineEvent {
  date: string;
  source: SourceKind;
  title: string;
  summary?: string | null;
  evidence_id?: string | null;
}

export interface MeetingBrief {
  id: string;
  customer_name: string;
  customer_aliases: string[];
  meeting_date?: string | null;
  objective?: string | null;
  period: Period;
  summary: string;
  meeting_objective: string;
  key_topics: KeyTopic[];
  risks: Risk[];
  opportunities: Opportunity[];
  suggested_questions: Question[];
  recommended_actions: Action[];
  timeline: TimelineEvent[];
  evidence: Evidence[];
  sources_count: number;
  risk_level: Severity;
  updated_at: string;
  errors?: Record<string, string>;
}

export interface AskResponse {
  brief_id: string;
  question: string;
  answer: string;
  evidence_ids: string[];
}

export interface Health {
  ok: boolean;
  anthropic: boolean;
  notion: boolean;
  slack: boolean;
  google_drive: boolean;
}
