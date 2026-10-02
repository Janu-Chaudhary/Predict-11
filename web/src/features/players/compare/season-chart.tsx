"use client";

import { ChartLine } from "lucide-react";
import { useState } from "react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import { isolatedPoints } from "@/components/charts/stat-charts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

import { Segmented } from "../../fantasy/ui";
import type { PlayerFantasy } from "../../fantasy/types";
import type { PlayerProfile } from "../types";
import { pcVar } from "./colours";
import { ACCENT, SectionCard } from "./compare-ui";

export type SeasonMetric = "runs" | "wickets" | "fantasy";

const METRICS: { key: SeasonMetric; label: string; long: string }[] = [
  { key: "runs", label: "Runs", long: "runs" },
  { key: "wickets", label: "Wickets", long: "wickets" },
  { key: "fantasy", label: "Fantasy pts / match", long: "mean fantasy points per match" },
];

type Row = { season: number } & Record<string, number | null>;

/**
 * One row per season any player appeared in; `p<i>` is that player's runs / wickets / mean fantasy
 * points, or null when they did not play (a gap, not a zero).
 */
export function seasonRows(profiles: PlayerProfile[], fantasies: (PlayerFantasy | null | undefined)[], metric: SeasonMetric): Row[] {
  const seasons = new Set<number>();
  if (metric === "fantasy") fantasies.forEach((f) => f?.by_season.forEach((s) => seasons.add(s.season)));
  else profiles.forEach((p) => p.by_season.forEach((s) => seasons.add(s.season)));
  return [...seasons]
    .sort((a, b) => a - b)
    .map((season) => {
      const row: Row = { season };
      profiles.forEach((p, i) => {
        if (metric === "fantasy") {
          const s = fantasies[i]?.by_season.find((x) => x.season === season);
          row[`p${i}`] = s?.mean ?? null;
        } else {
          const s = p.by_season.find((x) => x.season === season);
          row[`p${i}`] = s ? (metric === "runs" ? s.batting.runs : s.bowling.wickets) : null;
        }
      });
      return row;
    });
}

export function SeasonChart({
  profiles,
  fantasies,
  names,
  className,
}: {
  profiles: PlayerProfile[];
  fantasies: (PlayerFantasy | null | undefined)[];
  names: string[];
  className?: string;
}) {
  const [metric, setMetric] = useState<SeasonMetric>(() => (profiles.every((p) => p.bowling.balls > p.batting.balls) ? "wickets" : "runs"));
  const animate = !useReducedMotion();
  const data = seasonRows(profiles, fantasies, metric);
  const m = METRICS.find((x) => x.key === metric)!;
  const config = Object.fromEntries(profiles.map((_, i) => [`p${i}`, { label: names[i], color: pcVar(i) }])) satisfies ChartConfig;
  const summary = `${m.label} by season: ${profiles
    .map((_, i) => `${names[i]} ${data.filter((r) => r[`p${i}`] !== null).map((r) => `${r.season} ${Math.round((r[`p${i}`] as number) * 10) / 10}`).join(", ") || "no seasons"}`)
    .join("; ")}.`;
  return (
    <SectionCard
      id="seasons"
      title="Season by season"
      subtitle={`IPL ${m.long} per season, gaps where a player did not play`}
      icon={<ChartLine />}
      accent={ACCENT.bowling}
      className={className}
      aside={<Segmented label="Season metric" options={METRICS.map((x) => ({ key: x.key, label: x.key === "fantasy" ? "Fantasy" : x.label }))} value={metric} onChange={setMetric} />}
    >
      <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {names.map((n, i) => (
          <li key={n} className="inline-flex items-center gap-1.5">
            <svg aria-hidden width="18" height="8">
              <line x1="1" x2="17" y1="4" y2="4" stroke={pcVar(i)} strokeWidth="2.5" strokeLinecap="round" />
            </svg>
            {n}
          </li>
        ))}
      </ul>
      {data.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">No seasons in this scope.</p>
      ) : (
        <figure role="figure" aria-label={summary} className="m-0">
          <ChartContainer config={config} className="aspect-auto h-64 w-full min-w-0 md:h-72">
            <LineChart data={data} margin={{ top: 8, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="season" tickLine={false} axisLine={false} fontSize={11} interval="preserveStartEnd" minTickGap={12} />
              <YAxis tickLine={false} axisLine={false} fontSize={11} width={40} allowDecimals={metric === "fantasy"} />
              <ChartTooltip cursor={{ stroke: "var(--border)" }} content={<ChartTooltipContent indicator="line" />} />
              {profiles.map((p, i) => {
                const key = `p${i}`;
                const lone = isolatedPoints(data, key);
                return (
                  <Line
                    key={p.id}
                    dataKey={key}
                    name={names[i]}
                    type="monotone"
                    stroke={pcVar(i)}
                    strokeWidth={2.25}
                    dot={(d: { cx?: number; cy?: number; index?: number }) =>
                      d.index !== undefined && lone.has(d.index) && d.cx != null && d.cy != null ? (
                        <circle key={`dot-${key}-${d.index}`} cx={d.cx} cy={d.cy} r={3.5} fill={pcVar(i)} />
                      ) : (
                        <g key={`dot-${key}-${d.index}`} />
                      )
                    }
                    activeDot={{ r: 4, stroke: "var(--card)", strokeWidth: 2 }}
                    isAnimationActive={animate}
                    animationDuration={600}
                  />
                );
              })}
            </LineChart>
          </ChartContainer>
          <figcaption className="sr-only">{summary}</figcaption>
        </figure>
      )}
    </SectionCard>
  );
}
