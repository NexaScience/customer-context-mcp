import type { Evidence } from "../lib/types";
import { Card } from "./Card";
import { sourceColor, sourceLabel } from "../lib/format";

interface Props {
  evidence: Evidence[];
  highlightId?: string | null;
}

export function EvidenceDrawer({ evidence, highlightId }: Props) {
  if (evidence.length === 0) {
    return (
      <Card title="Evidence Drawer">
        <p className="text-sm text-ink-500">No evidence yet.</p>
      </Card>
    );
  }

  const ordered = highlightId
    ? [
        ...evidence.filter((e) => e.id === highlightId),
        ...evidence.filter((e) => e.id !== highlightId),
      ]
    : evidence;

  return (
    <Card title="Evidence Drawer">
      <ul className="space-y-3">
        {ordered.slice(0, 6).map((e) => (
          <li
            key={e.id}
            className={
              "rounded-lg p-3 " +
              (highlightId === e.id ? "bg-blue-50" : "bg-slate-50/50")
            }
          >
            <div className="flex items-baseline gap-2 text-sm">
              <span className={`font-semibold ${sourceColor[e.source]}`}>
                {sourceLabel[e.source]}
              </span>
              {e.url ? (
                <a
                  href={e.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-ink-900 hover:underline truncate"
                >
                  {e.title}
                </a>
              ) : (
                <span className="font-medium text-ink-900 truncate">{e.title}</span>
              )}
            </div>
            <p className="mt-1 text-xs text-ink-500 line-clamp-2">{e.excerpt}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
