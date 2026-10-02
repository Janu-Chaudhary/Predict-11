import { ClipboardCheck, Layers, ListOrdered, Shirt, Sparkles, Swords, Table2, Users } from "lucide-react";
import type { Metadata } from "next";

import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { SampleDataNote } from "@/components/shell/sample-data-note";
import { TabLinks, pickTab } from "@/components/shell/tab-links";

import { MatchPredictedXi } from "@/features/predictions/match-predicted-xi";

import { fetchMatchHeader, MatchVenueBanner } from "./match-venue";
import { SampleMatchCharts } from "./sample-charts";

const TABS = ["summary", "scorecard", "balls", "lineups", "fantasy", "predicted", "stats", "h2h", "review"] as const;
type Tab = (typeof TABS)[number];
const LABEL: Record<Tab, string> = {
  summary: "Summary",
  scorecard: "Scorecard",
  balls: "Balls",
  lineups: "Lineups",
  fantasy: "Fantasy",
  predicted: "Predicted XI",
  stats: "Stats",
  h2h: "H2H",
  review: "Review",
};

const EMPTY: Record<Exclude<Tab, "stats" | "predicted">, { icon: typeof Layers; title: string; why: string; when: string }> = {
  summary: { icon: Sparkles, title: "Summary not available yet", why: "Over momentum, win probability, top performers and conditions need this match’s data.", when: "Pre-match preview at T-24 h; full summary about an hour after the result." },
  scorecard: { icon: Table2, title: "No scorecard yet", why: "There is no live data in Predict-11; scorecards are harvested after the match.", when: "About 1 h after the result (retries hourly until all sources agree)." },
  balls: { icon: Layers, title: "Ball-by-ball not available", why: "Ball-by-ball comes from the post-match commentary harvest.", when: "About 45 min after the result; the last and next attempt times will show here." },
  lineups: { icon: Users, title: "Lineups not confirmed", why: "Before the toss this tab shows the probable XI with P(plays).", when: "Confirmed XIs and impact subs appear at the toss (≈ T-30 min)." },
  fantasy: { icon: Shirt, title: "Projections not ready", why: "Best XI, captain picks and per-player ranges need the projection model for this fixture.", when: "Provisional at T-24 h, re-projected at the toss." },
  h2h: { icon: Swords, title: "Head-to-head not loaded", why: "The team-vs-team history for this fixture hasn’t been fetched.", when: "With the H2H endpoint." },
  review: { icon: ClipboardCheck, title: "Nothing to review yet", why: "Review compares every projection with the actual fantasy points.", when: "About 1 h after the result, once the scorecard is harvested." },
};

export async function generateMetadata(props: PageProps<"/matches/[id]">): Promise<Metadata> {
  const { id } = await props.params;
  return { title: `Match ${decodeURIComponent(id)}` };
}

export default async function MatchPage(props: PageProps<"/matches/[id]">) {
  const { id } = await props.params;
  const sp = await props.searchParams;
  const tab = pickTab(sp.tab, TABS, "summary");
  const base = `/matches/${encodeURIComponent(id)}`;
  const empty = tab === "stats" || tab === "predicted" ? null : EMPTY[tab];
  const numericId = /^\d{1,10}$/.test(decodeURIComponent(id)) ? Number(decodeURIComponent(id)) : null;
  const header = await fetchMatchHeader(decodeURIComponent(id));

  return (
    <>
      {/* Score header — placeholder until the match endpoint lands. */}
      <section aria-labelledby="match-title" className="mb-4 rounded-xl border border-border bg-card p-4 shadow-e1">
        {header && <MatchVenueBanner match={header} />}
        <p className="text-overline text-muted-foreground">
          Match <span className="num">{decodeURIComponent(id)}</span> · IPL
        </p>
        <h1 id="match-title" className="sr-only">
          Match {decodeURIComponent(id)}
        </h1>
        <div className="mt-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-full bg-surface-2 text-faint">?</span>
            <span className="text-score-xl text-faint">–</span>
          </div>
          <span className="text-xs text-muted-foreground">vs</span>
          <div className="flex items-center gap-3">
            <span className="text-score-xl text-faint">–</span>
            <span className="flex size-10 items-center justify-center rounded-full bg-surface-2 text-faint">?</span>
          </div>
        </div>
        <p className="mt-3 text-center text-xs text-muted-foreground">Teams, score and match state appear once the match endpoint is connected.</p>
      </section>

      <TabLinks label="Match sections" tabs={TABS.map((t) => ({ key: t, label: LABEL[t] }))} active={tab} hrefFor={(t) => `${base}?tab=${t}`} />

      {tab === "predicted" ? (
        numericId !== null ? (
          <MatchPredictedXi matchId={numericId} />
        ) : (
          <EmptyState icon={Shirt} title="No honest prediction for this match" why="This match id isn’t a played IPL match." when="Predicted XIs exist for every played 2026 match." action={{ href: "/accuracy", label: "All predicted XIs" }} />
        )
      ) : empty ? (
        <EmptyState icon={empty.icon} title={empty.title} why={empty.why} when={empty.when} action={{ href: "/matches", label: "Back to all matches" }} />
      ) : (
        <div className="grid gap-4">
          <SampleDataNote>These charts preview the Stats tab layout with invented numbers.</SampleDataNote>
          <div className="flex items-center gap-2 text-sm">
            <TeamBadge team="CSK" size="md" />
            <span className="font-medium">CSK</span>
            <span className="text-muted-foreground">v</span>
            <span className="font-medium">MI</span>
            <TeamBadge team="MI" size="md" opponent="CSK" side="away" />
          </div>
          <SampleMatchCharts />
          <EmptyState compact icon={ListOrdered} title="Partnerships and wagon wheel" why="These need ball-by-ball data for this match." when="After the post-match harvest." />
        </div>
      )}
    </>
  );
}
