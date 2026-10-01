import { normalizeRange, rangeGeometry, type PointsRange } from "@/lib/range";
import { tierFor } from "@/lib/tokens";
import { cn } from "@/lib/utils";

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

/**
 * Floor–median–ceiling bar (§2.7). Track = surface-3, band = tier colour at 35 %,
 * median = 2 px tick + number. After the match an `actual` diamond is overlaid; outside the
 * band it turns positive/negative and gains ▲/▼ so colour is never the only signal.
 */
export function RangeBar({
  range,
  actual,
  scaleMin = 0,
  scaleMax = 120,
  showLabels = true,
  className,
}: {
  range: PointsRange;
  actual?: number;
  scaleMin?: number;
  scaleMax?: number;
  showLabels?: boolean;
  className?: string;
}) {
  const r = normalizeRange(range);
  const g = rangeGeometry(r, scaleMin, scaleMax);
  const tier = tierFor(r.median);
  // Tier ramp (violet → gold) at 35 %: <20 faint · 20–59 violet · 60+ gold.
  const band = tier === 0 ? "bg-faint/35" : tier <= 2 ? "bg-brand/40" : "bg-primary/45";
  const actualPos = actual === undefined ? null : rangeGeometry({ floor: actual, median: actual, ceiling: actual }, scaleMin, scaleMax).marker;
  const outcome = actual === undefined ? null : actual > r.ceiling ? "above" : actual < r.floor ? "below" : "inside";
  const label =
    `Projected points: floor ${fmt(r.floor)}, median ${fmt(r.median)}, ceiling ${fmt(r.ceiling)}` +
    (actual === undefined ? "" : `; actual ${fmt(actual)}${outcome === "inside" ? ", inside the range" : `, ${outcome} the range`}`);
  return (
    <div className={cn("w-full", className)}>
      <div role="img" aria-label={label} className="relative h-2 w-full rounded-full bg-surface-3" data-testid="range-track">
        <div
          data-testid="range-band"
          className={cn("absolute inset-y-0 rounded-full", band)}
          style={{ left: `${g.start}%`, width: `${g.width}%` }}
        />
        <div
          data-testid="range-marker"
          className="absolute -top-1 h-4 w-[2px] -translate-x-1/2 rounded-full bg-foreground"
          style={{ left: `${g.marker}%` }}
        />
        {actualPos !== null && (
          <div
            data-testid="range-actual"
            className={cn(
              "absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rotate-45 rounded-[2px] ring-2 ring-card",
              outcome === "above" ? "bg-positive" : outcome === "below" ? "bg-negative" : "bg-primary",
            )}
            style={{ left: `${actualPos}%` }}
          />
        )}
      </div>
      {showLabels && (
        <div aria-hidden className="num mt-1 flex justify-between text-[11px] leading-4 text-muted-foreground">
          <span>{fmt(r.floor)}</span>
          <span className="font-semibold text-foreground">
            {fmt(r.median)}
            {actual !== undefined && (
              <span className={cn("ml-1.5", outcome === "above" ? "text-positive" : outcome === "below" ? "text-negative" : "text-muted-foreground")}>
                {outcome === "above" ? "▲" : outcome === "below" ? "▼" : "◆"} {fmt(actual)}
              </span>
            )}
          </span>
          <span>{fmt(r.ceiling)}</span>
        </div>
      )}
    </div>
  );
}
