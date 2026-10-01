"use client";

import { ArrowDown, Trophy, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Sparkline } from "@/components/data/sparkline";
import { SeasonSelect } from "@/components/data/season-select";
import { RowsSkeleton } from "@/components/loaders/page-skeletons";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { RangeBar } from "@/components/player/range-bar";
import { RoleChip } from "@/components/player/role-chip";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { cn } from "@/lib/utils";

import { displayName, fmt, photoOf, teamCode } from "../players/format";
import { QueryError } from "../players/ui";
import {
  consistencyWord,
  describeDistribution,
  filterLeaderboard,
  fmtPts,
  leaderHref,
  MIN_MATCHES,
  rangeScale,
  ROLE_FILTERS,
  sortLeaderboard,
  SORTS,
  sortValueLabel,
  type LeaderState,
} from "./format";
import { useLeaderboard } from "./queries";
import type { LeaderRow, LeaderSort, RoleFilter } from "./types";
import { FantasySubnav, Segmented, ToolLink } from "./ui";

export const CURRENT_FANTASY_SEASON = 2026;
/** Seasons with stored Dream11 points (every IPL season is scored with the rules in force). */
export const FANTASY_SEASONS = Array.from({ length: CURRENT_FANTASY_SEASON - 2008 + 1 }, (_, i) => CURRENT_FANTASY_SEASON - i);

const ROW_LIMIT = 60;

/**
 * Fantasy leaderboards (C2): season totals and the shape of each player's points: floor
 * (p10), median and ceiling (p90) on a range bar, a last-10 sparkline and a consistency score.
 */
export function FantasyLeaderboard({ state }: { state: LeaderState }) {
  const router = useRouter();
  const q = useLeaderboard({ season: state.season, role: state.role, minMatches: state.min });
  const go = (next: Partial<LeaderState>) => router.replace(leaderHref({ ...state, ...next }, CURRENT_FANTASY_SEASON), { scroll: false });

  const data = q.data;
  const rows = data ? sortLeaderboard(filterLeaderboard(data.rows, state.role, state.min), state.sort) : [];
  const shown = rows.slice(0, ROW_LIMIT);
  const scaleMax = rangeScale(shown);
  // The leaderboard contract has no per-row form yet; the column appears once it does.
  const spark = shown.some((r) => r.recent.length > 0);
  const noCredits = state.sort === "ppc" && data && !data.credits_available;

  return (
    <>
      <PageHeader
        overline="Fantasy · Dream11 points"
        title="Fantasy leaderboards"
        subtitle="Who scored, how reliably, and at what price. Every IPL match is scored with the Dream11 rules in force on the day."
        actions={
          <ToolLink href={`/fantasy/best-xi${state.season !== CURRENT_FANTASY_SEASON ? `?season=${state.season}` : ""}`}>
            <Trophy aria-hidden className="size-4" /> Best XIs
          </ToolLink>
        }
      />
      <FantasySubnav active="leaderboards" season={state.season !== CURRENT_FANTASY_SEASON ? state.season : null} />

      <div className="mb-3 grid gap-3 rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4">
        <div className="flex flex-wrap items-center gap-2">
          <SeasonSelect value={state.season} seasons={FANTASY_SEASONS} onValueChange={(s) => go({ season: s })} />
          <label className="inline-flex items-center gap-2">
            <span className="text-overline text-muted-foreground">Min matches</span>
            <select
              value={state.min}
              onChange={(e) => go({ min: Number(e.target.value) })}
              className="num h-9 rounded-[10px] border border-input bg-card px-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {MIN_MATCHES.map((m) => (
                <option key={m} value={m}>
                  {m}+
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-overline text-muted-foreground">Sort by</span>
          <Segmented<LeaderSort> label="Sort leaderboard by" value={state.sort} onChange={(s) => go({ sort: s })} options={SORTS.map((s) => ({ key: s.key, label: s.short, title: s.hint }))} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-overline text-muted-foreground">Role</span>
          <Segmented<RoleFilter>
            label="Filter by role"
            value={state.role}
            onChange={(r) => go({ role: r })}
            options={ROLE_FILTERS.map((r) => ({ key: r, label: r === "ALL" ? "All" : r }))}
          />
        </div>
      </div>

      {q.isError ? (
        <QueryError error={q.error} onRetry={() => q.refetch()} what="the fantasy leaderboard" />
      ) : q.isPending || !data ? (
        <div role="status" aria-busy="true" aria-label="Loading leaderboard">
          <RowsSkeleton rows={10} />
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No players match these filters"
          why={`Nobody${state.role !== "ALL" ? ` listed as ${state.role}` : ""} played ${state.min}+ matches in IPL ${state.season}.`}
          action={{ href: leaderHref({ ...state, role: "ALL", min: 1 }, CURRENT_FANTASY_SEASON), label: "Show everyone" }}
        />
      ) : (
        <section aria-labelledby="lb-h" className={cn("min-w-0 rounded-xl border border-border bg-card shadow-e1 transition-opacity", q.isPlaceholderData && "opacity-60")} aria-busy={q.isFetching}>
          <header className="flex flex-wrap items-baseline justify-between gap-2 px-3 pt-3 md:px-4">
            <h2 id="lb-h" className="text-overline text-muted-foreground">
              IPL {state.season} · {SORTS.find((s) => s.key === state.sort)?.label}
            </h2>
            <p className="num text-xs text-muted-foreground" aria-live="polite">
              {q.isFetching ? "Updating…" : `${rows.length} players${rows.length > ROW_LIMIT ? `, top ${ROW_LIMIT} shown` : ""}`}
            </p>
          </header>
          {noCredits && (
            <p className="mx-3 mt-2 rounded-lg border border-warning/30 bg-warning/8 px-3 py-2 text-xs md:mx-4">
              <span className="font-semibold">No credits for {state.season}.</span> Dream11 credits are stored for 2025 onwards, so points per credit can’t be ranked here.
            </p>
          )}
          <LeaderHeader sort={state.sort} onSort={(s) => go({ sort: s })} spark={spark} />
          <ol className="divide-y divide-border">
            {shown.map((r, i) => (
              <LeaderItem key={r.player.id} row={r} rank={i + 1} sort={state.sort} scaleMax={scaleMax} spark={spark} />
            ))}
          </ol>
          <p className="border-t border-border px-3 py-2.5 text-xs text-muted-foreground md:px-4">
            Bar: floor (10th percentile) to ceiling (90th) of points per match, tick = median.{spark && " Line: last 10 matches."} Steady = 100 × (1 − SD ÷ mean).
          </p>
        </section>
      )}
    </>
  );
}

const GRID_SPARK = "lg:grid-cols-[2rem_minmax(0,15rem)_minmax(8rem,1fr)_5rem_3rem_4rem_4rem_4rem_4.5rem]";
const GRID_PLAIN = "lg:grid-cols-[2rem_minmax(0,15rem)_minmax(8rem,1fr)_3rem_4rem_4rem_4rem_4.5rem]";

/** Desktop column header; the four metric headers re-sort (aria-sort on the active one). */
function LeaderHeader({ sort, onSort, spark }: { sort: LeaderSort; onSort: (s: LeaderSort) => void; spark: boolean }) {
  const col = (key: LeaderSort, label: string) => (
    <div role="columnheader" aria-sort={sort === key ? "descending" : "none"} className="text-right">
      <button
        type="button"
        onClick={() => onSort(key)}
        className={cn("inline-flex min-h-6 items-center gap-0.5 rounded px-0.5 uppercase outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring", sort === key && "text-foreground")}
      >
        {sort === key && <ArrowDown aria-hidden className="size-3" />}
        {label}
      </button>
    </div>
  );
  return (
    <div aria-hidden className={cn("text-overline mt-2 hidden h-9 items-center gap-3 border-y border-border bg-surface-2 px-4 text-muted-foreground lg:grid", spark ? GRID_SPARK : GRID_PLAIN)}>
      <div className="text-right">#</div>
      <div>Player</div>
      <div>Floor · median · ceiling</div>
      {spark && <div>Last 10</div>}
      <div className="text-right">M</div>
      {col("mean", "Mean")}
      {col("consistency", "Steady")}
      {col("ppc", "Pts/cr")}
      {col("total", "Total")}
    </div>
  );
}

function LeaderItem({ row: r, rank, sort, scaleMax, spark }: { row: LeaderRow; rank: number; sort: LeaderSort; scaleMax: number; spark: boolean }) {
  const name = displayName(r.player);
  const code = teamCode(r.team);
  const hasRange = r.p10 !== null && r.median !== null && r.p90 !== null;
  const metric = SORTS.find((s) => s.key === sort)!;
  return (
    <li>
      <Link
        href={`/players/${encodeURIComponent(r.player.id)}`}
        aria-label={`${rank}. ${name}${r.team ? `, ${r.team}` : ""}${r.role ? `, ${r.role}` : ""}: ${metric.label} ${sortValueLabel(r, sort)}; ${describeDistribution(r)}`}
        className={cn(
          "grid grid-cols-[1.5rem_auto_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 px-3 py-2.5 outline-none hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset md:px-4 lg:min-h-[52px] lg:gap-y-0 lg:py-1.5",
          spark ? GRID_SPARK : GRID_PLAIN,
        )}
      >
        <span className="num text-right text-xs text-faint lg:text-sm">{rank}</span>
        {/* Player cell: avatar + name (+ meta on mobile). On desktop the avatar shares the name column. */}
        <PlayerAvatar name={name} src={photoOf(r.player)} team={code ?? undefined} size="sm" className="lg:hidden" />
        <span className="flex min-w-0 items-center gap-2.5">
          <PlayerAvatar name={name} src={photoOf(r.player)} team={code ?? undefined} size="sm" className="max-lg:hidden" />
          <span className="min-w-0">
            <span className="flex min-w-0 items-center gap-1.5">
              <span className="truncate text-sm font-medium">{name}</span>
            </span>
            <span className="num flex items-center gap-1.5 text-xs text-muted-foreground">
              {code && <TeamBadge team={code} />}
              {r.role && <RoleChip role={r.role} showIcon={false} className="h-5" />}
              <span className="whitespace-nowrap lg:hidden">
                {r.matches}m · {fmtPts(r.mean)}
              </span>
            </span>
          </span>
        </span>
        {/* Mobile: the active metric, big. */}
        <span className="w-16 text-right lg:hidden">
          <span className="num block text-base font-semibold">{sortValueLabel(r, sort)}</span>
          <span className="block text-[11px] leading-4 text-muted-foreground">{sort === "consistency" ? consistencyWord(r.consistency) : metric.short.toLowerCase()}</span>
        </span>

        {/* Range + sparkline: second line on mobile, own columns on desktop. */}
        <span className="col-span-4 flex min-w-0 items-center gap-3 lg:col-span-1">
          <span className="min-w-0 flex-1">
            {hasRange ? (
              <RangeBar range={{ floor: Math.round(r.p10!), median: Math.round(r.median!), ceiling: Math.round(r.p90!) }} scaleMax={scaleMax} className="pt-1" />
            ) : (
              <span className="text-xs text-faint">Range needs 3+ matches</span>
            )}
          </span>
          {spark && <Sparkline
            values={r.recent}
            width={72}
            height={24}
            className="shrink-0 lg:hidden"
            label={r.recent.length ? `Last ${r.recent.length} matches, oldest to newest: ${r.recent.join(", ")} points` : "No recent matches"}
          />}
        </span>
        {spark && <span className="max-lg:hidden">
          <Sparkline values={r.recent} width={72} height={24} label={r.recent.length ? `Last ${r.recent.length} matches: ${r.recent.join(", ")} points` : "No recent matches"} />
        </span>}
        <span className="num text-right text-sm max-lg:hidden">{r.matches}</span>
        <Metric active={sort === "mean"}>{fmt(r.mean, 1)}</Metric>
        <Metric active={sort === "consistency"} title={consistencyWord(r.consistency)}>
          {fmt(r.consistency, 0)}
        </Metric>
        <Metric active={sort === "ppc"}>{fmt(r.ppc, 2)}</Metric>
        <Metric active={sort === "total"}>{fmt(r.total)}</Metric>
      </Link>
    </li>
  );
}

function Metric({ active, children, title }: { active: boolean; children: React.ReactNode; title?: string }) {
  return (
    <span title={title} className={cn("num text-right text-sm max-lg:hidden", active ? "font-semibold text-foreground" : "text-muted-foreground")}>
      {children}
    </span>
  );
}
