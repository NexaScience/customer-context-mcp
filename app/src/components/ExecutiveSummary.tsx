import { Card } from "./Card";

export function ExecutiveSummary({ text }: { text: string }) {
  return (
    <Card title="Executive Summary">
      <p className="text-sm leading-relaxed text-ink-700 whitespace-pre-line">
        {text || "No summary available."}
      </p>
    </Card>
  );
}
