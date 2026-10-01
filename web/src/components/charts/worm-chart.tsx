"use client";

import { CartesianGrid, Line, LineChart, ReferenceArea, XAxis, YAxis } from "recharts";

import { ChartContainer, ChartTooltip } from "@/components/ui/chart";

import { useReducedMotion } from "@/hooks/use-reduced-motion";

import { ChartFrame, SeriesLegend } from "./chart-frame";
import { useMatchSeries } from "./team-colours";

export type WormPoint = { over: number; runs: number; wicket?: boolean };
export type WormInnings = { team: string; points: WormPoint[] };

type Row = { over: number; home?: number; away?: number; homeW?: boolean; awayW?: boolean };

function merge(home: WormInnings, away: WormInnings): Row[] {
  const byOver = new Map<number, Row>();
  const put = (side: "home" | "away", p: WormPoint) => {
    const r = byOver.get(p.over) ?? { over: p.over };
    r[side] = p.runs;
    if (p.wicket) r[side === "home" ? "homeW" : "awayW"] = true;
    byOver.set(p.over, r);
  };
  home.points.forEach((p) => put("home", p));
  away.points.forEach((p) => put("away", p));
  return [...byOver.values()].sort((a, b) => a.over - b.over);
}

/**
 * Worm (§2.7): cumulative runs by over for both innings. 2 px lines in team chart colours
 * (away dashed when the clash rule moved it), 6 px wicket dots with a surface ring, powerplay
 * (0–6) and death (16–20) bands at 4 %.
 */
export function WormChart({ home, away, summary }: { home: WormInnings; away: WormInnings; summary: string }) {
  const animate = !useReducedMotion();
  const { config, current, awayDashed } = useMatchSeries(home.team, away.team);
  const data = merge(home, away);
  const wicketDot = (side: "home" | "away") =>
    function Dot(props: { cx?: number; cy?: number; payload?: Row; index?: number }) {
      const { cx, cy, payload, index } = props;
      if (cx === undefined || cy === undefined || !payload?.[side === "home" ? "homeW" : "awayW"]) return <g key={`${side}-${index}`} />;
      return <circle key={`${side}-${index}`} cx={cx} cy={cy} r={4} fill={`var(--color-${side})`} stroke="var(--card)" strokeWidth={2} />;
    };
  return (
    <ChartFrame
      title="Worm"
      summary={summary}
      legend={
        <SeriesLegend
          items={[
            { label: home.team, color: current.home.color },
            { label: away.team, color: current.away.color, dashed: awayDashed },
          ]}
        />
      }
      table={{
        columns: ["Over", home.team, away.team],
        rows: data.map((r) => [r.over, r.home ?? "–", r.away ?? "–"]),
      }}
    >
      <ChartContainer config={config} className="aspect-auto h-56 w-full md:h-64">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <ReferenceArea x1={0} x2={6} fill="var(--foreground)" fillOpacity={0.04} ifOverflow="hidden" />
          <ReferenceArea x1={16} x2={20} fill="var(--foreground)" fillOpacity={0.04} ifOverflow="hidden" />
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="over" type="number" domain={[0, 20]} ticks={[0, 6, 10, 16, 20]} tickLine={false} axisLine={false} fontSize={11} />
          <YAxis tickLine={false} axisLine={false} fontSize={11} width={36} />
          <ChartTooltip
            cursor={{ stroke: "var(--border)" }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <div className="num rounded-lg border border-border bg-popover px-2.5 py-1.5 text-xs shadow-e2">
                  <div className="mb-1 font-medium">Over {label}</div>
                  {payload.map((p) => (
                    <div key={String(p.dataKey)} className="flex justify-between gap-4">
                      <span className="text-muted-foreground">{p.dataKey === "home" ? home.team : away.team}</span>
                      <span className="font-medium">{p.value as number}</span>
                    </div>
                  ))}
                </div>
              ) : null
            }
          />
          <Line dataKey="home" type="monotone" stroke="var(--color-home)" strokeWidth={2} dot={wicketDot("home")} activeDot={{ r: 4 }} connectNulls isAnimationActive={animate}
            animationDuration={600} />
          <Line
            dataKey="away"
            type="monotone"
            stroke="var(--color-away)"
            strokeWidth={2}
            strokeDasharray={awayDashed ? "6 4" : undefined}
            dot={wicketDot("away")}
            activeDot={{ r: 4 }}
            connectNulls
            isAnimationActive={animate}
            animationDuration={600}
          />
        </LineChart>
      </ChartContainer>
    </ChartFrame>
  );
}
