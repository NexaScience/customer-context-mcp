import type { MeetingBrief } from "../lib/types";
import { riskPill, updatedAgo } from "../lib/format";

export function CustomerCard({ brief }: { brief: MeetingBrief }) {
  const riskLabel =
    brief.risk_level === "high" ? "High" : brief.risk_level === "low" ? "Low" : "Medium";

  const meetingLine = [
    brief.objective ? `Meeting: ${brief.objective}` : "Meeting: Renewal discussion",
    brief.meeting_date ? `/ ${brief.meeting_date}` : "",
  ]
    .join(" ")
    .trim();

  const periodDays =
    brief.period === "7d"
      ? "7 days"
      : brief.period === "30d"
      ? "30 days"
      : brief.period === "90d"
      ? "90 days"
      : "All time";

  return (
    <section className="mx-8 mb-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        <div className="flex-1 min-w-[220px]">
          <div className="text-xl font-semibold text-ink-900">{brief.customer_name}</div>
          <div className="text-sm text-ink-500 mt-0.5">{meetingLine}</div>
        </div>

        <span
          className={`inline-flex items-center rounded-full px-3 py-1 text-xs ${riskPill[brief.risk_level]}`}
        >
          Risk: {riskLabel}
        </span>
        <span className="inline-flex items-center rounded-full bg-sky-50 border border-sky-200 px-3 py-1 text-xs text-sky-700">
          Sources: {brief.sources_count} items
        </span>
        <span className="inline-flex items-center rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-xs text-emerald-700">
          Period: {periodDays}
        </span>
        <span className="inline-flex items-center rounded-full border border-slate-200 px-3 py-1 text-xs text-ink-500">
          {updatedAgo(brief.updated_at)}
        </span>
      </div>
    </section>
  );
}
