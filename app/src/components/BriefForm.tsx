import { useState } from "react";
import type { Period } from "../lib/types";

interface Props {
  busy: boolean;
  onSubmit: (input: {
    customer_name: string;
    customer_aliases: string[];
    meeting_date: string | null;
    objective: string | null;
    period: Period;
  }) => void;
}

export function BriefForm({ busy, onSubmit }: Props) {
  const [name, setName] = useState("");
  const [aliases, setAliases] = useState("");
  const [date, setDate] = useState("");
  const [objective, setObjective] = useState("");
  const [period, setPeriod] = useState<Period>("30d");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!name.trim()) return;
        onSubmit({
          customer_name: name.trim(),
          customer_aliases: aliases
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          meeting_date: date || null,
          objective: objective || null,
          period,
        });
      }}
      className="mx-8 mb-6 grid grid-cols-1 md:grid-cols-6 gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
    >
      <label className="md:col-span-2 text-sm">
        <span className="block text-xs text-ink-500 mb-1">Customer name</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Acme Corp"
          className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
          required
        />
      </label>
      <label className="md:col-span-2 text-sm">
        <span className="block text-xs text-ink-500 mb-1">Aliases (comma separated)</span>
        <input
          value={aliases}
          onChange={(e) => setAliases(e.target.value)}
          placeholder="Acme, Acme Inc."
          className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
        />
      </label>
      <label className="text-sm">
        <span className="block text-xs text-ink-500 mb-1">Meeting date</span>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
        />
      </label>
      <label className="text-sm">
        <span className="block text-xs text-ink-500 mb-1">Period</span>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value as Period)}
          className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
        >
          <option value="7d">7 days</option>
          <option value="30d">30 days</option>
          <option value="90d">90 days</option>
          <option value="all">All time</option>
        </select>
      </label>
      <label className="md:col-span-5 text-sm">
        <span className="block text-xs text-ink-500 mb-1">Objective</span>
        <input
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          placeholder="Renewal discussion"
          className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
        />
      </label>
      <button
        type="submit"
        disabled={busy || !name.trim()}
        className="md:col-span-1 self-end rounded-md bg-ink-900 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40"
      >
        {busy ? "Generating…" : "Generate Brief"}
      </button>
    </form>
  );
}
