"use client";

import { useMutation } from "@tanstack/react-query";
import { History, RefreshCw, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { NumberRoll } from "@/components/loaders/number-roll";
import { StumpsLoader } from "@/components/loaders/stumps-loader";
import { PitchView } from "@/components/pitch/pitch-view";
import { PlayerCard, type PlayerStatus } from "@/components/player/player-card";
import { EmptyState } from "@/components/shell/empty-state";
import { SectionHeader } from "@/components/shell/page-header";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoaderVisibility, INLINE_LOADER_TIMING } from "@/hooks/use-loader-visibility";
import { cn } from "@/lib/utils";

import { fmtNum } from "@/features/lab/format";
import { DEFAULT_SEASON, optimiseMatch } from "@/features/predictions/api";
import { finalMatchId, matchLabel, rowToPlayer, teamCounts, xiToPitch } from "@/features/predictions/lib";
import { isNotFound, useMatchPrediction, useSeasonPredictions } from "@/features/predictions/queries";
import type { MatchPrediction, OptimiseResult, PlayerRow, SeasonPredictions } from "@/features/predictions/types";

const CREDIT_CAP = 100;

/**
 * Fantasy builder on the model's honest pre-match predictions (2026 walk-forward): the model XI
 * for the chosen match (default: the 2026 Final), lock / exclude, and a server-side re-optimise.
 */
export function MatchBuilder({ matchId }: { matchId: number | null }) {
  const season = useSeasonPredictions(DEFAULT_SEASON);
  const id = matchId ?? (season.data ? finalMatchId(season.data.matches) : null);
  if (id === null) {
    if (season.isError)
      return <EmptyState icon={History} title="Predictions unavailable" why={(season.error as Error).message} when="Retry in a moment; the stats API may be restarting." action={{ href: "/accuracy", label: "Predictions" }} />;
    return <BuilderSkeleton />;
  }
  return <BuilderBody key={id} matchId={id} season={season.data ?? null} />;
}

function BuilderSkeleton() {
  return (
    <div role="status" aria-label="Loading the predicted XI" className="flex flex-col gap-4">
      <Skeleton className="h-16 rounded-xl" />
      <Skeleton className="h-12 rounded-xl" />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Skeleton className="h-[520px] rounded-2xl" />
        <Skeleton className="h-56 rounded-xl" />
      </div>
    </div>
  );
}

function MatchPicker({ season, value }: { season: SeasonPredictions | null; value: number }) {
  const router = useRouter();
  const matches = season ? [...season.matches].reverse() : [];
  const label = (v: unknown) => {
    const m = matches.find((x) => String(x.match.match_id) === String(v));
    return m ? matchLabel(m.match) : `Match ${String(v)}`;
  };
  return (
    <Select
      value={String(value)}
      onValueChange={(v) => {
        if (v !== null) router.push(`/build?match=${v}`, { scroll: false });
      }}
    >
      <SelectTrigger aria-label="Match" className="h-9 min-w-56 rounded-[10px] bg-card" disabled={!matches.length}>
        <span className="text-xs text-muted-foreground">IPL {DEFAULT_SEASON}</span>
        <SelectValue>{label}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {matches.map((m) => (
          <SelectItem key={m.match.match_id} value={String(m.match.match_id)}>
            {matchLabel(m.match)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function BuilderBody({ matchId, season }: { matchId: number; season: SeasonPredictions | null }) {
  const q = useMatchPrediction(matchId);
  return (
    <div className="flex flex-col gap-4">
      {q.data ? <HonestNote d={q.data} season={season} /> : <Skeleton className="h-16 rounded-xl" />}
      {q.isPending && <BuilderSkeleton />}
      {q.isError &&
        (isNotFound(q.error) ? (
          <EmptyState icon={History} title="No honest prediction for this match" why="The builder only uses predictions made before a match from earlier matches (walk-forward)." when="Pick another 2026 match." action={{ href: "/build", label: "Back to the Final" }} />
        ) : (
          <EmptyState icon={History} title="Couldn’t load the prediction" why={(q.error as Error).message} when="Retry in a moment." action={{ href: "/accuracy", label: "Predictions" }} />
        ))}
      {q.data && <Builder d={q.data} />}
    </div>
  );
}

function HonestNote({ d, season }: { d: MatchPrediction; season: SeasonPredictions | null }) {
  const name = d.match.stage ? `the ${d.year ?? ""} ${d.match.stage}`.replace("  ", " ") : `${d.match.title} of ${d.year ?? ""}`;
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface-2 px-4 py-3 text-sm md:flex-row md:items-center md:justify-between">
      <p className="flex items-start gap-2">
        <History aria-hidden className="mt-0.5 size-4 shrink-0 text-brand" />
        <span>
          <span className="font-medium">
            Model prediction made before {name} using only earlier matches (walk-forward).
          </span>{" "}
          After the match: model XI scored <span className="num font-semibold">{fmtNum(d.totals.model, 0)}</span> pts vs best possible <span className="num font-semibold">{fmtNum(d.totals.best, 0)}</span>.{" "}
          <Link href={`/matches/${d.match.match_id}?tab=predicted`} className="font-medium text-brand hover:underline">
            Full breakdown
          </Link>
        </span>
      </p>
      <MatchPicker season={season} value={d.match.match_id} />
    </div>
  );
}

function Builder({ d }: { d: MatchPrediction }) {
  const model = d.xis.model;
  const [statuses, setStatuses] = useState<Record<string, PlayerStatus>>({});
  const [result, setResult] = useState<OptimiseResult | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(model?.captain ?? null);
  const opt = useMutation({
    mutationFn: (v: { locks: string[]; excludes: string[] }) => optimiseMatch(d.match.match_id, v.locks, v.excludes),
    onSuccess: (r) => setResult(r),
  });
  const pending = opt.isPending;
  const { visible: showLoader } = useLoaderVisibility(pending, INLINE_LOADER_TIMING);
  const xi = result?.xi ?? model;
  if (!xi) return <EmptyState icon={History} title="No feasible XI for this match" why="The optimiser could not build a valid team from the predicted players." action={{ href: "/accuracy", label: "Predictions" }} />;

  const toggle = (id: string, s: Exclude<PlayerStatus, null>) => setStatuses((prev) => ({ ...prev, [id]: prev[id] === s ? null : s }));
  const ids = (s: PlayerStatus) => Object.entries(statuses).filter(([, v]) => v === s).map(([k]) => k);
  const reoptimise = () => opt.mutate({ locks: ids("locked"), excludes: ids("excluded") });
  const reset = () => {
    setStatuses({});
    setResult(null);
    opt.reset();
  };

  const counts = teamCounts(xi);
  const capped = result?.credits_constrained ?? false;
  const inXi = new Set(xi.picks.map((p) => p.player_id));
  const byId = new Map(d.players.map((p) => [p.player_id, p]));
  const selected = (selectedId && byId.get(selectedId)) || null;
  const picked = d.players.filter((p) => inXi.has(p.player_id)).sort((a, b) => (b.pred_mean ?? 0) - (a.pred_mean ?? 0));
  const bench = d.players.filter((p) => !inXi.has(p.player_id)).sort((a, b) => (b.pred_mean ?? 0) - (a.pred_mean ?? 0));
  const projected = Math.round(xi.selected_on);
  const custom = result !== null && (ids("locked").length > 0 || ids("excluded").length > 0);
  const card = (p: PlayerRow) => (
    <PlayerCard key={p.player_id} player={rowToPlayer(p, xi)} status={statuses[p.player_id] ?? null} onToggleLock={(id) => toggle(id, "locked")} onToggleExclude={(id) => toggle(id, "excluded")} />
  );

  return (
    <>
      <div
        role="group"
        aria-label="Team summary"
        aria-busy={pending}
        className="glass sticky top-14 z-30 -mx-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border px-4 py-2.5 text-[13px] md:mx-0 md:rounded-xl md:border"
      >
        <div className="num flex flex-wrap items-center gap-x-2">
          <b className="font-semibold">{xi.picks.length}/11</b>
          <span className="text-faint">·</span>
          <span title={d.credits_note}>
            <b className="font-semibold">{fmtNum(xi.credits_total, 1)}</b>
            <span className="text-muted-foreground">{capped ? `/${CREDIT_CAP} cr` : " cr · no cap"}</span>
            {!xi.credits_complete && <span className="text-muted-foreground"> (partial)</span>}
          </span>
          <span className="text-faint">·</span>
          <span className="text-muted-foreground">
            {Object.entries(counts)
              .map(([t, n]) => `${t} ${n}`)
              .join(" ")}
          </span>
          <span className="text-faint">·</span>
          <span className="text-muted-foreground">roles ✓</span>
          {xi.actual_points !== null && (
            <>
              <span className="text-faint">·</span>
              <span className="text-muted-foreground">
                actual <b className="font-semibold text-foreground">{fmtNum(xi.actual_points, 0)}</b>
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="num">
            <span className="text-muted-foreground">Proj </span>
            {pending && <span className="text-muted-foreground">≈</span>}
            <NumberRoll value={projected} className="font-semibold" label={`Projected ${projected} points`} />
          </span>
          {result && (
            <Button variant="ghost" onClick={reset} disabled={pending} className="h-9 rounded-[10px]" aria-label="Back to the model XI">
              <RotateCcw aria-hidden />
              <span className="max-sm:hidden">Model XI</span>
            </Button>
          )}
          <Button variant="outline" onClick={reoptimise} disabled={pending} className="h-9 rounded-[10px]">
            {showLoader ? <StumpsLoader size={22} label={null} /> : <RefreshCw aria-hidden />}
            {pending ? "Re-optimising…" : "Re-optimise"}
          </Button>
        </div>
        <span className="sr-only" aria-live="polite">
          {pending ? "Re-optimising" : opt.isError ? `Re-optimise failed: ${(opt.error as Error).message}` : `XI updated, projected ${projected}`}
        </span>
      </div>

      {(opt.isError || result) && (
        <p className={cn("-mt-1 text-xs", opt.isError ? "text-negative" : "text-muted-foreground")}>
          {opt.isError
            ? `Couldn’t re-optimise: ${(opt.error as Error).message}`
            : `${custom ? "Your XI with locks / excludes" : "Re-optimised XI"}: ${result!.note}${xi.actual_points !== null ? ` It would have scored ${fmtNum(xi.actual_points, 0)} pts (model XI ${fmtNum(d.totals.model, 0)}).` : ""}`}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <PitchView players={xiToPitch(xi)} statuses={statuses} selectedId={selectedId} onSelect={setSelectedId} />
        <aside aria-label="Selected player" className="flex flex-col gap-3 lg:sticky lg:top-32 lg:self-start">
          {selected ? (
            <>
              <PlayerCard player={rowToPlayer(selected, xi)} status={statuses[selected.player_id] ?? null} onToggleLock={(id) => toggle(id, "locked")} onToggleExclude={(id) => toggle(id, "excluded")} />
              <PredictionCard p={selected} creditsSeason={d.credits_season} />
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Tap a player on the pitch to see their card.</p>
          )}
        </aside>
      </div>

      <section aria-labelledby="all-players" className="flex flex-col gap-1">
        <SectionHeader id="all-players" title={`All players · ${d.match.team1?.short_code ?? ""} v ${d.match.team2?.short_code ?? ""} (${d.players.length})`} />
        <h3 className="text-overline mt-1 mb-1 text-faint">In the XI ({picked.length})</h3>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">{picked.map(card)}</div>
        <h3 className="text-overline mt-4 mb-1 text-faint">Not picked ({bench.length})</h3>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">{bench.map(card)}</div>
      </section>
    </>
  );
}

function PredictionCard({ p, creditsSeason }: { p: PlayerRow; creditsSeason: number | null }) {
  const rows: [string, string][] = [
    ["Predicted mean", fmtNum(p.pred_mean, 1)],
    ["Range p10 – p90", `${fmtNum(p.q10, 0)} – ${fmtNum(p.q90, 0)}`],
    ["Median (p50)", fmtNum(p.q50, 0)],
    ["Last-5 average", fmtNum(p.baseline, 1)],
    [`Credits${creditsSeason ? ` (${creditsSeason})` : ""}`, p.credits !== null ? fmtNum(p.credits, 1) : "–"],
  ];
  return (
    <section aria-label={`${p.name} prediction`} className="rounded-xl border border-border bg-card p-3 shadow-e1">
      <h3 className="text-overline mb-2 text-muted-foreground">Prediction before the match</h3>
      <dl className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-muted-foreground">{k}</dt>
            <dd className="num text-right font-medium">{v}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-3 flex items-baseline justify-between border-t border-border pt-2 text-sm">
        <span className="text-muted-foreground">After the match</span>
        <span className="num">
          <b className="font-semibold">{fmtNum(p.actual, 0)}</b> pts{p.actual_rank ? <span className="text-muted-foreground"> · #{p.actual_rank} in match</span> : null}
        </span>
      </div>
    </section>
  );
}
