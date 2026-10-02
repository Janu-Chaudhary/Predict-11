"use client";

import { ArrowLeft, CloudMoon, Droplets, Wind } from "lucide-react";
import Link from "next/link";

import { StatBarChart } from "@/components/charts/stat-charts";
import { StatTile } from "@/components/data/stat-tile";
import { ChartSkeleton, TilesSkeleton } from "@/components/loaders/page-skeletons";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { ErrorState } from "./error-state";
import { fmtDate, fmtPct, fmtRuns, isNum } from "./format";
import { useVenue } from "./queries";
import type { VenueCard as VenueCardData } from "./types";
import { HERO_OVERLAP, VenueHero } from "./venue-photo";
import { DewSection, PaceSpinSection, TossTrendSection } from "./venue-conditions";
import { LeaderList, Panel, SeasonParBars, ParComparison, PhaseBars, TossOutcome, TossSplitBar, TotalsList } from "./venue-sections";

/** First season of the impact-player era; the API reports the same window as `recent`. */
export const RECENT_FROM = 2023;

/** Drop the notes the UI already covers with a labelled slot. */
const COVERED_NOTE = /pace vs spin/i;

/**
 * Venue card (E1): par first-innings score (2023+ next to all-time), chase and toss bias,
 * phase run rates, record totals and venue leaders. Pure view: data in, markup out.
 */
export function VenueCardView({ venue, recentFrom = RECENT_FROM, conditions = false }: { venue: VenueCardData; recentFrom?: number; /** Fetch toss trend, pace/spin and dew (needs a QueryClient). */ conditions?: boolean }) {
  const v = venue;
  const seasons = v.first_match && v.last_match ? `${v.first_match.slice(0, 4)}–${v.last_match.slice(0, 4)}` : null;
  const hasSeasonToss = v.by_season.some((s) => isNum(s.field_pct ?? null));
  const recentSeasons = v.by_season.filter((s) => s.season >= recentFrom);
  const smallRecent = v.recent.matches < 10;
  const notes = v.notes.filter((n) => !COVERED_NOTE.test(n));
  const overline = v.city ? `Venue · ${v.city}` : "Venue";
  const subtitle = (
    <span className="num">
      {v.matches} IPL matches{seasons && ` · ${seasons}`}
      {v.last_match && ` · last ${fmtDate(v.last_match)}`}
    </span>
  );

  return (
    <article aria-labelledby="venue-title">
      {v.image_url ? (
        <VenueHero
          image={v.image_url}
          credit={v.image_credit}
          overline={overline}
          title={<span id="venue-title">{v.name}</span>}
          subtitle={subtitle}
          topLeft={
            <Link
              href="/venues"
              className="inline-flex h-9 items-center gap-1.5 rounded-full bg-black/45 px-3 text-sm text-white/90 outline-none backdrop-blur-sm hover:bg-black/65 hover:text-white focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ArrowLeft aria-hidden className="size-4" /> All venues
            </Link>
          }
        />
      ) : (
        <>
          <Link
            href="/venues"
            className="mb-3 inline-flex h-11 items-center gap-1.5 rounded-[10px] pr-2 text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ArrowLeft aria-hidden className="size-4" /> All venues
          </Link>
          <PageHeader overline={overline} title={<span id="venue-title">{v.name}</span>} subtitle={subtitle} />
        </>
      )}

      <div className={cn("grid grid-cols-[minmax(0,1fr)] gap-4 lg:gap-5", v.image_url && HERO_OVERLAP)}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-4 xl:grid-cols-6">
          <StatTile
            label={`Par 1st inns ${recentFrom}+`}
            value={isNum(v.recent.avg_first_innings) ? Math.round(v.recent.avg_first_innings) : null}
            hint={
              <>
                all-time {fmtRuns(v.all_time.avg_first_innings)} · n={v.recent.matches}
              </>
            }
          />
          <StatTile
            label={`Median 1st inns ${recentFrom}+`}
            value={isNum(v.recent.median_first_innings) ? Math.round(v.recent.median_first_innings) : null}
            hint={<>all-time {fmtRuns(v.all_time.median_first_innings)}</>}
          />
          <StatTile label={`Avg 2nd inns ${recentFrom}+`} value={isNum(v.recent.avg_second_innings) ? Math.round(v.recent.avg_second_innings) : null} hint={<>all-time {fmtRuns(v.all_time.avg_second_innings)}</>} />
          <StatTile label={`Chase win ${recentFrom}+`} value={isNum(v.recent.chase_win_pct) ? fmtPct(v.recent.chase_win_pct) : null} hint={<>all-time {fmtPct(v.all_time.chase_win_pct)}</>} />
          <StatTile
            label={`Toss winner won ${recentFrom}+`}
            value={isNum(v.toss_recent.toss_winner_win_pct) ? fmtPct(v.toss_recent.toss_winner_win_pct) : null}
            hint={<>chose field {fmtPct(v.toss_recent.field_pct)}</>}
          />
          <StatTile label={`Matches ${recentFrom}+`} value={v.recent.matches} hint={<>{v.matches} all-time</>} />
        </div>
        {smallRecent && (
          <p className="rounded-lg border border-warning/30 bg-warning/8 px-3 py-2 text-xs text-foreground">
            <span className="font-semibold">Small sample.</span> Only {v.recent.matches} completed {v.recent.matches === 1 ? "match" : "matches"} here since {recentFrom}; treat the {recentFrom}+ figures as a rough guide.
          </p>
        )}

        {/* Main column (scores, trends, records) beside a conditions rail on wide screens. */}
        <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(380px,30rem)]">
          <div className="grid min-w-0 content-start gap-4 lg:gap-5">
            <Panel id="par" title="Par score" aside={`${recentFrom}+ vs all-time`}>
              <ParComparison recent={v.recent} allTime={v.all_time} recentFrom={recentFrom} weighted={v.par_weighted} />
            </Panel>

            <div className="grid min-w-0 gap-4 lg:gap-5 2xl:grid-cols-2">
              <SeasonParBars seasons={v.by_season} venueName={v.name} recentFrom={recentFrom} />
              {conditions ? (
                <TossTrendSection venueId={v.id} recentFrom={recentFrom} />
              ) : hasSeasonToss ? (
                <StatBarChart
                  title="Toss decision by season · chose to field %"
                  summary={`Share of toss winners who chose to field each season. ${recentSeasons.map((s) => `${s.season}: ${fmtPct(s.field_pct ?? null)}`).join(", ")}.`}
                  data={v.by_season.map((s) => ({ season: String(s.season), field: isNum(s.field_pct ?? null) ? Math.round(s.field_pct as number) : null }))}
                  xKey="season"
                  series={[{ key: "field", label: "Chose to field %", color: "var(--chart-3)" }]}
                />
              ) : null}
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:gap-5">
              <Panel id="highest" title="Highest totals" aside="All IPL seasons">
                <TotalsList totals={v.highest_totals} kind="highest" />
              </Panel>
              <Panel id="lowest" title="Lowest totals" aside="Completed innings">
                <TotalsList totals={v.lowest_totals} kind="lowest" />
              </Panel>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:gap-5">
              <Panel id="scorers" title="Top run-scorers here" aside="All IPL seasons">
                <LeaderList leaders={v.top_run_scorers} kind="runs" />
              </Panel>
              <Panel id="wickets" title="Top wicket-takers here" aside="All IPL seasons">
                <LeaderList leaders={v.top_wicket_takers} kind="wickets" />
              </Panel>
            </div>
          </div>

          <aside aria-label="Conditions" className="grid min-w-0 content-start gap-4 md:grid-cols-2 lg:gap-5 xl:grid-cols-1">
            <Panel id="toss" title="Toss" aside="What toss winners chose">
              <div className="grid gap-4">
                <TossSplitBar label={`${recentFrom}+`} toss={v.toss_recent} />
                <TossSplitBar label="All-time" toss={v.toss_all_time} />
                <TossOutcome toss={v.toss_recent} recentFrom={recentFrom} />
              </div>
            </Panel>
            <div className="min-w-0">
              <PhaseBars recent={v.phases_recent} allTime={v.phases_all_time} recentFrom={recentFrom} />
            </div>
            {conditions ? (
              <>
                <PaceSpinSection venueId={v.id} recentFrom={recentFrom} />
                <DewSection venueId={v.id} recentFrom={recentFrom} />
              </>
            ) : (
              <>
                <EmptyState compact icon={Wind} title="Pace vs spin wickets" why="Pace and spin shares of overs and wickets load separately from the venue card." />
                <EmptyState compact icon={Droplets} title="Dew factor" why="Chase win % on high- vs low-dew evenings loads separately from the venue card." />
              </>
            )}
            {notes.length > 0 && (
              <ul className="grid gap-1 px-1 text-[11px] leading-4 text-muted-foreground md:col-span-2 xl:col-span-1">
                {notes.map((n) => (
                  <li key={n} className="flex gap-1.5">
                    <CloudMoon aria-hidden className="mt-px size-3 shrink-0" />
                    {n}
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      </div>
    </article>
  );
}

export function VenueCardSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading venue">
      <Skeleton className="mb-3 h-11 w-28" />
      <div className="mb-6 grid gap-2">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-8 w-64 max-w-[80vw] md:h-9" />
        <Skeleton className="h-4 w-56" />
      </div>
      <div className="grid gap-4 lg:gap-5">
        <TilesSkeleton count={6} className="md:grid-cols-3 xl:grid-cols-6" />
        <div className="grid gap-4 lg:gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(380px,30rem)]">
          <div className="grid content-start gap-4 lg:gap-5">
            <Skeleton className="h-72 rounded-xl" />
            <div className="grid gap-4 lg:gap-5 2xl:grid-cols-2">
              <ChartSkeleton />
              <ChartSkeleton />
            </div>
          </div>
          <div className="grid content-start gap-4 lg:gap-5">
            <Skeleton className="h-72 rounded-xl" />
            <ChartSkeleton />
          </div>
        </div>
      </div>
    </div>
  );
}

export function VenueDetail({ id }: { id: number }) {
  const q = useVenue(id);
  if (q.isPending) return <VenueCardSkeleton />;
  if (q.isError) {
    return (
      <ErrorState
        title={`Couldn’t load venue ${id}`}
        error={q.error}
        onRetry={() => q.refetch()}
        retrying={q.isFetching}
        action={{ href: "/venues", label: "Back to all venues" }}
      />
    );
  }
  return <VenueCardView venue={q.data} conditions />;
}
