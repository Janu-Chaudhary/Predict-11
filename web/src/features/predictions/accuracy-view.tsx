"use client";

import { Check, FlaskConical, History, TrendingDown, TrendingUp, X } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { StatBarChart, StatLineChart } from "@/components/charts/stat-charts";
import { SeasonSelect } from "@/components/data/season-select";
import { StatTile } from "@/components/data/stat-tile";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { fmtDate, fmtNum, fmtPct, fmtSigned } from "../lab/format";
import { Segmented } from "../lab/ui";
import { cumulative, filterMatches, type MatchFilter } from "./lib";
import { isNotFound, useSeasonPredictions } from "./queries";
import type { CallRef, SeasonMatch, SeasonPredictions } from "./types";

export const SERIES = {
  model: { label: "Model XI", color: "var(--chart-1)" },
  baseline: { label: "Baseline XI", color: "var(--chart-2)" },
  best: { label: "Best possible", color: "var(--chart-3)" },
} as const;

export function AccuracyView({ year }: { year: number }) {
  const q = useSeasonPredictions(year);
  const d = q.data;
  const seasons = d?.seasons.map((s) => s.year) ?? [year];
  return (
    <>
      <PageHeader
        overline="Predictions · honest backtest"
        title={`${year} predicted XIs`}
        subtitle={
          d?.frozen
            ? "The team one frozen model (trained on earlier seasons, never retrained) would have picked before every match, against what actually happened."
            : "The team our model would have picked before every match of the season, against what actually happened. Predicted before the match using only earlier matches (walk-forward)."
        }
        actions={seasons.length > 1 ? <SeasonSelect value={year} seasons={seasons} hrefFor={(y) => `/accuracy?season=${y}`} label="Season" /> : undefined}
      />
      {q.isPending && <AccuracySkeleton />}
      {q.isError &&
        (isNotFound(q.error) ? (
          <EmptyState
            icon={History}
            title={`No honest predictions for ${year}`}
            why="Only seasons the model predicted before each match (walk-forward or a frozen test model) are shown; the final model has seen this data, so using it here would leak the answers."
            when="With the next training run that holds this season out."
            action={{ href: "/accuracy", label: "Back to 2026" }}
          />
        ) : (
          <EmptyState icon={History} title="Couldn’t load the predictions" why={(q.error as Error).message} when="Retry in a moment; the stats API may be restarting." action={{ href: "/lab", label: "Open the Model Lab" }} />
        ))}
      {d && <SeasonBody d={d} dim={q.isPlaceholderData} />}
    </>
  );
}

function AccuracySkeleton() {
  return (
    <div role="status" aria-label="Loading predictions" className="grid gap-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-80 rounded-xl" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }, (_, i) => (
          <Skeleton key={i} className="h-44 rounded-xl" />
        ))}
      </div>
    </div>
  );
}

function SeasonBody({ d, dim }: { d: SeasonPredictions; dim: boolean }) {
  const s = d.summary;
  const rows = useMemo(() => cumulative(d.matches), [d.matches]);
  const [filter, setFilter] = useState<MatchFilter>("all");
  const shown = filterMatches(d.matches, filter);
  const lost = filterMatches(d.matches, "lost").length;
  const last = rows.at(-1);
  return (
    <div className={cn("grid grid-cols-1 gap-4 lg:gap-5", dim && "opacity-60 transition-opacity")}>
      <MethodBanner d={d} />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatTile
          label="Model XI per match"
          value={s.model_mean}
          format={(n) => fmtNum(n, 0)}
          unit="pts"
          delta={s.model_mean !== null && s.baseline_mean !== null ? { value: Math.round(s.model_mean - s.baseline_mean), label: "vs baseline" } : undefined}
        />
        <StatTile label="Baseline XI per match" value={s.baseline_mean} format={(n) => fmtNum(n, 0)} unit="pts" hint="last-5-games average" />
        <StatTile label="Best possible per match" value={s.best_mean} format={(n) => fmtNum(n, 0)} unit="pts" hint={`model got ${fmtPct(s.model_share_of_best)} of it`} />
        <StatTile label="Captain in top 2" value={s.captain_top2_model} format={(n) => fmtPct(n)} hint={`baseline ${fmtPct(s.captain_top2_baseline)}`} />
        <StatTile label="Beat the baseline" value={`${s.beat_baseline}/${s.matches}`} hint={`${fmtPct(s.beat_baseline_rate)} of matches`} />
        <StatTile label="Season total" value={s.model_total} format={(n) => fmtNum(n, 0)} unit="pts" hint={`baseline ${fmtNum(s.baseline_total, 0)}`} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <section aria-labelledby="pred-cum" className="min-w-0 rounded-xl border border-border bg-card p-4 shadow-e1 lg:p-5">
          <h2 id="pred-cum" className="text-overline mb-3 text-muted-foreground">
            Season so far
          </h2>
          <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] [&>*]:min-w-0">
            <StatLineChart
              title="Cumulative fantasy points (thousands)"
              summary={`After ${d.matches.length} matches: model XIs ${fmtNum(last?.model, 0)}, baseline ${fmtNum(last?.baseline, 0)}, best possible ${fmtNum(last?.best, 0)} points.`}
              data={rows.map((r) => ({ match: r.match, model: r.model / 1000, baseline: r.baseline / 1000, best: r.best / 1000 }))}
              xKey="match"
              series={[
                { key: "model", ...SERIES.model },
                { key: "baseline", ...SERIES.baseline },
                { key: "best", ...SERIES.best, dashed: true },
              ]}
              height={420}
            />
            <StatBarChart
              title="Model minus baseline, per match"
              summary={`The model XI out-scored the baseline XI in ${s.beat_baseline} of ${s.matches} matches and trailed in ${lost}.`}
              data={rows.map((r) => ({ match: r.match, margin: r.margin }))}
              xKey="match"
              series={[{ key: "margin", label: "Model − baseline (pts)", color: "var(--chart-1)" }]}
              height={420}
            />
          </div>
        </section>
        <div className="grid content-start gap-4">
          <CallCard kind="best" call={s.best_call} match={d.matches.find((m) => m.match.match_id === s.best_call?.match_id)} />
          <CallCard kind="worst" call={s.worst_call} match={d.matches.find((m) => m.match.match_id === s.worst_call?.match_id)} />
          <HowMade d={d} />
        </div>
      </div>

      <section aria-labelledby="pred-matches" className="grid gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="pred-matches" className="text-overline text-muted-foreground">
            Every match <span className="num">({shown.length})</span>
          </h2>
          <Segmented
            size="sm"
            label="Filter matches"
            value={filter}
            onChange={setFilter}
            options={[
              { key: "all", label: `All ${d.matches.length}` },
              { key: "won", label: `Model won ${s.beat_baseline}` },
              { key: "lost", label: `Baseline won ${lost}` },
            ]}
          />
        </div>
        <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {[...shown].reverse().map((m) => (
            <li key={m.match.match_id} className="min-w-0">
              <MatchCard m={m} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function MethodBanner({ d }: { d: SeasonPredictions }) {
  return (
    <p className="flex items-start gap-2 rounded-xl border border-border bg-surface-2 px-4 py-3 text-sm">
      <History aria-hidden className="mt-0.5 size-4 shrink-0 text-brand" />
      <span>
        <span className="font-medium">{d.method_note}</span> <span className="text-muted-foreground">{d.credits_note}</span>
      </span>
    </p>
  );
}

function HowMade({ d }: { d: SeasonPredictions }) {
  const block = d.wf_block ?? 10;
  return (
    <section aria-labelledby="pred-how" className="rounded-xl border border-border bg-card p-4 shadow-e1 lg:p-5">
      <h2 id="pred-how" className="font-display text-lg leading-6 font-semibold">
        How these were made
      </h2>
      <ol className="mt-3 grid list-decimal gap-2 pl-5 text-sm text-muted-foreground marker:text-faint">
        {d.frozen ? (
          <li>One model trained on seasons before {d.year} predicted every {d.year} match. It was never retrained during the season.</li>
        ) : (
          <li>
            The model was retrained every <span className="num">{block}</span> matches on <span className="text-foreground">earlier matches only</span>, then predicted the next {block}. It never saw a match before predicting it.
          </li>
        )}
        <li>The optimiser picked the best 11 on the predicted mean: Dream11 role limits (1–8 each) and max 10 per team, captain ×2, vice-captain ×1.5, no credit cap.</li>
        <li>The baseline XI used each player’s last-5-games average instead; best possible is picked after the match on actual points.</li>
        <li>Every XI is scored with the points players actually made.</li>
      </ol>
      <p className="mt-3 text-xs text-faint">The final model behind live projections was trained on {d.year} too, so it is never used on this page.</p>
      <Link href="/lab" className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-brand outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
        <FlaskConical aria-hidden className="size-4" /> Open the Model Lab
      </Link>
    </section>
  );
}

function CallCard({ kind, call, match }: { kind: "best" | "worst"; call: CallRef | null; match?: SeasonMatch }) {
  if (!call || !match) return null;
  const Icon = kind === "best" ? TrendingUp : TrendingDown;
  const t1 = match.match.team1?.short_code;
  const t2 = match.match.team2?.short_code;
  return (
    <Link
      href={`/matches/${call.match_id}?tab=predicted`}
      className="flex items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-e1 transition-colors outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className={cn("flex size-10 shrink-0 items-center justify-center rounded-lg bg-surface-2", kind === "best" ? "text-positive" : "text-negative")}>
        <Icon aria-hidden className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="text-overline block text-muted-foreground">{kind === "best" ? "Best call" : "Worst call"}</span>
        <span className="block truncate text-sm font-medium">
          {call.title} · {t1} v {t2}
        </span>
        <span className="num block text-xs text-muted-foreground">
          {fmtNum(match.model_xi_points, 0)} vs {fmtNum(match.baseline_xi_points, 0)} baseline
        </span>
      </span>
      <span className={cn("num font-condensed text-2xl font-bold", call.margin >= 0 ? "text-positive" : "text-negative")}>{fmtSigned(call.margin, 0)}</span>
    </Link>
  );
}

export function PointsBars({ model, baseline, best, className }: { model: number | null; baseline: number | null; best: number | null; className?: string }) {
  const max = Math.max(1, best ?? 0, model ?? 0, baseline ?? 0);
  const rows = [
    { key: "model", v: model, ...SERIES.model },
    { key: "baseline", v: baseline, ...SERIES.baseline },
    { key: "best", v: best, ...SERIES.best },
  ];
  return (
    <dl className={cn("grid gap-1.5", className)}>
      {rows.map((r) => (
        <div key={r.key} className="grid grid-cols-[5.5rem_minmax(0,1fr)_2.75rem] items-center gap-2 text-xs">
          <dt className="truncate text-muted-foreground">{r.label}</dt>
          <dd className="h-2 overflow-hidden rounded-full bg-surface-3" aria-hidden>
            <div className="h-full rounded-full" style={{ width: `${((r.v ?? 0) / max) * 100}%`, background: r.color }} />
          </dd>
          <dd className={cn("num text-right", r.key === "model" ? "font-semibold text-foreground" : "text-muted-foreground")}>{fmtNum(r.v, 0)}</dd>
        </div>
      ))}
    </dl>
  );
}

function MatchCard({ m }: { m: SeasonMatch }) {
  const h = m.match;
  const t1 = h.team1?.short_code ?? "?";
  const t2 = h.team2?.short_code ?? "?";
  const cap = m.captain;
  return (
    <Link
      href={`/matches/${h.match_id}?tab=predicted`}
      aria-label={`${h.title}, ${h.team1?.name ?? t1} v ${h.team2?.name ?? t2}: model XI ${fmtNum(m.model_xi_points, 0)}, baseline ${fmtNum(m.baseline_xi_points, 0)}, best ${fmtNum(m.best_xi_points, 0)} points`}
      className="flex h-full flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-e1 transition-colors outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-overline min-w-0 truncate text-muted-foreground">
          {h.title} · <span className="num">{fmtDate(h.date)}</span>
        </p>
        {m.model_minus_baseline !== null && (
          <span
            className={cn(
              "num shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold",
              m.model_minus_baseline > 0 ? "bg-positive/12 text-positive" : m.model_minus_baseline < 0 ? "bg-negative/12 text-negative" : "bg-surface-2 text-muted-foreground",
            )}
            title="Model XI minus baseline XI"
          >
            {fmtSigned(m.model_minus_baseline, 0)}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <TeamBadge team={t1} size="md" />
        <span className="font-display text-base font-semibold">{t1}</span>
        <span className="text-xs text-muted-foreground">v</span>
        <span className="font-display text-base font-semibold">{t2}</span>
        <TeamBadge team={t2} size="md" opponent={t1} side="away" />
      </div>
      {h.result_text && <p className="-mt-1 truncate text-xs text-muted-foreground">{h.result_text}</p>}
      <PointsBars model={m.model_xi_points} baseline={m.baseline_xi_points} best={m.best_xi_points} />
      {cap && (
        <div className="mt-auto flex items-center gap-2 border-t border-border pt-3">
          <PlayerAvatar name={cap.player.name} src={cap.player.image_url} team={cap.player.team} size="md" />
          <span className="min-w-0 flex-1">
            <span className="text-overline block text-muted-foreground">Captain</span>
            <span className="block truncate text-sm font-medium">{cap.player.name}</span>
          </span>
          <span className="text-right">
            <span className="num block text-sm font-semibold">{fmtNum(cap.actual, 0)} pts</span>
            <span className="num block text-[11px] text-muted-foreground">pred {fmtNum(cap.predicted, 0)}</span>
          </span>
          {cap.top2 ? (
            <span title="Captain was one of the match’s top-2 scorers" className="flex size-6 items-center justify-center rounded-full bg-positive text-white">
              <Check aria-label="Top-2 scorer" className="size-4" strokeWidth={3} />
            </span>
          ) : (
            <span title={cap.actual_rank ? `Captain finished #${cap.actual_rank} in the match` : "Captain was not a top-2 scorer"} className="flex size-6 items-center justify-center rounded-full bg-surface-2 text-faint">
              <X aria-label="Not a top-2 scorer" className="size-3.5" />
            </span>
          )}
        </div>
      )}
    </Link>
  );
}
