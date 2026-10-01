"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { ChartFrame, SeriesLegend } from "@/components/charts/chart-frame";
import { TeamBadge } from "@/components/player/team-badge";
import { cn } from "@/lib/utils";

import { fmtDate, fmtInt, fmtPct, fmtRate, fmtRuns, isNum, PHASE_LABEL, PHASE_OVERS } from "./format";
import { teamCode } from "./team-code";
import type { ParStats, PhaseRate, TeamTotal, TossStats, VenueLeader } from "./types";

/** Card shell used by every venue section: overline heading + body. Flat, token surfaces only. */
export function Panel({
  title,
  id,
  aside,
  children,
  className,
}: {
  title: ReactNode;
  id: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section aria-labelledby={id} className={cn("min-w-0 rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4", className)}>
      <header className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 id={id} className="text-overline text-muted-foreground">
          {title}
        </h2>
        {aside && <div className="text-xs text-muted-foreground">{aside}</div>}
      </header>
      {children}
    </section>
  );
}

/* ------------------------------------------------------------------ par: 2023+ vs all-time */

type ParRow = { key: string; label: string; recent: string; allTime: string; delta?: number | null; unit?: "runs" | "pts" };

function parRows(recent: ParStats, allTime: ParStats): ParRow[] {
  // Difference of the displayed (rounded) values, so 197 vs 173 reads +24, never +23.
  const d = (a: number | null, b: number | null) => (isNum(a) && isNum(b) ? Math.round(a) - Math.round(b) : null);
  return [
    { key: "avg1", label: "Par 1st innings (avg)", recent: fmtRuns(recent.avg_first_innings), allTime: fmtRuns(allTime.avg_first_innings), delta: d(recent.avg_first_innings, allTime.avg_first_innings), unit: "runs" },
    { key: "med1", label: "Median 1st innings", recent: fmtRuns(recent.median_first_innings), allTime: fmtRuns(allTime.median_first_innings), delta: d(recent.median_first_innings, allTime.median_first_innings), unit: "runs" },
    { key: "avg2", label: "Avg 2nd innings", recent: fmtRuns(recent.avg_second_innings), allTime: fmtRuns(allTime.avg_second_innings), delta: d(recent.avg_second_innings, allTime.avg_second_innings), unit: "runs" },
    { key: "chase", label: "Chasing side won", recent: fmtPct(recent.chase_win_pct), allTime: fmtPct(allTime.chase_win_pct), delta: d(recent.chase_win_pct, allTime.chase_win_pct), unit: "pts" },
    { key: "bat1", label: "Batting first won", recent: fmtPct(recent.bat_first_win_pct), allTime: fmtPct(allTime.bat_first_win_pct), delta: d(recent.bat_first_win_pct, allTime.bat_first_win_pct), unit: "pts" },
  ];
}

function Delta({ value, unit }: { value: number | null | undefined; unit?: string }) {
  if (!isNum(value)) return <span className="text-faint">–</span>;
  if (value === 0) return <span className="text-muted-foreground">0</span>;
  const up = value > 0;
  return (
    <span className="text-muted-foreground" aria-label={`${up ? "up" : "down"} ${Math.abs(value)} ${unit ?? ""}`.trim()}>
      <span aria-hidden>{up ? "▲" : "▼"} </span>
      {up ? "+" : "−"}
      {Math.abs(value)}
    </span>
  );
}

export function ParComparison({ recent, allTime, recentFrom, weighted }: { recent: ParStats; allTime: ParStats; recentFrom: number; weighted: number | null }) {
  const rows = parRows(recent, allTime);
  return (
    <div>
      <div className="-mx-3 overflow-x-auto md:-mx-4">
        <table className="num w-full min-w-[19rem] border-separate border-spacing-0 text-[13px] leading-[18px] md:text-sm md:leading-5">
          <caption className="sr-only">
            Par scores and results at this venue, {recentFrom} onwards compared with all-time
          </caption>
          <thead>
            <tr className="text-overline text-muted-foreground">
              <th scope="col" className="h-9 border-b border-border px-3 text-left md:px-4">
                <span className="sr-only">Measure</span>
              </th>
              <th scope="col" className="h-9 border-b border-border px-3 text-right">
                <span className="text-foreground">{recentFrom}+</span>
                <span className="block text-[11px] font-medium tracking-normal normal-case">n={recent.matches}</span>
              </th>
              <th scope="col" className="h-9 border-b border-border px-3 text-right">
                All-time
                <span className="block text-[11px] font-medium tracking-normal normal-case">n={allTime.matches}</span>
              </th>
              <th scope="col" className="h-9 border-b border-border px-3 text-right md:pr-4">
                Change
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.key}>
                <th scope="row" className={cn("h-9 border-b border-border px-3 text-left font-normal text-muted-foreground md:px-4", i === rows.length - 1 && "border-b-0")}>
                  {r.label}
                </th>
                <td className={cn("border-b border-border px-3 text-right", i === 0 ? "text-base font-semibold" : "font-medium", i === rows.length - 1 && "border-b-0")}>{r.recent}</td>
                <td className={cn("border-b border-border px-3 text-right text-muted-foreground", i === rows.length - 1 && "border-b-0")}>{r.allTime}</td>
                <td className={cn("border-b border-border px-3 text-right text-xs md:pr-4", i === rows.length - 1 && "border-b-0")}>
                  <Delta value={r.delta} unit={r.unit} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 rounded-lg border border-warning/30 bg-warning/8 px-3 py-2 text-xs leading-5 text-foreground">
        <span className="font-semibold">Scoring has inflated since 2022.</span> League powerplay run rate went 7.8 (2022) → 10.1 (2026) with the impact-player rule, so
        all-time averages understate today&rsquo;s par. Plan with the {recentFrom}+ column
        {isNum(weighted) && (
          <>
            {" "}
            or the recency-weighted par of <span className="num font-semibold">{fmtRuns(weighted)}</span>
          </>
        )}
        .
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ toss */

/** Field vs bat split as a single 100% bar with both shares printed (colour is never the only cue). */
export function TossSplitBar({ label, toss }: { label: string; toss: TossStats }) {
  const field = toss.matches ? (toss.chose_field / toss.matches) * 100 : 0;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
        <span className="font-medium text-foreground">{label}</span>
        <span className="num text-muted-foreground">n={toss.matches}</span>
      </div>
      <div
        role="img"
        aria-label={`${label}: toss winners chose to field ${toss.chose_field} times and bat ${toss.chose_bat} times out of ${toss.matches}`}
        className="flex h-6 overflow-hidden rounded-md bg-surface-3"
      >
        <div className="flex items-center bg-chart-3/80 pl-2 text-[11px] font-semibold text-background" style={{ width: `${field}%` }}>
          {field >= 18 && `Field ${Math.round(field)}%`}
        </div>
        <div className="flex flex-1 items-center justify-end pr-2 text-[11px] font-semibold text-foreground">{100 - field >= 14 && `Bat ${Math.round(100 - field)}%`}</div>
      </div>
      <div className="num mt-1 flex justify-between text-[11px] text-muted-foreground">
        <span>{toss.chose_field} field</span>
        <span>{toss.chose_bat} bat</span>
      </div>
    </div>
  );
}

export function TossOutcome({ toss, recentFrom }: { toss: TossStats; recentFrom: number }) {
  const cells: [string, number | null, string][] = [
    ["Toss winner won", toss.toss_winner_win_pct, `all ${toss.matches} tosses`],
    ["…after fielding", toss.toss_winner_win_pct_when_field, `${toss.chose_field} times`],
    ["…after batting", toss.toss_winner_win_pct_when_bat, `${toss.chose_bat} times`],
  ];
  return (
    <dl className="grid grid-cols-3 gap-2" aria-label={`Toss outcomes since ${recentFrom}`}>
      {cells.map(([label, v, hint]) => (
        <div key={label} className="min-w-0 rounded-lg bg-surface-2 p-2">
          <dt className="truncate text-[11px] leading-4 text-muted-foreground">{label}</dt>
          <dd className="font-condensed num text-xl leading-7 font-bold">{fmtPct(v)}</dd>
          <dd className="num truncate text-[11px] leading-4 text-muted-foreground">{hint}</dd>
        </div>
      ))}
    </dl>
  );
}

/* ------------------------------------------------------------------ phases */

const PHASE_ORDER = ["powerplay", "middle", "death"];

export function PhaseBars({ recent, allTime, recentFrom }: { recent: PhaseRate[]; allTime: PhaseRate[]; recentFrom: number }) {
  const byPhase = PHASE_ORDER.map((p) => ({
    phase: p,
    recent: recent.find((r) => r.phase === p),
    allTime: allTime.find((r) => r.phase === p),
  }));
  const max = Math.max(12, ...byPhase.flatMap((p) => [p.recent?.run_rate ?? 0, p.allTime?.run_rate ?? 0]));
  const summary = byPhase
    .map((p) => `${PHASE_LABEL[p.phase]} ${fmtRate(p.recent?.run_rate, 2)} runs per over since ${recentFrom} vs ${fmtRate(p.allTime?.run_rate, 2)} all-time`)
    .join("; ");
  return (
    <ChartFrame
      title="Phase run rates"
      summary={`Run rate by phase at this venue. ${summary}.`}
      legend={
        <SeriesLegend
          items={[
            { label: `${recentFrom}+`, color: "var(--chart-1)" },
            { label: "All-time", color: "var(--faint)", dashed: true },
          ]}
        />
      }
      table={{
        columns: ["Phase", `RR ${recentFrom}+`, "RR all-time", `Wkts/inns ${recentFrom}+`, "Wkts/inns all-time"],
        rows: byPhase.map((p) => [
          PHASE_LABEL[p.phase] ?? p.phase,
          fmtRate(p.recent?.run_rate, 2),
          fmtRate(p.allTime?.run_rate, 2),
          fmtRate(p.recent?.wickets_per_innings, 2),
          fmtRate(p.allTime?.wickets_per_innings, 2),
        ]),
      }}
    >
      <ul className="grid gap-4">
        {byPhase.map((p) => (
          <li key={p.phase}>
            <div className="mb-1.5 flex items-baseline justify-between gap-2">
              <span className="text-sm font-medium">
                {PHASE_LABEL[p.phase] ?? p.phase} <span className="text-xs font-normal text-muted-foreground">{PHASE_OVERS[p.phase]}</span>
              </span>
              <span className="num text-xs text-muted-foreground">{fmtRate(p.recent?.wickets_per_innings)} wkts/inns</span>
            </div>
            <div className="grid gap-1">
              <Bar value={p.recent?.run_rate ?? null} max={max} tone="recent" label={`${recentFrom}+`} />
              <Bar value={p.allTime?.run_rate ?? null} max={max} tone="all" label="All-time" />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[11px] leading-4 text-muted-foreground">Runs per over, extras included, per 6 legal balls.</p>
    </ChartFrame>
  );
}

function Bar({ value, max, tone, label }: { value: number | null; max: number; tone: "recent" | "all"; label: string }) {
  const w = isNum(value) ? Math.max(2, (value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="w-14 shrink-0 text-[11px] text-muted-foreground">{label}</span>
      <div className="h-3 flex-1 overflow-hidden rounded-r bg-surface-2">
        <div
          className={cn("h-full rounded-r", tone === "recent" ? "bg-chart-1" : "border border-dashed border-faint bg-transparent")}
          style={{ width: `${w}%` }}
        />
      </div>
      <span className={cn("num w-10 shrink-0 text-right text-sm", tone === "recent" ? "font-semibold" : "text-muted-foreground")}>{fmtRate(value, 2)}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ totals */

export function TotalsList({ totals, kind }: { totals: TeamTotal[]; kind: "highest" | "lowest" }) {
  if (totals.length === 0) return <p className="text-sm text-muted-foreground">No completed innings recorded here.</p>;
  return (
    <ol className="-mx-3 md:-mx-4">
      {totals.map((t, i) => {
        const code = teamCode(t.team);
        const opp = teamCode(t.opponent);
        return (
          <li key={`${t.match_id}-${t.innings}`} className="flex min-h-[52px] items-center gap-3 border-b border-border px-3 last:border-b-0 md:px-4">
            <span className="num w-4 shrink-0 text-xs text-muted-foreground">{i + 1}</span>
            {code ? <TeamBadge team={code} /> : <span className="w-9" />}
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">
                {t.team ?? "Unknown"}
                {opp && <span className="font-normal text-muted-foreground"> v {opp}</span>}
              </div>
              <div className="num truncate text-xs text-muted-foreground">
                {fmtDate(t.date)} · {t.innings === 1 ? "1st" : "2nd"} innings
              </div>
            </div>
            <div className="shrink-0 text-right">
              <div className={cn("font-condensed num text-lg leading-6 font-bold", kind === "highest" && i === 0 && "text-foreground")}>
                {t.wickets >= 10 ? t.runs : `${t.runs}/${t.wickets}`}
              </div>
              <div className="num text-[11px] leading-4 text-muted-foreground">{t.overs} ov</div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/* ------------------------------------------------------------------ leaders */

export function LeaderList({ leaders, kind }: { leaders: VenueLeader[]; kind: "runs" | "wickets" }) {
  if (leaders.length === 0) return <p className="text-sm text-muted-foreground">No {kind} recorded at this ground yet.</p>;
  const rateLabel = kind === "runs" ? "SR" : "Econ";
  return (
    <ol className="-mx-3 md:-mx-4">
      {leaders.map((l, i) => (
        <li key={l.player.id} className="border-b border-border last:border-b-0">
          <Link
            href={`/players/${encodeURIComponent(l.player.id)}`}
            className="flex min-h-[52px] items-center gap-3 px-3 outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset md:px-4"
          >
            <span className="num w-4 shrink-0 text-xs text-muted-foreground">{i + 1}</span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{l.player.name}</div>
              <div className="num truncate text-xs text-muted-foreground">
                {fmtInt(l.innings)} inns · {rateLabel} {fmtRate(l.rate, kind === "runs" ? 1 : 2)}
              </div>
            </div>
            <div className="w-16 shrink-0 text-right">
              <div className="num text-sm font-semibold">{fmtInt(l.value)}</div>
              <div className="text-[11px] leading-4 text-muted-foreground">{kind}</div>
            </div>
          </Link>
        </li>
      ))}
    </ol>
  );
}

/* ------------------------------------------------------------------ par by season */

/**
 * Average 1st-innings score per season as plain HTML columns (value printed on each bar).
 * Local because the shared StatLineChart renders no SVG inside this layout (zero-width
 * ResponsiveContainer); swap back once that is fixed.
 */
export function SeasonParBars({ seasons, venueName, recentFrom }: { seasons: { season: number; matches: number; avg_first_innings: number | null }[]; venueName: string; recentFrom: number }) {
  const vals = seasons.map((s) => s.avg_first_innings).filter(isNum);
  const max = Math.max(1, ...vals);
  const min = Math.min(max, ...vals);
  const floor = Math.max(0, Math.floor((min - 30) / 10) * 10);
  return (
    <ChartFrame
      title="Average 1st-innings score by season"
      summary={`Average first-innings total per IPL season at ${venueName}. ${seasons.map((s) => `${s.season}: ${fmtRuns(s.avg_first_innings)}`).join(", ")}.`}
      table={{ columns: ["Season", "Matches", "Avg 1st inns"], rows: seasons.map((s) => [String(s.season), s.matches, fmtRuns(s.avg_first_innings)]) }}
    >
      <div className="flex h-48 items-end gap-0.5 sm:gap-1">
        {seasons.map((s) => {
          const v = s.avg_first_innings;
          const h = isNum(v) ? Math.max(4, ((v - floor) / (max - floor)) * 100) : 0;
          const recent = s.season >= recentFrom;
          return (
            <div key={s.season} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end">
              <span className="num mb-0.5 text-[10px] leading-3 text-muted-foreground max-sm:hidden">{isNum(v) ? Math.round(v) : ""}</span>
              <div className={cn("w-full rounded-t", recent ? "bg-chart-1" : "bg-chart-1/40")} style={{ height: `${h}%` }} title={`${s.season}: ${fmtRuns(v)} (${s.matches} matches)`} />
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex gap-0.5 sm:gap-1">
        {seasons.map((s, i) => (
          <span key={s.season} className="num min-w-0 flex-1 text-center text-[10px] leading-3 text-faint">
            {i % 2 === 0 || seasons.length < 10 ? `'${String(s.season).slice(2)}` : ""}
          </span>
        ))}
      </div>
      <p className="mt-2 text-[11px] leading-4 text-muted-foreground">
        Solid bars: {recentFrom}+ (impact-player era). Axis starts at {floor}.
      </p>
    </ChartFrame>
  );
}
