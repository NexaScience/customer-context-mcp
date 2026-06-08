import type { KeyTopic } from "../lib/types";
import { sourceLabel } from "../lib/format";
import { Card } from "./Card";

export function KeyTopics({ topics }: { topics: KeyTopic[] }) {
  return (
    <Card title="Key Topics">
      {topics.length === 0 ? (
        <p className="text-sm text-ink-500">No topics identified.</p>
      ) : (
        <ul className="space-y-2">
          {topics.map((t, i) => (
            <li key={i} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex items-center gap-2 text-ink-900">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                {t.title}
              </span>
              <span className="text-xs text-ink-500">
                {t.sources.map((s) => sourceLabel[s]).join(" / ")}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
