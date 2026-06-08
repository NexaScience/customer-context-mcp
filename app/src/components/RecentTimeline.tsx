import type { TimelineEvent } from "../lib/types";
import { Card } from "./Card";
import { shortDate, sourceLabel } from "../lib/format";

export function RecentTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <Card title="Recent Timeline">
      {events.length === 0 ? (
        <p className="text-sm text-ink-500">No recent activity.</p>
      ) : (
        <ul className="space-y-1.5 text-sm text-ink-900">
          {events.slice(0, 8).map((e, i) => (
            <li key={i} className="flex gap-3">
              <span className="w-12 shrink-0 text-ink-500">{shortDate(e.date)}</span>
              <span className="w-16 shrink-0 text-ink-500">{sourceLabel[e.source]}:</span>
              <span className="flex-1">{e.title}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
