"use client";

import { useMemo, useState, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

import { fmtNum, fmtValue } from "./format";
import type { Bin, Contribution, Curve, Pair } from "./types";

export const C = {
  model: "var(--chart-1)",
  baseline: "var(--chart-2)",
  best: "var(--chart-4)",
  valid: "var(--chart-3)",
  neg: "var(--chart-5)",
  muted: "var(--faint)",
};

const axis = { tickLine: false, axisLine: false, fontSize: 11 } as const;

// ------------------------------------------------------------------ histogram
export function HistogramChart({
  bins,
  color = C.model,
  height = 220,
  name = "Rows",
  refX,
}: {
  bins: Bin[];
  color?: string;
  height?: number;
  name?: string;
  /** Vertical reference lines at these x values (e.g. 0, the mean). */
  refX?: { x: number; label: string }[];
}) {
  const data = bins.map((b) => ({ x: b.lo, range: `${fmtNum(b.lo, 0)} to ${fmtNum(b.hi, 0)}`, n: b.n }));
  /** Reference values snap to the bin that contains them (category axis). */
  const binOf = (v: number) => (bins.find((b) => v >= b.lo && v < b.hi) ?? bins.at(-1))?.lo ?? 0;
  const config = { n: { label: name, color } } satisfies ChartConfig;
  return (
    <ChartContainer config={config} className="aspect-auto w-full min-w-0" style={{ height }}>
      <BarChart data={data} margin={{ top: 18, right: 8, bottom: 0, left: 0 }} barCategoryGap={1}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey="x" {...axis} interval="preserveStartEnd" minTickGap={16} />
        <YAxis {...axis} width={40} />
        <ChartTooltip cursor={{ fill: "var(--surface-2)" }} content={<ChartTooltipContent labelFormatter={(_, p) => `${p?.[0]?.payload?.range ?? ""} pts`} />} />
        {/* Bars are drawn without the grow-in animation: it left them blank in headless captures. */}
        <Bar dataKey="n" fill={color} radius={[3, 3, 0, 0]} isAnimationActive={false} />
        {refX?.map((r, i) => (
          <ReferenceLine key={r.label} x={binOf(r.x)} stroke="var(--foreground)" strokeOpacity={0.5} strokeDasharray="4 3" label={{ value: r.label, position: i % 2 ? "insideTopRight" : "insideTopLeft", fontSize: 11, fill: "var(--muted-foreground)" }} />
        ))}
      </BarChart>
    </ChartContainer>
  );
}

// ------------------------------------------------------------------ simple bars
export type BarSeries = { key: string; label: string; color: string };

export function BarsChart({
  data,
  xKey,
  series,
  height = 220,
  colorOf,
  yFmt,
  refY,
  layout = "vertical-bars",
  yWidth = 40,
}: {
  data: Record<string, string | number | null>[];
  xKey: string;
  series: BarSeries[];
  height?: number;
  /** Per-row colour for single-series charts. */
  colorOf?: (row: Record<string, string | number | null>) => string;
  yFmt?: (n: number) => string;
  refY?: { y: number; label?: string }[];
  layout?: "vertical-bars" | "horizontal-bars";
  yWidth?: number;
}) {
  const config = Object.fromEntries(series.map((s) => [s.key, { label: s.label, color: s.color }])) satisfies ChartConfig;
  const horizontal = layout === "horizontal-bars";
  return (
    <ChartContainer config={config} className="aspect-auto w-full min-w-0" style={{ height }}>
      <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2}>
        <CartesianGrid vertical={horizontal} horizontal={!horizontal} stroke="var(--border)" />
        {horizontal ? (
          <>
            <XAxis type="number" {...axis} tickFormatter={yFmt} />
            <YAxis type="category" dataKey={xKey} {...axis} width={yWidth} interval={0} />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} {...axis} interval="preserveStartEnd" />
            <YAxis {...axis} width={yWidth} tickFormatter={yFmt} />
          </>
        )}
        {refY?.map((r) => (
          <ReferenceLine key={`${r.y}-${r.label}`} {...(horizontal ? { x: r.y } : { y: r.y })} stroke="var(--foreground)" strokeOpacity={0.45} strokeDasharray="4 3" label={r.label ? { value: r.label, position: "insideTopRight", fontSize: 11, fill: "var(--muted-foreground)" } : undefined} />
        ))}
        <ChartTooltip cursor={{ fill: "var(--surface-2)" }} content={<ChartTooltipContent formatter={yFmt ? (v, n) => <TooltipRow name={String(config[String(n)]?.label ?? n)} value={yFmt(Number(v))} /> : undefined} />} />
        {series.map((s) => (
          <Bar key={s.key} dataKey={s.key} fill={s.color} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} isAnimationActive={false}>
            {colorOf && series.length === 1 && data.map((row, i) => <Cell key={i} fill={colorOf(row)} />)}
          </Bar>
        ))}
      </BarChart>
    </ChartContainer>
  );
}

function TooltipRow({ name, value }: { name: string; value: string }) {
  return (
    <div className="flex w-full items-center justify-between gap-3">
      <span className="text-muted-foreground">{name}</span>
      <span className="num font-medium text-foreground">{value}</span>
    </div>
  );
}

// ------------------------------------------------------------------ lines over an index
export function LinesChart({
  data,
  xKey,
  series,
  height = 260,
  brush = false,
  refX,
  yFmt,
  xLabel,
  yDomain,
}: {
  data: Record<string, string | number | null>[];
  xKey: string;
  series: (BarSeries & { dashed?: boolean; width?: number; opacity?: number })[];
  height?: number;
  brush?: boolean;
  refX?: { x: number | string; label: string }[];
  yFmt?: (n: number) => string;
  xLabel?: (v: string | number) => string;
  yDomain?: [number | "auto" | "dataMin" | "dataMax", number | "auto" | "dataMin" | "dataMax"];
}) {
  const animate = !useReducedMotion();
  const config = Object.fromEntries(series.map((s) => [s.key, { label: s.label, color: s.color }])) satisfies ChartConfig;
  return (
    <ChartContainer config={config} className="aspect-auto w-full min-w-0" style={{ height }}>
      <LineChart data={data} margin={{ top: 16, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey={xKey} {...axis} interval="preserveStartEnd" minTickGap={24} tickFormatter={xLabel} />
        <YAxis {...axis} width={44} tickFormatter={yFmt} domain={yDomain ?? ["auto", "auto"]} />
        <ChartTooltip cursor={{ stroke: "var(--border)" }} content={<ChartTooltipContent indicator="line" labelFormatter={xLabel ? (v) => xLabel(v as string | number) : undefined} />} />
        {refX?.map((r) => (
          <ReferenceLine key={r.label} x={r.x} stroke="var(--foreground)" strokeOpacity={0.55} strokeDasharray="4 3" label={{ value: r.label, position: "insideTopRight", fontSize: 11, fill: "var(--muted-foreground)" }} />
        ))}
        {series.map((s) => (
          <Line
            key={s.key}
            dataKey={s.key}
            type="monotone"
            stroke={s.color}
            strokeWidth={s.width ?? 2}
            strokeOpacity={s.opacity ?? 1}
            strokeDasharray={s.dashed ? "6 4" : undefined}
            dot={false}
            activeDot={{ r: 4, stroke: "var(--card)", strokeWidth: 2 }}
            isAnimationActive={animate}
            connectNulls
          />
        ))}
        {brush && data.length > 20 && <Brush dataKey={xKey} height={22} stroke="var(--brand)" fill="var(--card)" travellerWidth={8} tickFormatter={xLabel} />}
      </LineChart>
    </ChartContainer>
  );
}

/** Downsampled curve index → boosting round. */
export function curveRows(c: Curve): { iter: number; train: number | null; valid: number | null }[] {
  const n = Math.max(c.train.length, c.valid.length);
  const iters = c.iters ?? n;
  return Array.from({ length: n }, (_, i) => ({
    iter: n > 1 ? Math.round(1 + (i * (iters - 1)) / (n - 1)) : 1,
    train: c.train[i] ?? null,
    valid: c.valid[i] ?? null,
  }));
}

// ------------------------------------------------------------------ reliability
export function ReliabilityChart({ bins, height = 280 }: { bins: { predMean: number; actualMean: number; n: number }[]; height?: number }) {
  const max = Math.ceil(Math.max(10, ...bins.flatMap((b) => [b.predMean, b.actualMean])) / 10) * 10;
  const min = Math.min(0, Math.floor(Math.min(...bins.flatMap((b) => [b.predMean, b.actualMean])) / 10) * 10);
  const config = { actualMean: { label: "Actual average", color: C.model } } satisfies ChartConfig;
  return (
    <ChartContainer config={config} className="aspect-auto w-full min-w-0" style={{ height }}>
      <ScatterChart margin={{ top: 12, right: 16, bottom: 16, left: 0 }}>
        <CartesianGrid stroke="var(--border)" />
        <XAxis type="number" dataKey="predMean" name="Predicted" domain={[min, max]} {...axis} label={{ value: "predicted (bin average)", position: "insideBottom", offset: -8, fontSize: 11, fill: "var(--muted-foreground)" }} />
        <YAxis type="number" dataKey="actualMean" name="Actual" domain={[min, max]} {...axis} width={40} />
        <ZAxis type="number" dataKey="n" range={[40, 260]} name="Rows" />
        <ReferenceLine segment={[{ x: min, y: min }, { x: max, y: max }]} stroke="var(--foreground)" strokeOpacity={0.4} strokeDasharray="5 4" ifOverflow="extendDomain" />
        <ChartTooltip
          cursor={false}
          content={({ active, payload }) => {
            const p = payload?.[0]?.payload as { predMean: number; actualMean: number; n: number } | undefined;
            if (!active || !p) return null;
            return (
              <TipBox>
                <TooltipRow name="Predicted" value={fmtNum(p.predMean, 1)} />
                <TooltipRow name="Actual" value={fmtNum(p.actualMean, 1)} />
                <TooltipRow name="Gap" value={fmtNum(p.actualMean - p.predMean, 1)} />
                <TooltipRow name="Rows" value={fmtNum(p.n, 0)} />
              </TipBox>
            );
          }}
        />
        <Scatter data={bins} fill={C.model} fillOpacity={0.85} line={{ stroke: C.model, strokeWidth: 1.5 }} />
      </ScatterChart>
    </ChartContainer>
  );
}

export function TipBox({ children }: { children: ReactNode }) {
  return <div className="grid min-w-36 gap-1 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">{children}</div>;
}

// ------------------------------------------------------------------ dependence
export function DependenceChart({ points, feature, height = 280 }: { points: { x: number | null; shap: number }[]; feature: string; height?: number }) {
  const data = points.filter((p) => p.x !== null) as { x: number; shap: number }[];
  const config = { shap: { label: "SHAP", color: C.model } } satisfies ChartConfig;
  return (
    <ChartContainer config={config} className="aspect-auto w-full min-w-0" style={{ height }}>
      <ScatterChart margin={{ top: 12, right: 16, bottom: 16, left: 0 }}>
        <CartesianGrid stroke="var(--border)" />
        <XAxis type="number" dataKey="x" name={feature} domain={["auto", "auto"]} {...axis} label={{ value: feature, position: "insideBottom", offset: -8, fontSize: 11, fill: "var(--muted-foreground)" }} />
        <YAxis type="number" dataKey="shap" name="SHAP" {...axis} width={40} />
        <ReferenceLine y={0} stroke="var(--foreground)" strokeOpacity={0.4} />
        <ChartTooltip
          cursor={false}
          content={({ active, payload }) => {
            const p = payload?.[0]?.payload as { x: number; shap: number } | undefined;
            if (!active || !p) return null;
            return (
              <TipBox>
                <TooltipRow name={feature} value={fmtValue(p.x)} />
                <TooltipRow name="SHAP (pts)" value={fmtNum(p.shap, 2)} />
              </TipBox>
            );
          }}
        />
        <Scatter data={data} isAnimationActive={false}>
          {data.map((p, i) => (
            <Cell key={i} fill={p.shap >= 0 ? C.model : C.neg} fillOpacity={0.55} />
          ))}
        </Scatter>
      </ScatterChart>
    </ChartContainer>
  );
}

// ------------------------------------------------------------------ horizontal value bars
export type HBarItem = { key: string; label: ReactNode; value: number; sub?: ReactNode; title?: string };

/** Ranked horizontal bars (div based: crisp labels, works at 390 px). Signed values diverge from 0. */
export function HBars({ items, fmt, color = "bg-brand", negColor = "bg-negative", className, onSelect, selected }: { items: HBarItem[]; fmt: (n: number) => string; color?: string; negColor?: string; className?: string; onSelect?: (key: string) => void; selected?: string | null }) {
  const max = Math.max(1e-9, ...items.map((i) => Math.abs(i.value)));
  const signed = items.some((i) => i.value < 0);
  return (
    <ul className={cn("space-y-1", className)}>
      {items.map((it) => {
        const w = (Math.abs(it.value) / max) * (signed ? 50 : 100);
        const left = signed ? (it.value >= 0 ? 50 : 50 - w) : 0;
        const body = (
          <>
            <span className="min-w-0 truncate text-left text-[13px]" title={it.title}>
              {it.label}
              {it.sub && <span className="ml-1.5 text-xs text-muted-foreground">{it.sub}</span>}
            </span>
            <span className="relative h-3 rounded-sm bg-surface-2">
              {signed && <span aria-hidden className="absolute inset-y-[-2px] left-1/2 w-px bg-foreground/40" />}
              <span className={cn("absolute inset-y-0 rounded-sm", it.value >= 0 ? color : negColor)} style={{ left: `${left}%`, width: `${Math.max(0.6, w)}%` }} />
            </span>
            <span className="num text-right text-xs font-medium">{fmt(it.value)}</span>
          </>
        );
        const cls = "grid grid-cols-[minmax(7rem,12rem)_1fr_4rem] items-center gap-2 rounded-md px-1.5 py-1 md:grid-cols-[minmax(9rem,15rem)_1fr_4.5rem]";
        return (
          <li key={it.key}>
            {onSelect ? (
              <button type="button" onClick={() => onSelect(it.key)} aria-pressed={selected === it.key} className={cn(cls, "w-full outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring", selected === it.key && "bg-surface-2")}>
                {body}
              </button>
            ) : (
              <div className={cls}>{body}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

// ------------------------------------------------------------------ correlation heatmap
function corrColor(r: number): string {
  const a = Math.min(1, Math.abs(r));
  return r >= 0 ? `color-mix(in oklch, var(--chart-1) ${Math.round(a * 100)}%, var(--surface-2))` : `color-mix(in oklch, var(--chart-2) ${Math.round(a * 100)}%, var(--surface-2))`;
}

export function Heatmap({ features, matrix }: { features: string[]; matrix: number[][] }) {
  const [hover, setHover] = useState<[number, number] | null>(null);
  const n = features.length;
  const readout = hover ? `${features[hover[0]]} × ${features[hover[1]]}: r = ${fmtNum(matrix[hover[0]][hover[1]], 2)}` : "Hover or tap a cell";
  return (
    <div>
      <p className="num mb-2 h-5 truncate text-xs text-muted-foreground" aria-live="polite">
        {readout}
      </p>
      <div className="overflow-x-auto">
        <div className="grid min-w-[560px] gap-px" style={{ gridTemplateColumns: `9rem repeat(${n}, minmax(14px, 1fr))` }} onMouseLeave={() => setHover(null)}>
          {matrix.map((row, i) => (
            <div key={features[i]} className="contents">
              <div className={cn("truncate pr-2 text-right text-[11px] leading-[18px]", hover?.[0] === i ? "text-foreground" : "text-muted-foreground")} title={features[i]}>
                {features[i]}
              </div>
              {row.map((r, j) => (
                <button
                  key={j}
                  type="button"
                  aria-label={`${features[i]} and ${features[j]}: ${fmtNum(r, 2)}`}
                  onMouseEnter={() => setHover([i, j])}
                  onFocus={() => setHover([i, j])}
                  onClick={() => setHover([i, j])}
                  className={cn("aspect-square min-h-[14px] rounded-[2px] outline-none focus-visible:ring-2 focus-visible:ring-ring", hover && (hover[0] === i || hover[1] === j) && "ring-1 ring-foreground/30")}
                  style={{ background: corrColor(r) }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2 text-[11px] text-muted-foreground">
        <span>−1</span>
        <span className="h-2 w-40 rounded-full" style={{ background: `linear-gradient(90deg, ${corrColor(-1)}, ${corrColor(0)}, ${corrColor(1)})` }} />
        <span>+1</span>
        <span className="ml-2">gold = move in opposite directions · violet = move together</span>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ forest plot
export type ForestRow = { key: string; label: string; pair: Pair; emphasis?: boolean };

/** Difference (model − baseline) with 95% CI per evaluation set, shared axis, zero line. */
export function ForestPlot({ rows, fmt, higherIsBetter }: { rows: ForestRow[]; fmt: (n: number | null) => string; higherIsBetter: boolean }) {
  const vals = rows.flatMap((r) => [r.pair.ci[0], r.pair.ci[1], r.pair.diff]).filter((v): v is number => v !== null);
  const span = Math.max(1e-9, ...vals.map(Math.abs)) * 1.1;
  const x = (n: number) => 50 + (n / span) * 50;
  return (
    <div>
      <div className="mb-1 grid grid-cols-[6.5rem_1fr_5.5rem] gap-2 text-[11px] text-faint md:grid-cols-[8rem_1fr_7rem]">
        <span />
        <span className="flex justify-between">
          <span>← {higherIsBetter ? "baseline better" : "model better"}</span>
          <span>{higherIsBetter ? "model better" : "baseline better"} →</span>
        </span>
        <span className="text-right">Δ (95% CI)</span>
      </div>
      <ul className="space-y-1">
        {rows.map((r) => {
          const [lo, hi] = r.pair.ci;
          const good = r.pair.diff !== null && (higherIsBetter ? r.pair.diff > 0 : r.pair.diff < 0);
          const clear = lo !== null && hi !== null && (lo > 0 || hi < 0);
          const color = !clear ? "bg-muted-foreground" : good ? "bg-positive" : "bg-negative";
          return (
            <li key={r.key} className={cn("grid grid-cols-[6.5rem_1fr_5.5rem] items-center gap-2 rounded-md py-1 md:grid-cols-[8rem_1fr_7rem]", r.emphasis && "bg-surface-2/70")}>
              <span className={cn("truncate pl-1 text-[13px]", r.emphasis && "font-semibold")}>{r.label}</span>
              <span className="relative h-5" role="img" aria-label={`${r.label}: ${fmt(r.pair.diff)} (${fmt(lo)} to ${fmt(hi)})`}>
                <span className="absolute inset-x-0 top-1/2 h-px bg-border" />
                <span className="absolute inset-y-0 left-1/2 w-px bg-foreground/40" />
                {lo !== null && hi !== null && <span className={cn("absolute top-1/2 h-1 -translate-y-1/2 rounded-full opacity-50", color)} style={{ left: `${x(lo)}%`, width: `${Math.max(0.5, x(hi) - x(lo))}%` }} />}
                {r.pair.diff !== null && <span className={cn("absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card", color)} style={{ left: `${x(r.pair.diff)}%` }} />}
              </span>
              <span className="num text-right text-xs">
                <span className="font-medium">{fmt(r.pair.diff)}</span>
                <span className="block text-[10px] text-faint">
                  {fmt(lo)} … {fmt(hi)}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ------------------------------------------------------------------ SHAP waterfall
/** Base value → each contribution (largest first) → prediction. The rest fold into one row. */
export function Waterfall({ base, contribs, top = 12, unit = "pts" }: { base: number; contribs: Contribution[]; top?: number; unit?: string }) {
  const rows = useMemo(() => {
    const sorted = [...contribs].sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap));
    const head = sorted.slice(0, top);
    const rest = sorted.slice(top);
    const restSum = rest.reduce((s, c) => s + c.shap, 0);
    const items: { label: string; value: string; shap: number; start: number; end: number; desc?: string | null }[] = [];
    let cur = base;
    for (const c of head) {
      items.push({ label: c.feature, value: fmtValue(c.value), shap: c.shap, start: cur, end: cur + c.shap, desc: c.description });
      cur += c.shap;
    }
    if (rest.length) {
      items.push({ label: `${rest.length} other features`, value: "", shap: restSum, start: cur, end: cur + restSum });
      cur += restSum;
    }
    return { items, final: cur };
  }, [base, contribs, top]);
  const xs = [base, rows.final, ...rows.items.flatMap((r) => [r.start, r.end])];
  const lo = Math.min(...xs);
  const hi = Math.max(...xs);
  const pad = (hi - lo) * 0.06 || 1;
  const x = (n: number) => ((n - (lo - pad)) / (hi - lo + 2 * pad)) * 100;
  const grid = "grid grid-cols-[minmax(6rem,10rem)_1fr_3.5rem] items-center gap-2 md:grid-cols-[minmax(9rem,14rem)_1fr_4rem]";
  return (
    <div className="text-[13px]">
      <div className={cn(grid, "py-1")}>
        <span className="text-muted-foreground">Base value</span>
        <span className="relative h-4">
          <span className="absolute inset-y-0 w-0.5 bg-foreground/60" style={{ left: `${x(base)}%` }} />
        </span>
        <span className="num text-right font-medium">{fmtNum(base, 1)}</span>
      </div>
      <ul>
        {rows.items.map((r, i) => (
          <li key={`${r.label}-${i}`} className={cn(grid, "border-t border-border/60 py-1")} title={r.desc ?? undefined}>
            <span className="min-w-0 truncate">
              <span className="font-mono text-xs">{r.label}</span>
              {r.value && <span className="ml-1.5 text-xs text-muted-foreground">= {r.value}</span>}
            </span>
            <span className="relative h-4">
              <span
                className={cn("absolute inset-y-0.5 rounded-sm", r.shap >= 0 ? "bg-brand" : "bg-negative")}
                style={{ left: `${x(Math.min(r.start, r.end))}%`, width: `${Math.max(0.4, Math.abs(x(r.end) - x(r.start)))}%` }}
              />
            </span>
            <span className={cn("num text-right font-medium", r.shap >= 0 ? "text-foreground" : "text-negative")}>
              {r.shap >= 0 ? "+" : "−"}
              {fmtNum(Math.abs(r.shap), 1)}
            </span>
          </li>
        ))}
      </ul>
      <div className={cn(grid, "border-t-2 border-border py-1.5")}>
        <span className="font-semibold">Prediction</span>
        <span className="relative h-4">
          <span className="absolute inset-y-0 w-0.5 bg-brand" style={{ left: `${x(rows.final)}%` }} />
        </span>
        <span className="num text-right font-semibold">
          {fmtNum(rows.final, 1)} <span className="text-[10px] font-normal text-muted-foreground">{unit}</span>
        </span>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ prediction range row
/** p10–p90 band with p50 tick and mean diamond; actual = dot; baseline = hollow ring. */
export function PredRange({ q10, q50, q90, mean, actual, baseline, max }: { q10: number | null; q50: number | null; q90: number | null; mean: number | null; actual: number | null; baseline: number | null; max: number }) {
  const lo = -10;
  const x = (n: number) => Math.max(0, Math.min(100, ((n - lo) / (max - lo)) * 100));
  const inside = actual !== null && q10 !== null && q90 !== null && actual >= q10 && actual <= q90;
  const label = `Predicted range ${fmtNum(q10, 0)}–${fmtNum(q90, 0)}, median ${fmtNum(q50, 0)}, mean ${fmtNum(mean, 1)}; actual ${fmtNum(actual, 0)}${actual !== null ? (inside ? " (inside)" : " (outside)") : ""}; baseline ${fmtNum(baseline, 1)}`;
  return (
    <div role="img" aria-label={label} title={label} className="relative h-5 w-full min-w-32">
      <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-surface-3" />
      {q10 !== null && q90 !== null && <div className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-brand/40" style={{ left: `${x(q10)}%`, width: `${Math.max(0.5, x(q90) - x(q10))}%` }} />}
      {q50 !== null && <div className="absolute top-1/2 h-3.5 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground" style={{ left: `${x(q50)}%` }} />}
      {mean !== null && <div className="absolute top-1/2 size-2 -translate-x-1/2 -translate-y-1/2 rotate-45 bg-brand" style={{ left: `${x(mean)}%` }} />}
      {baseline !== null && <div className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--chart-2)]" style={{ left: `${x(baseline)}%` }} />}
      {actual !== null && <div className={cn("absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card", inside ? "bg-positive" : "bg-negative")} style={{ left: `${x(actual)}%` }} />}
    </div>
  );
}

export function PredRangeLegend() {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      <li className="inline-flex items-center gap-1.5">
        <span className="h-1.5 w-6 rounded-full bg-brand/40" /> p10–p90
      </li>
      <li className="inline-flex items-center gap-1.5">
        <span className="h-3 w-0.5 rounded-full bg-foreground" /> median (p50)
      </li>
      <li className="inline-flex items-center gap-1.5">
        <span className="size-2 rotate-45 bg-brand" /> mean
      </li>
      <li className="inline-flex items-center gap-1.5">
        <span className="size-2.5 rounded-full border-2 border-[var(--chart-2)]" /> last-5 baseline
      </li>
      <li className="inline-flex items-center gap-1.5">
        <span className="size-2.5 rounded-full bg-positive" />/<span className="size-2.5 rounded-full bg-negative" /> actual (inside / outside range)
      </li>
    </ul>
  );
}

// ------------------------------------------------------------------ composed bars + line
export function BarsWithLine({ data, xKey, bar, line, height = 240, lineFmt }: { data: Record<string, number | string | null>[]; xKey: string; bar: BarSeries; line: BarSeries[]; height?: number; lineFmt?: (n: number) => string }) {
  const animate = !useReducedMotion();
  const config = Object.fromEntries([bar, ...line].map((s) => [s.key, { label: s.label, color: s.color }])) satisfies ChartConfig;
  return (
    <ChartContainer config={config} className="aspect-auto w-full min-w-0" style={{ height }}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey={xKey} {...axis} />
        <YAxis yAxisId="l" {...axis} width={40} />
        <YAxis yAxisId="r" orientation="right" {...axis} width={44} tickFormatter={lineFmt} />
        <ChartTooltip cursor={{ fill: "var(--surface-2)" }} content={<ChartTooltipContent />} />
        <Bar yAxisId="l" dataKey={bar.key} fill={bar.color} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        {line.map((l) => (
          <Line key={l.key} yAxisId="r" dataKey={l.key} stroke={l.color} strokeWidth={2} dot={{ r: 3, fill: l.color }} isAnimationActive={animate} />
        ))}
      </ComposedChart>
    </ChartContainer>
  );
}
