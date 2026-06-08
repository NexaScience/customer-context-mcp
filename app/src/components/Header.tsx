interface HeaderProps {
  sources: { notion: boolean; slack: boolean; google_drive: boolean };
}

const PILLS = [
  { key: "notion", label: "Notion" },
  { key: "slack", label: "Slack" },
  { key: "google_drive", label: "Google Drive" },
] as const;

export function Header({ sources }: HeaderProps) {
  return (
    <header className="flex items-start justify-between px-8 py-6 bg-slate-50">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-ink-900">
          Customer Meeting Brief
        </h1>
        <p className="text-sm text-ink-500 mt-1">
          iframe MCP App / Meeting Preparation Assistant
        </p>
      </div>
      <div className="flex gap-2">
        {PILLS.map((p) => {
          const enabled = sources[p.key];
          return (
            <span
              key={p.key}
              className={
                "inline-flex items-center rounded-full border px-3 py-1 text-xs " +
                (enabled
                  ? "border-slate-300 text-ink-700 bg-white"
                  : "border-slate-200 text-slate-400 bg-white")
              }
              title={enabled ? "Configured" : "Not configured"}
            >
              {p.label}
            </span>
          );
        })}
      </div>
    </header>
  );
}
