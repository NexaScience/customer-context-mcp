import type { Action } from "../lib/types";
import { Card } from "./Card";

export function RecommendedActions({ actions }: { actions: Action[] }) {
  return (
    <Card title="Recommended Actions">
      {actions.length === 0 ? (
        <p className="text-sm text-ink-500">No actions recommended.</p>
      ) : (
        <ol className="space-y-2 text-sm text-ink-900 list-decimal pl-5 marker:text-ink-500">
          {actions.map((a, i) => (
            <li key={i}>
              {a.title}
              {a.owner ? <span className="ml-2 text-xs text-ink-500">({a.owner})</span> : null}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
