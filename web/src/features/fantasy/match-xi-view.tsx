"use client";

import { ArrowLeft, CloudOff, SearchX } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { StatTile } from "@/components/data/stat-tile";
import { TilesSkeleton } from "@/components/loaders/page-skeletons";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { Skeleton } from "@/components/ui/skeleton";

import { ApiError } from "../players/api";
import { fmt, fmtDate } from "../players/format";
import { Panel, QueryError } from "../players/ui";
import { bestXiHref } from "./best-xi-view";
import { fmtPts, signed } from "./format";
import { useMatchBestXi } from "./queries";
import type { MatchBestXi } from "./types";
import { Segmented } from "./ui";
import { XiList, XiPanel } from "./xi-view";

/** Hindsight Dream Team for one match (H2), next to the naive form XI and the gap between them. */
export function MatchXiView({ id }: { id: number }) {
  const q = useMatchBestXi(id);
  if (q.isPending) {
    return (
      <div role="status" aria-busy="true" aria-label="Loading match best XI">
        <Skeleton className="mb-6 h-16 w-72 max-w-full" />
        <TilesSkeleton count={4} />
        <Skeleton className="mt-4 h-[32rem] rounded-2xl" />
      </div>
    );
  }
  if (q.isError) {
    if (q.error instanceof ApiError && q.error.status === 404) {
      return <EmptyState icon={SearchX} title="Match not found" why={q.error.message} action={{ href: "/fantasy/best-xi", label: "All best XIs this season" }} />;
    }
    return <QueryError error={q.error} onRetry={() => q.refetch()} what="this match’s best XI" />;
  }
  return <MatchXiCard data={q.data} />;
}

export function MatchXiCard({ data: d }: { data: MatchBestXi }) {
  const [capped, setCapped] = useState(false);
  const best = capped && d.best_with_credits ? d.best_with_credits : d.best;
  const season = d.season;
  const gap = best && d.naive ? best.total - d.naive.total : d.gap;
  return (
    <article aria-labelledby="mxi-title">
      <Link
        href={season ? bestXiHref(season) : "/fantasy/best-xi"}
        className="mb-3 inline-flex h-11 items-center gap-1.5 rounded-[10px] pr-2 text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft aria-hidden className="size-4" /> Best XIs {season}
      </Link>
      <PageHeader
        overline={`Hindsight Dream Team · ${d.match_number ? `Match ${d.match_number}` : (d.stage ?? "IPL")}${season ? ` · ${season}` : ""}`}
        title={
          <span id="mxi-title" className="inline-flex flex-wrap items-center gap-2">
            {d.home && <TeamBadge team={d.home} size="md" />}
            {d.home ?? "?"} <span className="text-muted-foreground">v</span> {d.away ?? "?"}
            {d.away && <TeamBadge team={d.away} size="md" opponent={d.home ?? undefined} side="away" />}
          </span>
        }
        subtitle={
          <span className="num">
            {fmtDate(d.date)}
            {d.venue && ` · ${d.venue}`}
            {d.result && ` · ${d.result}`}
          </span>
        }
      />

      {d.no_result || !best ? (
        <EmptyState icon={CloudOff} title="No result, no Dream Team" why="This match was abandoned or washed out, so every player scored 0." action={{ href: season ? bestXiHref(season) : "/fantasy/best-xi", label: "Other matches" }} />
      ) : (
        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:gap-3">
            <StatTile label="Best XI total" value={best.total} format={(n) => fmtPts(n)} hint={best.credits_used !== null ? `${fmt(best.credits_used, 1)} credits` : "no credit cap"} />
            <StatTile label="Form XI total" value={d.naive?.total ?? null} format={(n) => fmtPts(n)} hint="picked on last-5 form" />
            <StatTile label="Gap" value={gap} format={(n) => signed(n)} hint="hindsight − form" />
            <StatTile label="Captain" value={best.picks.find((p) => p.captain)?.player.name ?? null} hint={(() => { const c = best.picks.find((p) => p.captain); return c ? `${c.points} × 2 = ${fmtPts(c.effective)}` : undefined; })()} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
            <Panel
              id="best"
              title="Hindsight best XI"
              className="lg:col-span-7"
              action={
                d.best_with_credits ? (
                  <Segmented<"open" | "capped">
                    label="Credit cap"
                    value={capped ? "capped" : "open"}
                    onChange={(v) => setCapped(v === "capped")}
                    options={[
                      { key: "open", label: "No cap" },
                      { key: "capped", label: "100 credits", title: `Dream11 budget, ${d.credits_season ?? ""} credits` },
                    ]}
                  />
                ) : undefined
              }
            >
              <XiPanel
                xi={best.picks}
                title="Hindsight best XI"
                footer={
                  <p className="mt-2 text-xs text-muted-foreground">
                    The 11 highest possible scorers within Dream11’s shape (1–8 per role, max 10 from one side), C ×2 and VC ×1.5.
                    {capped && d.credits_season && ` Credits from ${d.credits_season}.`}
                    {capped && d.without_credits > 0 && ` ${d.without_credits} player${d.without_credits === 1 ? " has" : "s have"} no credits and ${d.without_credits === 1 ? "is" : "are"} left out.`}
                  </p>
                }
              />
            </Panel>
            <Panel id="naive" title="Form XI · what recent form would have picked" className="lg:col-span-5" bodyClassName="px-0 md:px-0 pb-1">
              {d.naive && d.naive.picks.length > 0 ? (
                <>
                  <p className="px-3 pb-2 text-xs text-muted-foreground md:px-4">Best XI by each player’s mean over their last 5 IPL games before this match (“form”), scored on what they actually got.</p>
                  <XiList xi={d.naive.picks} showProjected caption="Form XI" />
                </>
              ) : (
                <p className="px-3 py-4 text-sm text-muted-foreground md:px-4">No form XI: too few prior games to rank players.</p>
              )}
            </Panel>
          </div>
        </div>
      )}
    </article>
  );
}
