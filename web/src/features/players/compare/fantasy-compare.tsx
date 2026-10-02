"use client";

import { Gauge } from "lucide-react";

import { Sparkline } from "@/components/data/sparkline";
import { RangeBar } from "@/components/player/range-bar";
import { Skeleton } from "@/components/ui/skeleton";

import { consistencyWord, fmtPts, rangeScale } from "../../fantasy/format";
import type { PlayerFantasy } from "../../fantasy/types";
import { fmt, fmtDate } from "../format";
import { QueryError } from "../ui";
import { pcVar } from "./colours";
import { ACCENT, SectionCard } from "./compare-ui";

type FantasyQuery = { data?: PlayerFantasy; isPending: boolean; isError: boolean; error: unknown; refetch: () => unknown };

/**
 * Dream11 shape side by side (GET /fantasy/players/{id}): floor–median–ceiling on one shared
 * scale, mean, consistency, points per credit, and the last-10 sparkline in the player colour.
 */
export function FantasyCompare({ queries, names, scopeLabel, className }: { queries: FantasyQuery[]; names: string[]; scopeLabel: string; className?: string }) {
  const loaded = queries.map((q) => q.data).filter((d): d is PlayerFantasy => Boolean(d));
  const scaleMax = rangeScale(loaded);
  return (
    <SectionCard
      id="fantasy-shape"
      title="Fantasy comparison"
      subtitle={`Dream11 points per match · ${scopeLabel.toLowerCase()}`}
      icon={<Gauge />}
      accent={ACCENT.fantasy}
      className={className}
    >
      <ul className="divide-y divide-border/60">
        {queries.map((q, i) => (
          <li key={names[i]} className="py-3 first:pt-0 last:pb-0">
            {q.isPending ? (
              <div role="status" aria-label={`Loading fantasy points for ${names[i]}`} className="grid gap-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-2.5 w-full rounded-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : q.isError || !q.data ? (
              <QueryError error={q.error} onRetry={() => q.refetch()} what={`fantasy points for ${names[i]}`} />
            ) : (
              <FantasyLine d={q.data} name={names[i]} index={i} scaleMax={scaleMax} />
            )}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[11px] leading-4 text-muted-foreground">
        Bar = 10th to 90th percentile points per match, tick = median, on one scale for all players. Steady = 100 × (1 − SD / mean). Points per credit = mean ÷ Dream11 credits.
      </p>
    </SectionCard>
  );
}

function FantasyLine({ d, name, index, scaleMax }: { d: PlayerFantasy; name: string; index: number; scaleMax: number }) {
  const hasRange = d.p10 !== null && d.median !== null && d.p90 !== null;
  const last = d.last10.map((g) => g.points);
  return (
    <div className="grid gap-x-6 gap-y-3 md:grid-cols-[minmax(0,1fr)_minmax(10rem,14rem)]" data-fantasy-player>
      <div className="min-w-0">
        <div className="mb-2 flex items-baseline justify-between gap-2">
          <span className="inline-flex min-w-0 items-center gap-1.5 text-sm font-semibold">
            <span aria-hidden className="size-2 shrink-0 rounded-full" style={{ background: pcVar(index) }} />
            <span className="truncate">{name}</span>
          </span>
          <span className="num text-xs text-muted-foreground">{fmt(d.matches)} scored matches</span>
        </div>
        {d.matches === 0 ? (
          <p className="text-sm text-muted-foreground">No scored matches in this scope.</p>
        ) : (
          <>
            {hasRange && <RangeBar range={{ floor: Math.round(d.p10!), median: Math.round(d.median!), ceiling: Math.round(d.p90!) }} scaleMax={scaleMax} />}
            <dl className="num mt-2 grid grid-cols-4 gap-2 text-center">
              <Stat label="Mean" value={fmtPts(d.mean)} />
              <Stat label="Steady" value={fmt(d.consistency, 0)} hint={consistencyWord(d.consistency)} />
              <Stat label="Pts / cr" value={fmt(d.ppc, 2)} hint={d.credits !== null ? `${fmt(d.credits, 1)} cr` : "no credits"} />
              <Stat label="Best" value={fmt(d.max)} />
            </dl>
          </>
        )}
      </div>
      {last.length > 0 && (
        <div className="min-w-0 self-end">
          <div className="mb-1 flex items-baseline justify-between gap-2">
            <span className="text-overline text-muted-foreground">Last {last.length}</span>
            <span className="num text-xs text-muted-foreground">avg {fmt(last.reduce((a, b) => a + b, 0) / last.length, 1)}</span>
          </div>
          <Sparkline
            values={last}
            width={224}
            height={44}
            stroke={pcVar(index)}
            className="h-11 w-full"
            label={`${name}: fantasy points in the last ${last.length} matches, oldest to newest: ${last.join(", ")}`}
          />
          <div aria-hidden className="num mt-0.5 flex justify-between text-[11px] text-faint">
            <span>{fmtDate(d.last10[0]?.date, { day: "numeric", month: "short", year: "2-digit" })}</span>
            <span>{fmtDate(d.last10[d.last10.length - 1]?.date, { day: "numeric", month: "short", year: "2-digit" })}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="min-w-0 rounded-lg bg-surface-2/60 px-1 py-1.5">
      <dt className="text-overline truncate text-muted-foreground">{label}</dt>
      <dd className="font-condensed text-lg leading-6 font-bold">{value}</dd>
      {hint && <dd className="truncate text-[11px] leading-4 text-muted-foreground">{hint}</dd>}
    </div>
  );
}
