"use client";

import { History, ListChecks, RotateCcw, Wand2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { StumpsLoader } from "@/components/loaders/stumps-loader";
import { RowsSkeleton } from "@/components/loaders/page-skeletons";
import { SectionHeader } from "@/components/shell/page-header";
import { EmptyState } from "@/components/shell/empty-state";
import { cn } from "@/lib/utils";

import { useScenarioPicks, useScenarios } from "../queries";
import type { ScenarioPick, Scenarios, TeamRef } from "../types";
import { FixturePicker } from "./fixture-picker";
import { ScenarioTeamList } from "./scenario-teams";
import { replaceQuery } from "../url";
import { ErrorState } from "./states";

/** How far back a finished season's replay starts by default (the last ~2 weeks of league games). */
const REPLAY_WINDOW = 14;


export function ScenariosPanel({ season, initialAfter }: { season: number; initialAfter: number | null }) {
  // Probe = the season as it stands (all league games played so far).
  const probe = useScenarios(season, null);
  const played = probe.data?.after_match ?? null;
  const league = probe.data?.league_matches ?? null;
  const complete = probe.data ? probe.data.remaining_matches === 0 : false;
  const defaultAfter = complete && played !== null ? Math.max(0, played - REPLAY_WINDOW) : null;

  const [after, setAfter] = useState<number | null>(initialAfter);
  const effective = after ?? defaultAfter;
  const [sliderValue, setSliderValue] = useState<number | null>(null);

  // Debounce slider → query (250 ms, §7.2); the thumb itself moves instantly.
  useEffect(() => {
    if (sliderValue === null) return;
    const t = setTimeout(() => {
      setAfter(sliderValue);
      replaceQuery({ after: String(sliderValue) });
    }, 250);
    return () => clearTimeout(t);
  }, [sliderValue]);

  const base = useScenarios(season, effective);
  const [picks, setPicks] = useState<Map<number, number>>(new Map());
  // A new replay point invalidates the picks (different fixtures remain).
  const [picksFor, setPicksFor] = useState(effective);
  if (picksFor !== effective) {
    setPicksFor(effective);
    setPicks(new Map());
  }
  const pickList: ScenarioPick[] = useMemo(() => [...picks].map(([match_id, winner_id]) => ({ match_id, winner_id })), [picks]);
  const picked = useScenarioPicks(season, effective, pickList);

  if (probe.isPending) return <ScenariosSkeleton />;
  if (probe.isError) return <ErrorState title="Couldn't load the scenarios" error={probe.error} onRetry={() => probe.refetch()} />;

  const usingPicks = pickList.length > 0;
  const view: Scenarios | undefined = usingPicks ? (picked.data ?? base.data) : base.data;
  const pending = usingPicks ? picked.isFetching || picked.isPlaceholderData || !picked.data : base.isFetching && base.isPlaceholderData;
  const pickError = usingPicks && picked.isError;

  const teamsById = new Map<number, TeamRef>((view ?? probe.data).teams.map((t) => [t.team.id, t.team]));
  const fixtures = base.data?.remaining ?? [];
  const sliderShown = sliderValue ?? effective ?? played ?? 0;

  const onPick = (matchId: number, winnerId: number | null) =>
    setPicks((prev) => {
      const next = new Map(prev);
      if (winnerId === null) next.delete(matchId);
      else next.set(matchId, winnerId);
      return next;
    });
  const fillActual = () =>
    setPicks(new Map(fixtures.filter((f) => f.actual_winner_id !== null).map((f) => [f.match_id, f.actual_winner_id!])));

  return (
    <div className="grid gap-4 lg:grid-cols-12 lg:gap-6">
      <div className="grid content-start gap-4 lg:col-span-7">
        {/* Replay slider (any season with games played). */}
        {played !== null && played > 0 && (
          <section aria-labelledby="replay-h" className="rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="replay-h" className="text-overline flex items-center gap-1.5 text-muted-foreground">
                <History aria-hidden className="size-3.5" /> Replay as of match
              </h2>
              <span className="num text-sm">
                <span className="font-semibold">{sliderShown}</span>
                <span className="text-muted-foreground"> / {league}</span>
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={played}
              step={1}
              value={sliderShown}
              onChange={(e) => setSliderValue(Number(e.target.value))}
              aria-label="Replay the table as it stood after league match"
              aria-valuetext={`After match ${sliderShown} of ${league}`}
              className="mt-3 h-11 w-full cursor-pointer accent-[var(--primary)]"
            />
            <div className="num flex justify-between text-[11px] text-faint">
              <span>Start</span>
              <span>{complete ? "End of league" : `Now (M${played})`}</span>
            </div>
            {base.data && (
              <p className="mt-2 text-xs text-muted-foreground">
                <span className="num">{base.data.remaining_matches}</span> league games left ·{" "}
                {base.data.method === "exhaustive" ? (
                  <>
                    all <span className="num">{base.data.outcomes_evaluated.toLocaleString("en-IN")}</span> outcomes enumerated
                  </>
                ) : (
                  <>
                    <span className="num">{base.data.outcomes_evaluated.toLocaleString("en-IN")}</span> simulated seasons (Monte Carlo)
                  </>
                )}
                {complete && effective === defaultAfter && after === null && " · finished season: replaying the run-in"}
              </p>
            )}
          </section>
        )}

        <section aria-labelledby="odds-h">
          <SectionHeader
            id="odds-h"
            title={usingPicks ? "Odds with your picks" : "Qualification odds"}
            action={
              <span aria-live="polite" className="flex min-h-7 items-center gap-1.5 text-xs text-muted-foreground">
                {pending && usingPicks ? (
                  <>
                    <StumpsLoader size={24} label={null} /> Recomputing…
                  </>
                ) : usingPicks && picked.data ? (
                  `${pickList.length} pick${pickList.length === 1 ? "" : "s"} applied`
                ) : null}
              </span>
            }
          />
          {pickError && (
            <p role="alert" className="mb-2 rounded-lg border border-negative/30 bg-negative/8 px-3 py-2 text-xs">
              Couldn&apos;t recompute with your picks; showing the last good odds. Your picks are kept.{" "}
              <button type="button" className="font-semibold text-brand underline-offset-2 hover:underline" onClick={() => picked.refetch()}>
                Retry
              </button>
            </p>
          )}
          {base.isError && !view ? (
            <ErrorState error={base.error} onRetry={() => base.refetch()} />
          ) : view ? (
            <ScenarioTeamList teams={view.teams} pending={pending} />
          ) : (
            <RowsSkeleton rows={10} />
          )}
          {view && (
            <p className="mt-2 text-xs text-muted-foreground">
              Solid bar: through on points alone. Hatched: only if net run rate breaks a tie their way. Assumes{" "}
              {view.assumption.replace(/^each/, "every")}.{!view.flags_exact && " Clinched/eliminated flags are proven by bounds, so they may be conservative."}
            </p>
          )}
        </section>
      </div>

      <section aria-labelledby="picks-h" className="content-start lg:col-span-5">
        <SectionHeader
          id="picks-h"
          title={`Pick the winners${fixtures.length ? ` · ${fixtures.length} left` : ""}`}
          action={
            fixtures.length > 0 && (
              <div className="flex items-center gap-1">
                {fixtures.some((f) => f.actual_winner_id !== null) && (
                  <button
                    type="button"
                    onClick={fillActual}
                    className="inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs font-medium text-brand outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <Wand2 aria-hidden className="size-3.5" /> Actual results
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setPicks(new Map())}
                  disabled={!usingPicks}
                  className="inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs font-medium text-muted-foreground outline-none hover:bg-surface-2 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40"
                >
                  <RotateCcw aria-hidden className="size-3.5" /> Reset
                </button>
              </div>
            )
          }
        />
        {base.isPending ? (
          <RowsSkeleton rows={6} />
        ) : fixtures.length === 0 ? (
          <EmptyState
            compact
            icon={ListChecks}
            title="No games left to pick"
            why={`Every league game ${complete ? "of this season has been played" : "up to this point is already decided"}.`}
            when="Drag the replay slider back to any earlier match to pick the run-in yourself."
          />
        ) : (
          <div className={cn("max-h-[min(70dvh,40rem)] overflow-y-auto rounded-xl border border-border bg-card shadow-e1")}>
            <FixturePicker fixtures={fixtures} teamsById={teamsById} picks={picks} onPick={onPick} />
          </div>
        )}
      </section>
    </div>
  );
}

function ScenariosSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading scenarios" className="grid gap-4 lg:grid-cols-12 lg:gap-6">
      <div className="grid gap-4 lg:col-span-7">
        <RowsSkeleton rows={2} />
        <RowsSkeleton rows={10} />
      </div>
      <RowsSkeleton rows={8} className="lg:col-span-5 lg:self-start" />
    </div>
  );
}
