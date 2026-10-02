"use client";

import { Radar as RadarIcon } from "lucide-react";
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart } from "recharts";

import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

import { fmt } from "../format";
import type { StatFilter } from "../types";
import { QueryError } from "../ui";
import { pcVar } from "./colours";
import { ACCENT, SectionCard } from "./compare-ui";
import { usePercentiles, type PercentilesResponse } from "./data";

/** Short spoke labels for the radar (full labels live in the table below it). */
const SPOKE: Record<string, string> = {
  runs_per_inns: "Run volume",
  strike_rate: "Strike rate",
  average: "Average",
  wickets_per_inns: "Wickets",
  economy: "Economy",
  fielding_per_match: "Fielding",
  fantasy_mean: "Fantasy",
};

const VALUE_DIGITS: Record<string, number> = { runs_per_inns: 1, strike_rate: 1, average: 1, wickets_per_inns: 2, economy: 2, fielding_per_match: 2, fantasy_mean: 1 };

export type RadarRow = { axis: string; key: string } & Record<string, number | string | null>;

/** One row per axis with `p0..pN` percentiles (null = not ranked), in the API's axis order. */
export function radarRows(data: PercentilesResponse, ids: string[]): RadarRow[] {
  return data.axes.map((a) => {
    const row: RadarRow = { axis: SPOKE[a.key] ?? a.label, key: a.key };
    ids.forEach((id, i) => {
      const p = data.players.find((x) => x.id === id)?.axes.find((x) => x.key === a.key);
      row[`p${i}`] = p?.percentile ?? null;
    });
    return row;
  });
}

/**
 * Skill profile radar: percentile (0–100) on seven axes vs every IPL player with enough sample in
 * the same scope (GET /players/percentiles). Economy is inverted server-side so outward = better.
 * Unranked axes (sample too small) are skipped by the polygon and printed as "–" in the table.
 */
export function SkillRadar({ ids, names, filter, className }: { ids: string[]; names: string[]; filter: StatFilter; className?: string }) {
  const q = usePercentiles(ids, filter);
  const animate = !useReducedMotion();
  return (
    <SectionCard
      id="radar"
      title="Skill profile"
      subtitle="Percentile vs all IPL players with enough sample, same scope"
      icon={<RadarIcon />}
      accent={ACCENT.overview}
      className={className}
    >
      {q.isPending ? (
        <div role="status" aria-label="Loading percentiles" className="grid gap-3 md:grid-cols-[1fr_16rem]">
          <Skeleton className="aspect-square max-h-80 w-full rounded-full" />
          <Skeleton className="h-56" />
        </div>
      ) : q.isError ? (
        <QueryError error={q.error} onRetry={() => q.refetch()} what="the skill percentiles" />
      ) : (
        <RadarBody data={q.data} ids={ids} names={names} animate={animate} stale={q.isPlaceholderData} />
      )}
    </SectionCard>
  );
}

function RadarBody({ data, ids, names, animate, stale }: { data: PercentilesResponse; ids: string[]; names: string[]; animate: boolean; stale: boolean }) {
  const rows = radarRows(data, ids);
  const config = Object.fromEntries(ids.map((_, i) => [`p${i}`, { label: names[i], color: pcVar(i) }])) satisfies ChartConfig;
  const summary = `Skill percentiles: ${ids
    .map((_, i) => `${names[i]} ${rows.map((r) => `${r.axis} ${r[`p${i}`] ?? "unranked"}`).join(", ")}`)
    .join("; ")}.`;
  const valueOf = (id: string, key: string) => data.players.find((x) => x.id === id)?.axes.find((x) => x.key === key)?.value ?? null;
  return (
    <div className={cn("grid items-center gap-4 transition-opacity lg:grid-cols-[minmax(0,1fr)_minmax(15rem,20rem)]", stale && "opacity-60")}>
      <figure role="figure" aria-label={summary} className="m-0 min-w-0">
        <ChartContainer config={config} className="mx-auto aspect-square max-h-[22rem] w-full">
          <RadarChart data={rows} outerRadius="64%" margin={{ top: 8, right: 32, bottom: 8, left: 32 }}>
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} />
            <PolarRadiusAxis domain={[0, 100]} tickCount={5} tick={false} axisLine={false} />
            <ChartTooltip content={<ChartTooltipContent indicator="line" />} />
            {ids.map((id, i) => (
              <Radar
                key={id}
                name={names[i]}
                dataKey={`p${i}`}
                stroke={pcVar(i)}
                strokeWidth={2}
                fill={pcVar(i)}
                fillOpacity={ids.length > 2 ? 0.1 : 0.16}
                connectNulls
                dot={{ r: 2.5, fill: pcVar(i), strokeWidth: 0 }}
                isAnimationActive={animate}
                animationDuration={600}
              />
            ))}
          </RadarChart>
        </ChartContainer>
        <figcaption className="sr-only">{summary}</figcaption>
      </figure>
      <div className="min-w-0">
        <table className="num w-full text-[13px]">
          <caption className="sr-only">Percentile (and raw value) per skill axis</caption>
          <thead>
            <tr>
              <th scope="col" className="text-overline pb-1.5 text-left font-normal text-muted-foreground">
                Percentile
              </th>
              {ids.map((id, i) => (
                <th key={id} scope="col" className="pb-1.5 text-right text-[11px] font-semibold" style={{ color: pcVar(i) }}>
                  {names[i]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {data.axes.map((a) => {
              const ps = rows.find((r) => r.key === a.key)!;
              const vals = ids.map((_, i) => ps[`p${i}`] as number | null);
              const ranked = vals.filter((v): v is number => v !== null);
              const top = ranked.length >= 2 ? Math.max(...ranked) : null;
              return (
                <tr key={a.key}>
                  <th scope="row" className="py-1.5 pr-2 text-left font-normal text-muted-foreground" title={`${a.label} · ranked among ${a.population} players (${a.sample})`}>
                    {SPOKE[a.key] ?? a.label}
                    {a.better === "low" && <span className="ml-1 text-[11px] text-faint">(inv.)</span>}
                  </th>
                  {ids.map((id, i) => {
                    const v = vals[i];
                    const lead = top !== null && v === top && ranked.filter((x) => x === top).length === 1;
                    return (
                      <td key={id} className="py-1.5 text-right" title={`raw ${fmt(valueOf(id, a.key), VALUE_DIGITS[a.key] ?? 1)}`}>
                        <span className={lead ? "font-bold" : "text-foreground/80"} style={lead ? { color: pcVar(i) } : undefined}>
                          {v === null ? "–" : fmt(v, 0)}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="mt-2 text-[11px] leading-4 text-muted-foreground">
          50 = median IPL player. Ranked only with enough sample (e.g. ≥ 100 balls faced for strike rate, ≥ 120 balls bowled for economy); “–” = not ranked. Economy is inverted so higher is better.
        </p>
      </div>
    </div>
  );
}
