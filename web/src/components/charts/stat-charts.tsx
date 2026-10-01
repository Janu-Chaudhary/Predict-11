"use client";

import { Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";

import { useReducedMotion } from "@/hooks/use-reduced-motion";

import { ChartFrame, SeriesLegend } from "./chart-frame";

export type Series = {
  key: string;
  label: string;
  /** CSS colour; defaults to the chart-N token in fixed order (never cycled). */
  color?: string;
  dashed?: boolean;
};

const FIXED = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

function toConfig(series: Series[]): ChartConfig {
  if (series.length > FIXED.length && series.some((s) => !s.color)) {
    throw new Error("More than 5 un-coloured series: fold extras into 'Other' or use small multiples.");
  }
  return Object.fromEntries(series.map((s, i) => [s.key, { label: s.label, color: seriesColor(s, i) }]));
}

/**
 * The series colour itself, not `var(--color-<key>)`: a data key with a dot, space or other
 * character that is not valid in a CSS custom-property name ("avg.first", "1st inns") made that
 * var invalid, so the line was drawn with `stroke: none` and the chart looked empty.
 */
export function seriesColor(s: Series, i: number): string {
  return s.color ?? FIXED[i];
}

type Row = Record<string, string | number | null>;

const isValue = (v: unknown) => v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v));

/**
 * Indexes of points with no plotted neighbour on either side. With `dot={false}` such a point
 * draws nothing (a line needs two points), so a sparse series — one season, or seasons split by
 * nulls such as a venue unused in 2020 — rendered an empty chart. These get a dot.
 */
export function isolatedPoints(data: Row[], key: string): Set<number> {
  const out = new Set<number>();
  data.forEach((r, i) => {
    if (isValue(r[key]) && !isValue(data[i - 1]?.[key]) && !isValue(data[i + 1]?.[key])) out.add(i);
  });
  return out;
}

function tableOf(data: Row[], xKey: string, series: Series[]) {
  return { columns: [xKey, ...series.map((s) => s.label)], rows: data.map((r) => [String(r[xKey] ?? ""), ...series.map((s) => (r[s.key] ?? "–") as string | number)]) };
}

/** Generic bar chart (season totals, splits). Rounded 4 px data ends, 2 px gaps, horizontal grid only. */
export function StatBarChart({
  title,
  summary,
  data,
  xKey,
  series,
  height = 224,
  layout = "vertical-bars",
}: {
  title: string;
  summary: string;
  data: Row[];
  xKey: string;
  series: Series[];
  height?: number;
  layout?: "vertical-bars" | "horizontal-bars";
}) {
  const animate = !useReducedMotion();
  const config = toConfig(series);
  const horizontal = layout === "horizontal-bars";
  return (
    <ChartFrame
      title={title}
      summary={summary}
      table={tableOf(data, xKey, series)}
      legend={series.length > 1 ? <SeriesLegend items={series.map((s, i) => ({ label: s.label, color: s.color ?? FIXED[i] }))} /> : undefined}
    >
      <ChartContainer config={config} className="aspect-auto w-full min-w-0" style={{ height }}>
        <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2}>
          <CartesianGrid vertical={horizontal} horizontal={!horizontal} stroke="var(--border)" />
          {horizontal ? (
            <>
              <XAxis type="number" tickLine={false} axisLine={false} fontSize={11} />
              <YAxis type="category" dataKey={xKey} tickLine={false} axisLine={false} fontSize={11} width={72} />
            </>
          ) : (
            <>
              <XAxis dataKey={xKey} tickLine={false} axisLine={false} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} fontSize={11} width={36} />
            </>
          )}
          <ChartTooltip cursor={{ fill: "var(--surface-2)" }} content={<ChartTooltipContent />} />
          {series.map((s, i) => (
            <Bar key={s.key} dataKey={s.key} fill={seriesColor(s, i)} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} isAnimationActive={animate}
            animationDuration={600} />
          ))}
        </BarChart>
      </ChartContainer>
    </ChartFrame>
  );
}

/** Generic line chart (trends over matches/seasons). 2 px lines, dashed series for shape cues. */
export function StatLineChart({
  title,
  summary,
  data,
  xKey,
  series,
  height = 224,
}: {
  title: string;
  summary: string;
  data: Row[];
  xKey: string;
  series: Series[];
  height?: number;
}) {
  const animate = !useReducedMotion();
  const config = toConfig(series);
  return (
    <ChartFrame
      title={title}
      summary={summary}
      table={tableOf(data, xKey, series)}
      legend={series.length > 1 ? <SeriesLegend items={series.map((s, i) => ({ label: s.label, color: s.color ?? FIXED[i], dashed: s.dashed }))} /> : undefined}
    >
      <ChartContainer config={config} className="aspect-auto w-full min-w-0" style={{ height }}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey={xKey} tickLine={false} axisLine={false} fontSize={11} />
          <YAxis tickLine={false} axisLine={false} fontSize={11} width={36} />
          <ChartTooltip cursor={{ stroke: "var(--border)" }} content={<ChartTooltipContent indicator="line" />} />
          {series.map((s, i) => {
            const color = seriesColor(s, i);
            const lone = isolatedPoints(data, s.key);
            return (
            <Line
              key={s.key}
              dataKey={s.key}
              type="monotone"
              stroke={color}
              strokeWidth={2}
              strokeDasharray={s.dashed ? "6 4" : undefined}
              dot={(p: { cx?: number; cy?: number; index?: number }) =>
                p.index !== undefined && lone.has(p.index) && p.cx != null && p.cy != null ? (
                  <circle key={`dot-${s.key}-${p.index}`} data-isolated cx={p.cx} cy={p.cy} r={3} fill={color} />
                ) : (
                  <g key={`dot-${s.key}-${p.index}`} />
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
    </ChartFrame>
  );
}
