import type { SourceKind, Severity } from "./types";

export const sourceLabel: Record<SourceKind, string> = {
  notion: "Notion",
  slack: "Slack",
  google_drive: "Drive",
};

export const sourceColor: Record<SourceKind, string> = {
  notion: "text-violet-600",
  slack: "text-rose-600",
  google_drive: "text-blue-600",
};

export function relativeOrDate(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-CA"); // YYYY-MM-DD
}

export function shortDate(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${mm}/${dd}`;
}

export function updatedAgo(iso?: string | null): string {
  if (!iso) return "Updated now";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Updated now";
  const diffMs = Date.now() - d.getTime();
  const min = Math.round(diffMs / 60000);
  if (min < 1) return "Updated now";
  if (min < 60) return `Updated ${min}m ago`;
  const h = Math.round(min / 60);
  if (h < 24) return `Updated ${h}h ago`;
  const days = Math.round(h / 24);
  return `Updated ${days}d ago`;
}

export const severityBadge: Record<Severity, { label: string; cls: string }> = {
  high: {
    label: "High",
    cls: "bg-rose-50 text-rose-700 border border-rose-200",
  },
  medium: {
    label: "Med",
    cls: "bg-amber-50 text-amber-700 border border-amber-200",
  },
  low: {
    label: "Low",
    cls: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  },
};

export const riskPill: Record<Severity, string> = {
  high: "bg-rose-50 text-rose-700 border border-rose-200",
  medium: "bg-amber-50 text-amber-700 border border-amber-200",
  low: "bg-emerald-50 text-emerald-700 border border-emerald-200",
};
