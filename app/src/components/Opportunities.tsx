import type { Opportunity } from "../lib/types";
import { Card } from "./Card";

export function Opportunities({ opportunities }: { opportunities: Opportunity[] }) {
  return (
    <Card title="Opportunities">
      {opportunities.length === 0 ? (
        <p className="text-sm text-ink-500">No opportunities identified.</p>
      ) : (
        <ul className="space-y-2">
          {opportunities.map((o, i) => (
            <li
              key={i}
              className="rounded-lg border border-emerald-200 bg-emerald-50/60 px-3 py-2 text-sm text-ink-900"
            >
              {o.title}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
