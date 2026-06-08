import { useEffect, useState } from "react";
import { Header } from "./components/Header";
import { CustomerCard } from "./components/CustomerCard";
import { ExecutiveSummary } from "./components/ExecutiveSummary";
import { KeyTopics } from "./components/KeyTopics";
import { Risks } from "./components/Risks";
import { Opportunities } from "./components/Opportunities";
import { RecommendedActions } from "./components/RecommendedActions";
import { RecentTimeline } from "./components/RecentTimeline";
import { AskPanel } from "./components/AskPanel";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { BriefForm } from "./components/BriefForm";
import { api } from "./lib/api";
import type { Health, MeetingBrief, Period } from "./lib/types";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [brief, setBrief] = useState<MeetingBrief | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightId, setHighlightId] = useState<string | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    api
      .latestBrief()
      .then(setBrief)
      .catch(() => {
        /* no brief yet — show form */
      });
  }, []);

  async function generate(input: {
    customer_name: string;
    customer_aliases: string[];
    meeting_date: string | null;
    objective: string | null;
    period: Period;
  }) {
    setLoading(true);
    setError(null);
    try {
      const next = await api.generateBrief(input);
      setBrief(next);
      setHighlightId(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const sources = {
    notion: !!health?.notion,
    slack: !!health?.slack,
    google_drive: !!health?.google_drive,
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <Header sources={sources} />

      <BriefForm busy={loading} onSubmit={generate} />

      {error ? (
        <div className="mx-8 mb-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {!brief ? (
        <div className="mx-8 mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-ink-500">
          Generate a brief above to see Acme Corp-style dashboard with insights from
          Notion, Slack, and Google Drive.
        </div>
      ) : (
        <>
          <CustomerCard brief={brief} />

          <main className="mx-8 grid grid-cols-1 lg:grid-cols-3 gap-4 pb-10">
            <div className="lg:col-span-2 flex flex-col gap-4">
              <ExecutiveSummary text={brief.summary} />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <KeyTopics topics={brief.key_topics} />
                <Risks risks={brief.risks} onPickEvidence={setHighlightId} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Opportunities opportunities={brief.opportunities} />
                <RecommendedActions actions={brief.recommended_actions} />
              </div>

              <RecentTimeline events={brief.timeline} />
            </div>

            <aside className="flex flex-col gap-4">
              <AskPanel brief={brief} suggested={brief.suggested_questions} />
              <EvidenceDrawer evidence={brief.evidence} highlightId={highlightId} />
            </aside>
          </main>
        </>
      )}
    </div>
  );
}
