import { useState } from "react";
import type { MeetingBrief, Question } from "../lib/types";
import { Card } from "./Card";
import { api } from "../lib/api";

interface Props {
  brief: MeetingBrief;
  suggested: Question[];
}

export function AskPanel({ brief, suggested }: Props) {
  const [text, setText] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function ask(q: string) {
    const question = q.trim();
    if (!question) return;
    setLoading(true);
    setAnswer(null);
    try {
      const res = await api.ask({ brief_id: brief.id, question });
      setAnswer(res.answer);
    } catch (e) {
      setAnswer(`Error: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }

  const fallback: string[] = [
    "この顧客の最大の懸念点は？",
    "Slack上の根拠だけを見せて",
    "Google Driveの提案資料から論点を抽出して",
    "次回商談で確認すべき質問は？",
  ];
  const items = suggested.length ? suggested.map((s) => s.text) : fallback;

  return (
    <div className="flex flex-col gap-4">
      <Card title="Ask about this customer">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="この顧客について質問する"
          rows={4}
          className="w-full rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-ink-900 placeholder:text-ink-500 focus:outline-none focus:ring-2 focus:ring-slate-300"
        />
        <div className="mt-3 flex justify-end">
          <button
            onClick={() => ask(text)}
            disabled={loading || !text.trim()}
            className="rounded-md bg-ink-900 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40"
          >
            {loading ? "..." : "Ask"}
          </button>
        </div>
        {answer ? (
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-ink-900 whitespace-pre-line">
            {answer}
          </div>
        ) : null}
      </Card>

      <Card title="Suggested Questions">
        <ul className="space-y-2">
          {items.slice(0, 5).map((q, i) => (
            <li key={i}>
              <button
                onClick={() => {
                  setText(q);
                  void ask(q);
                }}
                className="w-full truncate rounded-full border border-slate-200 bg-slate-100 px-3 py-1.5 text-left text-sm text-ink-700 hover:bg-slate-200"
              >
                {q}
              </button>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
