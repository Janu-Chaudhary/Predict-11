"use client";

import { Check, History, LayoutGrid, List, SearchX } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { StatTile } from "@/components/data/stat-tile";
import { PitchView } from "@/components/pitch/pitch-view";
import { CaptainRoundel } from "@/components/player/captain-roundel";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { RoleChip } from "@/components/player/role-chip";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { PredRange, PredRangeLegend } from "../lab/charts";
import { fmtNum, fmtPct, fmtSigned } from "../lab/format";
import { Segmented } from "../lab/ui";
import { PointsBars } from "./accuracy-view";
import { xiToPitch } from "./lib";
import { isNotFound, useMatchPrediction } from "./queries";
import type { MatchPrediction, PlayerRow, XiCard, XiKey, XiPlayer } from "./types";

const XI_LABEL: Record<XiKey, string> = { model: "Model", baseline: "Baseline", best: "Best possible" };
const XI_NOTE: Record<XiKey, string> = {
  model: "Picked before the match by the optimiser on the model’s predicted mean (Dream11 role limits, max 10 per team, C ×2, VC ×1.5, no credit cap), then scored with actual points.",
  baseline: "Same optimiser on each player’s last-5-games average: the simple rule the model has to beat.",
  best: "Picked after the match on actual points: the most any XI could have scored (the ceiling).",
};

export function MatchPredictedXi({ matchId }: { matchId: number }) {
  const q = useMatchPrediction(matchId);
  if (q.isPending)
    return (
      <div role="status" aria-label="Loading the predicted XI" className="grid gap-4">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-[36rem] rounded-xl" />
      </div>
    );
  if (q.isError)
    return isNotFound(q.error) ? (
      <EmptyState
        icon={SearchX}
        title="No honest prediction for this match"
        why="Predicted XIs are shown only for matches the model predicted before they were played, using earlier matches only (the 2026 walk-forward season and the 2025 frozen-model test)."
        when="Future matches get a prediction once they are played and the model is re-run walk-forward."
        action={{ href: "/accuracy", label: "All predicted XIs" }}
      />
    ) : (
      <EmptyState icon={SearchX} title="Couldn’t load the prediction" why={(q.error as Error).message} when="Retry in a moment." action={{ href: "/accuracy", label: "All predicted XIs" }} />
    );
  return <PredictedBody d={q.data} />;
}

function PredictedBody({ d }: { d: MatchPrediction }) {
  const [key, setKey] = useState<XiKey>("model");
  const [view, setView] = useState<"pitch" | "list">("pitch");
  const xi = d.xis[key];
  const t = d.totals;
  const model = d.xis.model;
  const cap = model?.picks.find((p) => p.player_id === model.captain) ?? null;
  return (
    <div className="grid grid-cols-1 gap-4 lg:gap-5">
      <p className="flex items-start gap-2 rounded-xl border border-border bg-surface-2 px-4 py-3 text-sm">
        <History aria-hidden className="mt-0.5 size-4 shrink-0 text-brand" />
        <span>
          <span className="font-medium">{d.method_note}</span> <span className="text-muted-foreground">{d.credits_note}</span>{" "}
          <Link href={`/accuracy${d.year && d.year !== 2026 ? `?season=${d.year}` : ""}`} className="font-medium text-brand hover:underline">
            Whole season
          </Link>
        </span>
      </p>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatTile
          label="Model XI"
          value={t.model}
          format={(n) => fmtNum(n, 0)}
          unit="pts"
          delta={t.model_minus_baseline !== null ? { value: Math.round(t.model_minus_baseline), label: "vs baseline" } : undefined}
        />
        <StatTile label="Baseline XI" value={t.baseline} format={(n) => fmtNum(n, 0)} unit="pts" hint="last-5 average" />
        <StatTile label="Best possible" value={t.best} format={(n) => fmtNum(n, 0)} unit="pts" hint={`model got ${fmtPct(t.model_share_of_best)}`} />
        <StatTile
          label="Model captain"
          value={cap ? fmtNum(cap.actual, 0) : null}
          unit="pts"
          hint={
            cap ? (
              <span className="inline-flex items-center gap-1">
                {cap.name}
                {t.captain_top2_model ? <Check aria-label="top-2 scorer" className="size-3.5 text-positive" strokeWidth={3} /> : " · not top 2"}
              </span>
            ) : undefined
          }
        />
        <StatTile label="Error per player" value={t.mae_model} format={(n) => fmtNum(n, 1)} unit="pts" hint={`baseline ${fmtNum(t.mae_base, 1)} · in range ${fmtPct(t.coverage)}`} />
        <StatTile
          label="Model XI credits"
          value={model?.credits_total ?? null}
          format={(n) => fmtNum(n, 1)}
          hint={d.credits_season ? `${d.credits_season} credits${model?.credits_complete ? "" : ", partial"} · no cap` : "credits unavailable"}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:gap-5 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <section aria-labelledby="pxi-pitch" className="min-w-0 rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 id="pxi-pitch" className="text-overline text-muted-foreground">
              Predicted XI
            </h2>
            <div className="flex flex-wrap gap-2">
              <Segmented size="sm" label="Which XI" value={key} onChange={setKey} options={(Object.keys(XI_LABEL) as XiKey[]).map((k) => ({ key: k, label: `${XI_LABEL[k]} ${fmtNum(d.xis[k]?.actual_points, 0)}` }))} />
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
          <p className="mb-3 text-sm text-muted-foreground">{XI_NOTE[key]}</p>
          {!xi ? (
            <p className="text-sm text-muted-foreground">No feasible XI for this match.</p>
          ) : view === "pitch" ? (
            <>
              <PitchView players={xiToPitch(xi)} pointsLabel={pitchLabel(xi)} className="mx-auto max-w-3xl" />
              <p className="mt-2 text-center text-xs text-muted-foreground">Under each player: predicted mean → actual points (C/VC multiplier applied to the actual).</p>
            </>
          ) : (
            <XiList xi={xi} />
          )}
        </section>

        <div className="grid min-w-0 content-start gap-4">
          <section aria-labelledby="pxi-totals" className="rounded-xl border border-border bg-card p-4 shadow-e1 lg:p-5">
            <h2 id="pxi-totals" className="text-overline mb-3 text-muted-foreground">
              Totals, scored with actual points
            </h2>
            <PointsBars model={t.model} baseline={t.baseline} best={t.best} className="gap-2.5 [&_dl]:text-sm" />
            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-muted-foreground">Model vs baseline</dt>
              <dd className={cn("num text-right font-semibold", (t.model_minus_baseline ?? 0) > 0 ? "text-positive" : (t.model_minus_baseline ?? 0) < 0 ? "text-negative" : "")}>{fmtSigned(t.model_minus_baseline, 0)} pts</dd>
              <dt className="text-muted-foreground">Model players in best XI</dt>
              <dd className="num text-right">{model ? `${model.overlap_with_best} of 11` : "–"}</dd>
              <dt className="text-muted-foreground">Baseline captain top 2</dt>
              <dd className="text-right">{t.captain_top2_baseline === null ? "–" : t.captain_top2_baseline ? "yes" : "no"}</dd>
            </dl>
          </section>
          {xi && view === "pitch" && (
            <section aria-labelledby="pxi-list" className="rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4">
              <h2 id="pxi-list" className="text-overline mb-1 text-muted-foreground">
                {XI_LABEL[key]} XI, player by player
              </h2>
              <XiList xi={xi} />
            </section>
          )}
        </div>
      </div>

      <PlayersTable d={d} />
    </div>
  );
}

function pitchLabel(xi: XiCard) {
  const by = new Map(xi.picks.map((p) => [p.player_id, p]));
  return (p: { id: string }) => {
    const x = by.get(p.id);
    if (!x) return "";
    return `${fmtNum(x.pred_mean, 0)} → ${fmtNum(x.points, 0)}`;
  };
}

function XiList({ xi }: { xi: XiCard }) {
  return (
    <ul className="divide-y divide-border">
      {xi.picks.map((p: XiPlayer) => (
        <li key={p.player_id} className="flex items-center gap-3 py-2">
          <PlayerAvatar name={p.name} src={p.image_url} team={p.team} size="sm" />
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-1.5">
              <span className="truncate text-sm font-medium">{p.name}</span>
              {p.player_id === xi.captain && <CaptainRoundel kind="C" />}
              {p.player_id === xi.vice_captain && <CaptainRoundel kind="VC" />}
            </span>
            <span className="num text-xs text-muted-foreground">
              pred {fmtNum(p.pred_mean, 0)} ({fmtNum(p.q10, 0)}–{fmtNum(p.q90, 0)}) · actual {fmtNum(p.actual, 0)}
              {p.multiplier !== 1 ? ` × ${p.multiplier}` : ""}
              {p.credits !== null ? ` · ${fmtNum(p.credits, 1)} cr` : ""}
            </span>
          </span>
          <TeamBadge team={p.team} />
          <RoleChip role={p.role} className="max-sm:hidden" />
          <span className="num w-12 text-right text-sm font-semibold">{fmtNum(p.points, 0)}</span>
        </li>
      ))}
      <li className="flex justify-between py-2 text-sm font-semibold">
        <span>
          Total (actual points)
          {xi.credits_total !== null && <span className="num ml-2 text-xs font-normal text-muted-foreground">{fmtNum(xi.credits_total, 1)} credits{xi.credits_complete ? "" : " (partial)"}</span>}
        </span>
        <span className="num">{fmtNum(xi.actual_points, 0)}</span>
      </li>
    </ul>
  );
}

function XiMark({ on, mult, label, title }: { on: boolean; mult: number | null; label: string; title: string }) {
  if (!on) return <span aria-hidden className="inline-flex size-6 items-center justify-center rounded-md text-[11px] text-faint">·</span>;
  const role = mult === 2 ? " (captain)" : mult === 1.5 ? " (vice-captain)" : "";
  return (
    <span title={`${title}${role}`} aria-label={`${title}${role}`} className="relative inline-flex size-6 items-center justify-center rounded-md bg-surface-2 text-[11px] font-semibold">
      {label}
      {mult === 2 && <span className="absolute -top-1 -right-1 size-2 rounded-full bg-primary" />}
      {mult === 1.5 && <span className="bg-brand-gradient absolute -top-1 -right-1 size-2 rounded-full" />}
    </span>
  );
}

function PlayersTable({ d }: { d: MatchPrediction }) {
  const max = Math.max(60, ...d.players.flatMap((p) => [p.q90 ?? 0, p.actual ?? 0])) + 5;
  const columns: StatColumn<PlayerRow>[] = [
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
          <PlayerAvatar name={p.name} src={p.image_url} team={p.team} size="xs" />
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
    {
      key: "range",
      header: "Predicted range vs actual",
      align: "left",
      value: (p) => p.pred_mean,
      cell: (p) => (
        <div className="w-48 md:w-72 xl:w-96">
          <PredRange q10={p.q10} q50={p.q50} q90={p.q90} mean={p.pred_mean} actual={p.actual} baseline={p.baseline} max={max} />
        </div>
      ),
    },
    { key: "mean", header: "Pred", sortable: true, value: (p) => p.pred_mean, cell: (p) => <span className="font-semibold">{fmtNum(p.pred_mean, 1)}</span> },
    { key: "p10", header: "p10", sortable: true, hideBelow: "md", value: (p) => p.q10, cell: (p) => fmtNum(p.q10, 0) },
    { key: "p50", header: "p50", sortable: true, hideBelow: "md", value: (p) => p.q50, cell: (p) => fmtNum(p.q50, 0) },
    { key: "p90", header: "p90", sortable: true, hideBelow: "md", value: (p) => p.q90, cell: (p) => fmtNum(p.q90, 0) },
    { key: "base", header: "Last-5", sortable: true, hideBelow: "lg", value: (p) => p.baseline, cell: (p) => fmtNum(p.baseline, 1) },
    { key: "actual", header: "Actual", sortable: true, value: (p) => p.actual, cell: (p) => <span className="font-semibold">{fmtNum(p.actual, 0)}</span> },
    { key: "rank", header: "Rank", sortable: true, defaultDir: "asc", hideBelow: "sm", value: (p) => p.actual_rank, cell: (p) => (p.actual_rank ? `#${p.actual_rank}` : "–") },
    { key: "credits", header: "Cr", sortable: true, hideBelow: "lg", value: (p) => p.credits, cell: (p) => fmtNum(p.credits, 1) },
    {
      key: "xi",
      header: "In XI",
      align: "center",
      sortable: true,
      value: (p) => Number(p.in_model_xi) * 4 + Number(p.in_base_xi) * 2 + Number(p.in_best_xi),
      cell: (p) => (
        <span className="inline-flex gap-1">
          <XiMark on={p.in_model_xi} mult={p.model_mult} label="M" title="Model XI" />
          <XiMark on={p.in_base_xi} mult={p.base_mult} label="B" title="Baseline XI" />
          <XiMark on={p.in_best_xi} mult={p.best_mult} label="H" title="Best possible XI" />
        </span>
      ),
    },
  ];
  return (
    <section aria-labelledby="pxi-all" className="grid gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="pxi-all" className="text-overline text-muted-foreground">
          Every player: predicted before the match vs what happened
        </h2>
        <PredRangeLegend />
      </div>
      <StatTable columns={columns} rows={d.players} rowKey={(p) => p.player_id} caption="Predicted points range (p10–p90, median and mean) and actual points for every player in the match, sorted by predicted mean" initialSort={{ key: "mean", dir: "desc" }} dense maxHeight="min(80dvh, 56rem)" />
      <p className="text-xs text-muted-foreground">M / B / H = in the model, baseline or best-possible XI (dot = captain or vice-captain). Rank = finishing position by actual points.</p>
    </section>
  );
}
