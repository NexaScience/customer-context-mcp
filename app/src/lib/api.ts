import type { AskResponse, Health, MeetingBrief, Period, SourceKind } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${text}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),

  latestBrief: () => request<MeetingBrief>("/api/brief"),

  getBrief: (id: string) => request<MeetingBrief>(`/api/brief/${encodeURIComponent(id)}`),

  generateBrief: (body: {
    customer_name: string;
    customer_aliases?: string[];
    meeting_date?: string | null;
    objective?: string | null;
    period?: Period;
  }) =>
    request<MeetingBrief>("/api/brief", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  ask: (body: { brief_id: string; question: string; evidence_scope?: SourceKind[] }) =>
    request<AskResponse>("/api/ask", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  draft: (body: { brief_id: string; purpose: string }) =>
    request<{ draft: string }>("/api/draft", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
