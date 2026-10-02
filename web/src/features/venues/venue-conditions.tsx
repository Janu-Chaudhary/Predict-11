"use client";

import { Droplets, Wind } from "lucide-react";
import { useState } from "react";

import { StatLineChart } from "@/components/charts/stat-charts";
import { ConfidenceBadge } from "@/components/data/confidence-badge";
import { ChartSkeleton } from "@/components/loaders/page-skeletons";
import { EmptyState } from "@/components/shell/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { useDew, usePaceSpin, useTossTrend } from "./conditions";
import type { BowlGroupLine, DewReport, DewSeason, PaceSpin, TossTrend } from "./conditions-api";
import { fmtInt, fmtPct, fmtRate, isNum } from "./format";
import { Panel } from "./venue-sections";

/** Venue samples: a chase-win % over 6 evenings is anecdote. */
const VENUE_THRESHOLDS = { medium: 10, high: 25 };

function Loading({ h = "h-56" }: { h?: string }) {
  return <Skeleton className={cn("rounded-xl", h)} />;
}

function Failed({ title, onRetry }: { title: string; onRetry: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-negative/30 bg-negative/8 p-4 text-sm">
      <p className="font-semibold">Couldn’t load {title.toLowerCase()}</p>
      <button type="button" onClick={onRetry} className="mt-2 rounded text-sm font-medium text-brand outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
        Retry
      </button>
    </div>
  );
}

function Toggle({ value, onChange, recentFrom }: { value: "recent" | "all"; onChange: (v: "recent" | "all") => void; recentFrom: number }) {
  return (
    <div role="group" aria-label="Window" className="inline-flex rounded-[10px] bg-surface-2 p-0.5">
      {(["recent", "all"] as const).map((k) => (
        <button
          key={k}
          type="button"
          aria-pressed={value === k}
          onClick={() => onChange(k)}
          className={cn(
            "inline-flex h-7 items-center rounded-lg px-2 text-xs font-medium text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring",
            value === k && "bg-card text-foreground shadow-e1",
          )}
        >
          {k === "recent" ? `${recentFrom}+` : "All-time"}
        </button>
      ))}
    </div>
  );
}

/* ---------------- Toss trend ---------------- */

export function TossTrendChart({ data, recentFrom }: { data: TossTrend; recentFrom: number }) {
  const seasons = [...data.seasons].sort((a, b) => a.season - b.season);
  if (seasons.length === 0) return null;
  const recent = seasons.filter((s) => s.season >= recentFrom);
  return (
    <StatLineChart
      title="Toss and chase by season"
      summary={`At ${data.venue}, toss winners chose to field ${fmtPct(data.recent.toss_field_pct)} of the time since ${recentFrom} (all-time ${fmtPct(data.all_time.toss_field_pct)}); chasing sides won ${fmtPct(data.recent.chase_win_pct)}. By season: ${recent.map((s) => `${s.season} field ${fmtPct(s.toss_field_pct)}, chase won ${fmtPct(s.chase_win_pct)}`).join("; ")}.`}
      data={seasons.map((s) => ({
        season: String(s.season),
        field: isNum(s.toss_field_pct) ? Math.round(s.toss_field_pct) : null,
        chase: isNum(s.chase_win_pct) ? Math.round(s.chase_win_pct) : null,
      }))}
      xKey="season"
      series={[
        { key: "field", label: "Chose to field %", color: "var(--chart-3)" },
        { key: "chase", label: "Chase won %", color: "var(--chart-1)", dashed: true },
      ]}
      height={208}
    />
  );
}

export function TossTrendSection({ venueId, recentFrom }: { venueId: number; recentFrom: number }) {
  const q = useTossTrend(venueId);
  if (q.isPending) return <ChartSkeleton />;
  if (q.isError) return <Failed title="Toss trend" onRetry={() => q.refetch()} />;
  return (
    <div className="min-w-0">
      <TossTrendChart data={q.data} recentFrom={recentFrom} />
    </div>
  );
}

/* ---------------- Pace vs spin ---------------- */

function ShareBar({ label, pace, spin }: { label: string; pace: number | null; spin: number | null }) {
  const p = isNum(pace) ? pace : 0;
  const s = isNum(spin) ? spin : 0;
  const tot = p + s || 1;
  const pw = (p / tot) * 100;
  return (
    <div>
      <div className="mb-1 text-xs font-medium">{label}</div>
      <div role="img" aria-label={`${label}: pace ${fmtPct(pace)}, spin ${fmtPct(spin)}`} className="flex h-6 overflow-hidden rounded-md bg-surface-3">
        <div className="flex items-center bg-chart-2/80 pl-2 text-[11px] font-semibold text-background" style={{ width: `${pw}%` }}>
          {pw >= 20 && `Pace ${Math.round(p)}%`}
        </div>
        <div className="flex flex-1 items-center justify-end bg-chart-4/70 pr-2 text-[11px] font-semibold text-background">{100 - pw >= 16 && `Spin ${Math.round(s)}%`}</div>
      </div>
    </div>
  );
}

export function PaceSpinView({ data, recentFrom }: { data: PaceSpin; recentFrom: number }) {
  const [win, setWin] = useState<"recent" | "all">("recent");
  const w = win === "recent" ? data.recent : data.all_time;
  const g = (name: string): BowlGroupLine | undefined => w.groups.find((x) => x.group === name);
  const pace = g("pace");
  const spin = g("spin");
  const types = [...w.by_type].filter((t) => t.balls > 0).sort((a, b) => b.wickets - a.wickets);
  return (
    <Panel id="pace-spin" title="Pace vs spin" aside={<Toggle value={win} onChange={setWin} recentFrom={recentFrom} />}>
      {!pace && !spin ? (
        <p className="text-sm text-muted-foreground">No bowling recorded in this window.</p>
      ) : (
        <div className="grid gap-3">
          <ShareBar label="Share of wickets" pace={pace?.wickets_share_pct ?? null} spin={spin?.wickets_share_pct ?? null} />
          <ShareBar label="Share of overs" pace={pace?.overs_share_pct ?? null} spin={spin?.overs_share_pct ?? null} />
          <table className="num w-full text-[13px]">
            <caption className="sr-only">Pace and spin at this venue, {win === "recent" ? `${recentFrom}+` : "all-time"}</caption>
            <thead>
              <tr className="text-overline text-muted-foreground">
                <th scope="col" className="h-8 text-left font-semibold">Group</th>
                <th scope="col" className="text-right font-semibold">Wkts</th>
                <th scope="col" className="text-right font-semibold">Econ</th>
                <th scope="col" className="text-right font-semibold">SR</th>
                <th scope="col" className="text-right font-semibold">Avg</th>
              </tr>
            </thead>
            <tbody>
              {[pace, spin].filter((x): x is BowlGroupLine => Boolean(x)).map((x) => (
                <tr key={x.group} className="border-t border-border">
                  <th scope="row" className="h-9 text-left font-medium capitalize">{x.group}</th>
                  <td className="text-right font-semibold">{fmtInt(x.wickets)}</td>
                  <td className="text-right">{fmtRate(x.economy, 2)}</td>
                  <td className="text-right">{fmtRate(x.strike_rate)}</td>
                  <td className="text-right">{fmtRate(x.average)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {types.length > 0 && (
            <details className="group rounded-lg border border-border">
              <summary className="flex min-h-11 cursor-pointer items-center px-3 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring">By bowling type ({types.length})</summary>
              <ul className="divide-y divide-border border-t border-border">
                {types.map((t) => (
                  <li key={t.group} className="num flex min-h-9 items-center gap-2 px-3 text-[13px]">
                    <span className="min-w-0 flex-1 truncate capitalize">{t.group}</span>
                    <span className="w-16 text-right font-semibold">{t.wickets} wk</span>
                    <span className="w-16 text-right text-muted-foreground">econ {fmtRate(t.economy, 1)}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
          <p className="text-[11px] leading-4 text-muted-foreground">
            {w.matches} matches. SR = balls per wicket.
            {isNum(w.unknown_ball_pct) && w.unknown_ball_pct > 0 && ` Bowler type unknown for ${fmtRate(w.unknown_ball_pct)}% of balls.`}
          </p>
        </div>
      )}
    </Panel>
  );
}

export function PaceSpinSection({ venueId, recentFrom }: { venueId: number; recentFrom: number }) {
  const q = usePaceSpin(venueId);
  if (q.isPending) return <Loading h="h-72" />;
  if (q.isError) return <EmptyState compact icon={Wind} title="Pace vs spin" why="The pace/spin split didn’t load. Reload to try again." />;
  return <PaceSpinView data={q.data} recentFrom={recentFrom} />;
}

/* ---------------- Dew ---------------- */

function DewRow({ label, s }: { label: string; s: DewSeason }) {
  const hi = s.high_dew;
  const lo = s.low_dew;
  return (
    <tr className="border-t border-border">
      <th scope="row" className="h-10 text-left font-medium">{label}</th>
      <td className="text-right">
        {fmtInt(s.high_dew_matches)}
        <span className="text-muted-foreground">/{fmtInt(s.with_weather)}</span>
      </td>
      <td className="text-right font-semibold">
        {fmtPct(hi.chase_win_pct)} <span className="text-[11px] font-normal text-muted-foreground">n={hi.matches}</span>
      </td>
      <td className="text-right">
        {fmtPct(lo.chase_win_pct)} <span className="text-[11px] text-muted-foreground">n={lo.matches}</span>
      </td>
    </tr>
  );
}

export function DewView({ data, recentFrom }: { data: DewReport; recentFrom: number }) {
  const r = data.recent;
  const t = data.total;
  if (t.with_weather === 0) {
    return <EmptyState compact icon={Droplets} title="Dew factor" why="No evening matches here have weather data yet." when="Once the weather backfill reaches this ground." />;
  }
  const diff = isNum(t.high_dew.chase_win_pct) && isNum(t.low_dew.chase_win_pct) ? t.high_dew.chase_win_pct - t.low_dew.chase_win_pct : null;
  return (
    <Panel id="dew" title="Dew factor" aside={<span>evening games · 2nd-innings dew point</span>}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="font-condensed num text-[1.75rem] leading-8 font-bold">{fmtPct(t.with_weather ? (t.high_dew_matches / t.with_weather) * 100 : null)}</span>
        <span className="text-sm text-muted-foreground">of evenings were high-dew (spread ≤ {data.high_dew_spread_c}°C)</span>
        <ConfidenceBadge n={t.high_dew.matches} thresholds={VENUE_THRESHOLDS} />
      </div>
      <table className="num w-full text-[13px]">
        <caption className="sr-only">Chase win percentage on high-dew vs low-dew evenings</caption>
        <thead>
          <tr className="text-overline text-muted-foreground">
            <th scope="col" className="h-8 text-left font-semibold">Window</th>
            <th scope="col" className="text-right font-semibold">High-dew</th>
            <th scope="col" className="text-right font-semibold">Chase won, dew</th>
            <th scope="col" className="text-right font-semibold">No dew</th>
          </tr>
        </thead>
        <tbody>
          <DewRow label={`${recentFrom}+`} s={r} />
          <DewRow label="All-time" s={t} />
        </tbody>
      </table>
      <p className="mt-2 text-xs text-muted-foreground">
        {diff === null
          ? "Not enough dew and no-dew evenings to compare."
          : Math.abs(diff) < 5
            ? `Dew barely moves the chase here (${diff > 0 ? "+" : ""}${Math.round(diff)} pts).`
            : `Chasing sides win ${Math.abs(Math.round(diff))} pts ${diff > 0 ? "more" : "less"} often on high-dew evenings.`}{" "}
        Avg spread {fmtRate(t.avg_spread)}°C, humidity {fmtPct(t.avg_humidity)}.
      </p>
      <p className="mt-1 text-[11px] leading-4 text-muted-foreground">Spread = temperature − dew point at start + 2.5 h (Open-Meteo). Small spreads mean a wet outfield and ball.</p>
    </Panel>
  );
}

export function DewSection({ venueId, recentFrom }: { venueId: number; recentFrom: number }) {
  const q = useDew(venueId);
  if (q.isPending) return <Loading />;
  if (q.isError) return <EmptyState compact icon={Droplets} title="Dew factor" why="The dew report didn’t load. Reload to try again." />;
  return <DewView data={q.data} recentFrom={recentFrom} />;
}
