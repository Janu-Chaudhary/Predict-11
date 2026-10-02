"use client";

import { LayoutGrid, List } from "lucide-react";
import { useState } from "react";

import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { StatTile } from "@/components/data/stat-tile";
import { PitchView } from "@/components/pitch/pitch-view";
import { CaptainRoundel } from "@/components/player/captain-roundel";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { RoleChip } from "@/components/player/role-chip";
import { TeamBadge } from "@/components/player/team-badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { Player } from "@/lib/mock";
import type { TeamCode } from "@/lib/tokens";
import { cn } from "@/lib/utils";

import { PredRange, PredRangeLegend } from "./charts";
import { PHASE_LABEL, fmtDate, fmtNum, fmtPct, fmtSigned } from "./format";
import { MatchPicker } from "./match-picker";
import { useMatch } from "./queries";
import type { MatchDetail, MatchPlayer, Telemetry, XiKey, XiResult } from "./types";
import { LearnMore, Segmented, Term, useLabState } from "./ui";

const XI_LABEL: Record<XiKey, string> = { model: "Model XI", baseline: "Baseline XI", hindsight: "Hindsight XI" };
const ROLE_ORDER = { WK: 0, BAT: 1, AR: 2, BOWL: 3 } as const;

/** Optimiser XI → the shared PitchView's Player shape (points = actual, before C/VC). */
export function xiToPitch(xi: XiResult): Player[] {
  return [...xi.picks]
    .sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role] || b.value - a.value)
    .map((p) => {
      const pts = Math.round(p.actual ?? 0);
      return {
        id: p.playerId,
        name: p.name,
        team: p.team as TeamCode,
        role: p.role,
        credits: 0,
        projection: { floor: pts, median: pts, ceiling: pts },
        captain: p.playerId === xi.captain,
        viceCaptain: p.playerId === xi.viceCaptain,
        photoUrl: p.imageUrl,
      };
    });
}

export function overlap(a: XiResult | null, b: XiResult | null): number {
  if (!a || !b) return 0;
  const s = new Set(b.picks.map((p) => p.playerId));
  return a.picks.filter((p) => s.has(p.playerId)).length;
}

export function PredictionsTab({ t, version }: { t: Telemetry; version: string }) {
  const state = useLabState();
  const q = useMatch(version, state.match);
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[20rem_minmax(0,1fr)] xl:grid-cols-[22rem_minmax(0,1fr)]">
      <div className="min-w-0 lg:sticky lg:top-20 lg:self-start">
        <MatchPicker version={version} />
      </div>
      <div className="min-w-0 space-y-4">
        {state.match === null && (
          <section className="rounded-xl border border-dashed border-border bg-card/60 p-5">
            <h2 className="text-base font-semibold">Pick a match</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Every match of the {t.protocol.testSeason ?? "test"} test season and the {t.protocol.wfSeason ?? "walk-forward"} walk-forward season, with each player&apos;s predicted range, the
              baseline, what actually happened, and the three XIs (model, baseline, hindsight).
            </p>
          </section>
        )}
        {state.match !== null && q.isPending && <Skeleton className="h-96 rounded-xl" />}
        {q.isError && <p className="text-sm text-muted-foreground">Couldn&apos;t load this match: {(q.error as Error).message}</p>}
        {q.data && <MatchView d={q.data} dim={q.isPlaceholderData} />}
      </div>
    </div>
  );
}

function MatchView({ d, dim }: { d: MatchDetail; dim: boolean }) {
  const [xiKey, setXiKey] = useState<XiKey>("model");
  const [view, setView] = useState<"pitch" | "list">("pitch");
  const xi = d.xi[xiKey];
  const max = Math.max(60, ...d.players.flatMap((p) => [p.q90 ?? 0, p.actual ?? 0])) + 5;
  const { team1, team2 } = d.info;
  const columns: StatColumn<MatchPlayer>[] = [
    {
      key: "name",
      header: "Player",
      align: "left",
      sticky: true,
      sortable: true,
      value: (p) => p.name,
      className: "bg-card",
      cell: (p) => (
        <div className="flex min-w-[11rem] items-center gap-2">
          <PlayerAvatar name={p.name} src={p.imageUrl} team={p.team} size="xs" />
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium">{p.name}</span>
            <span className="flex items-center gap-1">
              <TeamBadge team={p.team} size="sm" />
              <RoleChip role={p.role} showIcon={false} className="max-sm:hidden" />
            </span>
          </span>
        </div>
      ),
    },
    { key: "range", header: "Predicted range vs actual", align: "left", value: (p) => p.predMean, cell: (p) => <div className="w-48 md:w-64"><PredRange q10={p.q10} q50={p.q50} q90={p.q90} mean={p.predMean} actual={p.actual} baseline={p.baseline} max={max} /></div> },
    { key: "mean", header: "Mean", sortable: true, value: (p) => p.predMean, cell: (p) => <span className="font-semibold">{fmtNum(p.predMean, 1)}</span> },
    { key: "p10", header: "p10", sortable: true, hideBelow: "md", value: (p) => p.q10, cell: (p) => fmtNum(p.q10, 0) },
    { key: "p50", header: "p50", sortable: true, hideBelow: "md", value: (p) => p.q50, cell: (p) => fmtNum(p.q50, 0) },
    { key: "p90", header: "p90", sortable: true, hideBelow: "md", value: (p) => p.q90, cell: (p) => fmtNum(p.q90, 0) },
    { key: "base", header: "Last-5", sortable: true, value: (p) => p.baseline, cell: (p) => fmtNum(p.baseline, 1) },
    { key: "actual", header: "Actual", sortable: true, value: (p) => p.actual, cell: (p) => <span className="font-semibold">{fmtNum(p.actual, 0)}</span> },
    {
      key: "err",
      header: "Act − pred",
      sortable: true,
      hideBelow: "sm",
      value: (p) => (p.actual === null || p.predMean === null ? null : p.actual - p.predMean),
      cell: (p) => (p.actual === null || p.predMean === null ? "–" : <span className={cn(Math.abs(p.actual - p.predMean) > 30 && "text-negative")}>{fmtSigned(p.actual - p.predMean, 0)}</span>),
    },
    {
      key: "xi",
      header: "In XI",
      align: "center",
      sortable: true,
      value: (p) => Number(p.inModelXi) * 4 + Number(p.inBaseXi) * 2 + Number(p.inBestXi),
      cell: (p) => (
        <span className="inline-flex gap-1">
          <XiMark on={p.inModelXi} mult={p.modelMult} label="M" title="Model XI" />
          <XiMark on={p.inBaseXi} mult={p.baseMult} label="B" title="Baseline XI" />
          <XiMark on={p.inBestXi} mult={p.bestMult} label="H" title="Hindsight XI" />
        </span>
      ),
    },
  ];

  return (
    <div className={cn("space-y-4", dim && "opacity-60 transition-opacity")}>
      <header className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-e1">
        {team1 && <TeamBadge team={team1.code} size="md" />}
        <div className="min-w-0 flex-1">
          <h2 className="text-title truncate">
            {team1?.name ?? "?"} <span className="text-muted-foreground">v</span> {team2?.name ?? "?"}
          </h2>
          <p className="num text-xs text-muted-foreground">
            {fmtDate(d.info.date)}
            {d.info.venue ? ` · ${d.info.venue}` : ""}
            {d.info.matchNumber ? ` · match ${d.info.matchNumber}` : ""} · {PHASE_LABEL[d.phase]} set
          </p>
        </div>
        {team2 && <TeamBadge team={team2.code} size="md" opponent={team1?.code} side="away" />}
      </header>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatTile label="Model XI" value={d.xi.model?.actualPoints ?? null} format={(n) => fmtNum(n, 0)} unit="pts" hint="actual points, C ×2 / VC ×1.5" />
        <StatTile
          label="Baseline XI"
          value={d.xi.baseline?.actualPoints ?? null}
          format={(n) => fmtNum(n, 0)}
          unit="pts"
          delta={d.xi.model?.actualPoints != null && d.xi.baseline?.actualPoints != null ? { value: Math.round(d.xi.model.actualPoints - d.xi.baseline.actualPoints), label: "model vs this" } : undefined}
        />
        <StatTile label="Hindsight XI" value={d.xi.hindsight?.actualPoints ?? null} format={(n) => fmtNum(n, 0)} unit="pts" hint={`model shares ${overlap(d.xi.model, d.xi.hindsight)} of 11 players`} />
        <StatTile label="MAE model" value={d.maeModel} format={(n) => fmtNum(n, 1)} hint={`baseline ${fmtNum(d.maeBase, 1)}`} />
        <StatTile label="In p10–p90" value={d.coverage} format={(n) => fmtPct(n)} hint="target 80%" />
        <StatTile label="Players" value={d.players.length} hint="both XIs incl. impact subs" />
      </div>

      <section className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-overline text-muted-foreground">Every player: prediction vs what happened</h3>
          <PredRangeLegend />
        </div>
        <StatTable columns={columns} rows={d.players} rowKey={(p) => p.playerId} caption="Predicted points range, baseline and actual points for every player in the match" initialSort={{ key: "mean", dir: "desc" }} dense maxHeight="min(80dvh, 52rem)" />
        <LearnMore
          learn={{
            concept: (
              <>
                The model gives a <Term id="quantile">p10–p90 range</Term>, a median and a mean for each player. The range should contain the actual score about 80% of the time (
                <Term id="coverage">coverage</Term>); the mean drives the optimiser.
              </>
            ),
            read: "Violet band = p10–p90; black tick = median; violet diamond = mean; gold ring = last-5 baseline; dot = actual (green inside the range, red outside). M / B / H mark the model, baseline and hindsight XIs (C/VC shown).",
            good: "Most green dots; the big scorers having wide upper ranges; the model's mean closer to the actual than the gold ring more often than not.",
            ours: `${fmtPct(d.coverage)} of players landed inside their range. MAE ${fmtNum(d.maeModel, 1)} (model) vs ${fmtNum(d.maeBase, 1)} (baseline) in this match.`,
          }}
        />
      </section>

      <section className="rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-overline text-muted-foreground">The three XIs</h3>
          <div className="flex flex-wrap gap-2">
            <Segmented size="sm" label="Which XI" value={xiKey} onChange={setXiKey} options={(Object.keys(XI_LABEL) as XiKey[]).map((k) => ({ key: k, label: `${XI_LABEL[k]} ${fmtNum(d.xi[k]?.actualPoints, 0)}` }))} />
            <Segmented
              size="sm"
              label="View"
              value={view}
              onChange={setView}
              options={[
                { key: "pitch", label: <LayoutGrid aria-label="Pitch" className="size-4" /> },
                { key: "list", label: <List aria-label="List" className="size-4" /> },
              ]}
            />
          </div>
        </div>
        <p className="mb-3 text-sm text-muted-foreground">
          {xiKey === "model" && "Picked by the exact optimiser on the model's mean predictions (Dream11 rules, no credit cap), then scored with actual points."}
          {xiKey === "baseline" && "Same optimiser, but on each player's last-5-games average."}
          {xiKey === "hindsight" && "Picked after the match on actual points: the best score anyone could have had (the ceiling)."}
        </p>
        {!xi ? (
          <p className="text-sm text-muted-foreground">No feasible XI for this match.</p>
        ) : view === "pitch" ? (
          <PitchView players={xiToPitch(xi)} className="mx-auto max-w-3xl" />
        ) : (
          <XiTable xi={xi} />
        )}
      </section>
    </div>
  );
}

function XiMark({ on, mult, label, title }: { on: boolean; mult: number | null; label: string; title: string }) {
  if (!on) return <span aria-hidden className="inline-flex size-6 items-center justify-center rounded-md text-[11px] text-faint">·</span>;
  return (
    <span title={`${title}${mult === 2 ? " (captain)" : mult === 1.5 ? " (vice-captain)" : ""}`} className="relative inline-flex size-6 items-center justify-center rounded-md bg-surface-2 text-[11px] font-semibold">
      {label}
      {mult === 2 && <span className="absolute -top-1 -right-1 size-2 rounded-full bg-primary" />}
      {mult === 1.5 && <span className="bg-brand-gradient absolute -top-1 -right-1 size-2 rounded-full" />}
    </span>
  );
}

function XiTable({ xi }: { xi: XiResult }) {
  return (
    <ul className="divide-y divide-border">
      {xi.picks.map((p) => (
        <li key={p.playerId} className="flex items-center gap-3 py-2">
          <PlayerAvatar name={p.name} src={p.imageUrl} team={p.team} size="sm" />
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-1.5">
              <span className="truncate text-sm font-medium">{p.name}</span>
              {p.playerId === xi.captain && <CaptainRoundel kind="C" />}
              {p.playerId === xi.viceCaptain && <CaptainRoundel kind="VC" />}
            </span>
            <span className="num text-xs text-muted-foreground">
              selected on {fmtNum(p.value, 1)} · actual {fmtNum(p.actual, 0)}
              {p.multiplier !== 1 ? ` × ${p.multiplier}` : ""}
            </span>
          </span>
          <TeamBadge team={p.team} />
          <RoleChip role={p.role} className="max-sm:hidden" />
          <span className="num w-12 text-right text-sm font-semibold">{fmtNum(p.points, 0)}</span>
        </li>
      ))}
      <li className="flex justify-between py-2 text-sm font-semibold">
        <span>Total (actual points)</span>
        <span className="num">{fmtNum(xi.actualPoints, 0)}</span>
      </li>
    </ul>
  );
}
