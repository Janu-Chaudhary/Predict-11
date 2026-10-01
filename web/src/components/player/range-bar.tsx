import { normalizeRange, rangeGeometry, type PointsRange } from "@/lib/range";
import { cn } from "@/lib/utils";

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

/**
 * Floor–median–ceiling bar. Shows uncertainty honestly: the band is the plausible range,
 * the tick is the median projection.
 */
export function RangeBar({
  range,
  scaleMin = 0,
  scaleMax = 120,
  className,
}: {
  range: PointsRange;
  scaleMin?: number;
  scaleMax?: number;
  className?: string;
}) {
  const r = normalizeRange(range);
  const g = rangeGeometry(r, scaleMin, scaleMax);
  const label = `Projected points: floor ${fmt(r.floor)}, median ${fmt(r.median)}, ceiling ${fmt(r.ceiling)}`;
  return (
    <div className={cn("w-full", className)}>
      <div
        role="img"
        aria-label={label}
        className="relative h-2 w-full rounded-full bg-muted"
        data-testid="range-track"
      >
        <div
          data-testid="range-band"
          className="absolute inset-y-0 rounded-full bg-pitch/35 dark:bg-pitch/45"
          style={{ left: `${g.start}%`, width: `${g.width}%` }}
        />
        <div
          data-testid="range-marker"
          className="absolute -top-0.5 h-3 w-1 -translate-x-1/2 rounded-full bg-pitch ring-2 ring-card"
          style={{ left: `${g.marker}%` }}
        />
      </div>
      <div aria-hidden className="mt-1 flex justify-between text-[10px] text-muted-foreground tabular-nums">
        <span>{fmt(r.floor)}</span>
        <span className="font-semibold text-foreground">{fmt(r.median)}</span>
        <span>{fmt(r.ceiling)}</span>
      </div>
    </div>
  );
}
