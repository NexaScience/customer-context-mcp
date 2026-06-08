import type { Risk } from "../lib/types";
import { severityBadge } from "../lib/format";
import { Card } from "./Card";

interface Props {
  risks: Risk[];
  onPickEvidence: (id: string) => void;
}

export function Risks({ risks, onPickEvidence }: Props) {
  return (
    <Card title="Risks">
      {risks.length === 0 ? (
        <p className="text-sm text-ink-500">No risks flagged.</p>
      ) : (
        <ul className="space-y-3">
          {risks.map((r, i) => {
            const badge = severityBadge[r.severity];
            const evid = r.evidence_ids[0];
            return (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span
                  className={`mt-0.5 inline-flex w-12 justify-center rounded-md px-2 py-0.5 text-xs font-medium ${badge.cls}`}
                >
                  {badge.label}
                </span>
                <div className="flex-1">
                  <div className="text-ink-900">{r.title}</div>
                  {evid ? (
                    <button
                      onClick={() => onPickEvidence(evid)}
                      className="mt-0.5 text-xs text-blue-600 hover:underline"
                    >
                      View evidence →
                    </button>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
