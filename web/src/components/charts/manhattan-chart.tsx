"use client";

import { Bar, BarChart, CartesianGrid, ReferenceLine, XAxis, YAxis } from "recharts";

import { ChartContainer, ChartTooltip } from "@/components/ui/chart";

import { useReducedMotion } from "@/hooks/use-reduced-motion";

import { ChartFrame } from "./chart-frame";
import { useTeamColour } from "./team-colours";

export type ManhattanOver = { over: number; runs: number; wickets?: number };

/**
 * Manhattan (§2.7): runs per over as bars in the batting team's colour at 85 %, wickets as
 * dots stacked above the bar, and an optional dashed par run-rate line.
 */
export function ManhattanChart({ team, overs, parRunRate, summary }: { team: string; overs: ManhattanOver[]; parRunRate?: number; summary: string }) {
  const animate = !useReducedMotion();
  const colour = useTeamColour(team);
  const config = { runs: { label: "Runs", color: colour } };
  const WicketBar = (props: { x?: number; y?: number; width?: number; height?: number; payload?: ManhattanOver }) => {
    const { x = 0, y = 0, width = 0, height = 0, payload } = props;
    const w = payload?.wickets ?? 0;
    const r = Math.min(4, width / 2 - 0.5);
    return (
      <g>
        <path
          d={`M${x},${y + height} V${y + r} q0,-${r} ${r},-${r} H${x + width - r} q${r},0 ${r},${r} V${y + height} Z`}
          fill="var(--color-runs)"
          fillOpacity={0.85}
        />
        {Array.from({ length: w }, (_, i) => (
          <circle key={i} cx={x + width / 2} cy={y - 6 - i * 9} r={3.5} fill="var(--negative)" stroke="var(--card)" strokeWidth={1.5} />
        ))}
      </g>
    );
  };
  return (
    <ChartFrame
      title={`Manhattan · ${team}`}
      summary={summary}
      table={{ columns: ["Over", "Runs", "Wickets"], rows: overs.map((o) => [o.over, o.runs, o.wickets ?? 0]) }}
    >
      <ChartContainer config={config} className="aspect-auto h-56 w-full md:h-64">
        <BarChart data={overs} margin={{ top: 24, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="over" tickLine={false} axisLine={false} fontSize={11} interval="preserveStartEnd" />
          <YAxis tickLine={false} axisLine={false} fontSize={11} width={36} allowDecimals={false} />
          {parRunRate !== undefined && (
            <ReferenceLine y={parRunRate} stroke="var(--faint)" strokeDasharray="4 4" label={{ value: `par ${parRunRate}`, position: "insideTopRight", fill: "var(--faint)", fontSize: 11 }} />
          )}
          <ChartTooltip
            cursor={{ fill: "var(--surface-2)" }}
            content={({ active, payload }) => {
              const o = payload?.[0]?.payload as ManhattanOver | undefined;
              return active && o ? (
                <div className="num rounded-lg border border-border bg-popover px-2.5 py-1.5 text-xs shadow-e2">
                  <div className="font-medium">Over {o.over}</div>
                  <div className="text-muted-foreground">
                    {o.runs} runs{o.wickets ? ` · ${o.wickets} wkt` : ""}
                  </div>
                </div>
              ) : null;
            }}
          />
          <Bar dataKey="runs" shape={WicketBar} isAnimationActive={animate}
            animationDuration={600} />
        </BarChart>
      </ChartContainer>
    </ChartFrame>
  );
}
