"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";

import { Sparkline } from "@/components/data/sparkline";
import { RangeBar } from "@/components/player/range-bar";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { fmt, fmtDate, fmtPct } from "../players/format";
import type { StatFilter } from "../players/types";
import { Panel, QueryError } from "../players/ui";
import { consistencyWord, describeDistribution, fmtPts, rangeScale } from "./format";
import { usePlayerFantasy } from "./queries";
import type { PlayerFantasy } from "./types";
import { CategoryMixBar } from "./ui";

/** Player profile side panel (C1): the shape of the player's Dream11 points in the current scope. */
export function PlayerFantasyPanel({ id, filter, scopeLabel }: { id: string; filter: StatFilter; scopeLabel: string }) {
  const q = usePlayerFantasy(id, filter);
  if (q.isPending) {
    return (
      <div role="status" aria-busy="true" aria-label="Loading fantasy points" className="rounded-xl border border-border bg-card p-4">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="mt-4 h-2.5 w-full rounded-full" />
        <div className="mt-4 grid grid-cols-3 gap-2">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
        <Skeleton className="mt-4 h-24" />
      </div>
    );
  }
  if (q.isError) return <QueryError error={q.error} onRetry={() => q.refetch()} what="fantasy points" />;
  return <FantasyDistribution data={q.data} scopeLabel={scopeLabel} stale={q.isPlaceholderData} />;
}

export function FantasyDistribution({ data: d, scopeLabel, stale = false }: { data: PlayerFantasy; scopeLabel: string; stale?: boolean }) {
  if (d.matches === 0) {
    return (
      <Panel title="Fantasy points" id="fantasy">
        <p className="flex gap-2 text-sm text-muted-foreground">
          <Sparkles aria-hidden className="mt-0.5 size-4 shrink-0" />
          No scored matches in {scopeLabel.toLowerCase()}.
        </p>
      </Panel>
    );
  }
  const hasRange = d.p10 !== null && d.median !== null && d.p90 !== null;
  const scaleMax = rangeScale([d, ...d.by_season]);
  const last = d.last10.map((g) => g.points);
  const seasons = [...d.by_season].sort((a, b) => b.season - a.season);
  return (
    <Panel
      id="fantasy"
      title={`Fantasy points · ${scopeLabel}`}
      className={cn("transition-opacity", stale && "opacity-60")}
      action={
        <Link href="/fantasy" className="rounded text-xs font-medium text-brand outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
          Leaderboards →
        </Link>
      }
    >
      <p className="sr-only">{describeDistribution(d)}</p>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-overline text-muted-foreground">Floor · median · ceiling</span>
        <span className="num text-xs text-muted-foreground">{d.matches} matches</span>
      </div>
      {hasRange && <RangeBar range={{ floor: Math.round(d.p10!), median: Math.round(d.median!), ceiling: Math.round(d.p90!) }} scaleMax={scaleMax} className="mt-2" />}
      <p className="mt-1 text-[11px] leading-4 text-muted-foreground">10th percentile, median and 90th percentile points per match.</p>

      <dl className="num mt-3 grid grid-cols-3 gap-2 text-center">
        <Tile label="Mean" value={fmtPts(d.mean)} hint={`SD ${fmt(d.sd, 0)}`} />
        <Tile label="Steady" value={fmt(d.consistency, 0)} hint={consistencyWord(d.consistency)} />
        <Tile label="Pts / cr" value={fmt(d.ppc, 2)} hint={d.credits !== null ? `${fmt(d.credits, 1)} cr${d.credits_season ? ` · ${d.credits_season}` : ""}` : "no credits"} />
        <Tile label="50+" value={fmtPct(d.pct_50, 0)} hint="of matches" />
        <Tile label="100+" value={fmtPct(d.pct_100, 0)} hint="of matches" />
        <Tile label="Best" value={fmt(d.max)} hint={`total ${fmt(d.total)}`} />
      </dl>

      <h3 className="text-overline mt-4 mb-1.5 text-muted-foreground">Where the points come from</h3>
      <CategoryMixBar mix={d.mix} />

      {last.length > 0 && (
        <>
          <div className="mt-4 mb-1 flex items-baseline justify-between gap-2">
            <h3 className="text-overline text-muted-foreground">Last {last.length} matches</h3>
            <span className="num text-xs text-muted-foreground">avg {fmt(last.reduce((a, b) => a + b, 0) / last.length, 1)}</span>
          </div>
          <Sparkline
            values={last}
            width={280}
            height={40}
            className="h-10 w-full"
            label={`Fantasy points in the last ${last.length} matches, oldest to newest: ${d.last10.map((g) => `${g.points} vs ${g.opponent ?? "?"}`).join(", ")}`}
          />
          <div aria-hidden className="num mt-0.5 flex justify-between text-[11px] text-faint">
            <span>{fmtDate(d.last10[0]?.date, { day: "numeric", month: "short", year: "2-digit" })}</span>
            <span>{fmtDate(d.last10[d.last10.length - 1]?.date, { day: "numeric", month: "short", year: "2-digit" })}</span>
          </div>
        </>
      )}

      {seasons.length > 0 && (
        <>
          <h3 className="text-overline mt-4 mb-1.5 text-muted-foreground">By season</h3>
          <div className="max-h-72 overflow-auto rounded-lg border border-border" role="region" aria-label="Fantasy points by season" tabIndex={0}>
            <table className="num w-full border-separate border-spacing-0 text-[13px]">
              <caption className="sr-only">Dream11 points by season: matches, mean, floor to ceiling and points per credit</caption>
              <thead>
                <tr>
                  {["Season", "M", "Mean", "p10–p90", "Pts/cr"].map((h, i) => (
                    <th key={h} scope="col" className={cn("text-overline sticky top-0 h-8 border-b border-border bg-surface-2 px-2 text-muted-foreground", i === 0 ? "text-left" : "text-right")}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {seasons.map((s) => (
                  <tr key={s.season}>
                    <th scope="row" className="h-8 border-b border-border px-2 text-left font-medium">
                      {s.season}
                      {s.team && <span className="ml-1 text-[11px] font-normal text-muted-foreground">{s.team}</span>}
                    </th>
                    <td className="border-b border-border px-2 text-right">{s.matches}</td>
                    <td className="border-b border-border px-2 text-right font-semibold">{fmtPts(s.mean)}</td>
                    <td className="border-b border-border px-2 text-right text-muted-foreground">
                      {fmt(s.p10, 0)}–{fmt(s.p90, 0)}
                    </td>
                    <td className="border-b border-border px-2 text-right" title={s.credits !== null ? `${fmt(s.credits, 1)} credits${s.credits_season && s.credits_season !== s.season ? ` (${s.credits_season})` : ""}` : undefined}>
                      {fmt(s.ppc, 2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-1.5 text-[11px] leading-4 text-muted-foreground">Points per credit = mean ÷ Dream11 credits (stored from 2025; later seasons reuse the latest).</p>
        </>
      )}
    </Panel>
  );
}

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="min-w-0 rounded-lg bg-surface-2/60 px-1 py-2">
      <dt className="text-overline truncate text-muted-foreground">{label}</dt>
      <dd className="font-condensed text-xl leading-7 font-bold">{value}</dd>
      {hint && <dd className="truncate text-[11px] leading-4 text-muted-foreground">{hint}</dd>}
    </div>
  );
}
