import { cn } from "@/lib/utils";

/**
 * Tiny inline trend line (no axes). Pure SVG so it can render in server components and dense
 * table cells. The last point is marked; `aria-label` should summarise the trend.
 */
export function Sparkline({
  values,
  width = 96,
  height = 28,
  label,
  stroke = "var(--brand)",
  showArea = true,
  className,
}: {
  values: number[];
  width?: number;
  height?: number;
  label: string;
  stroke?: string;
  showArea?: boolean;
  className?: string;
}) {
  if (values.length === 0) {
    return <span role="img" aria-label={`${label}: no data`} className={cn("inline-block text-faint", className)} style={{ width, height }} />;
  }
  const pad = 3;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = values.length > 1 ? (width - pad * 2) / (values.length - 1) : 0;
  const pts = values.map((v, i) => [pad + i * step, height - pad - ((v - min) / span) * (height - pad * 2)] as const);
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${d} L${pts[pts.length - 1][0].toFixed(1)},${height} L${pts[0][0].toFixed(1)},${height} Z`;
  const [lx, ly] = pts[pts.length - 1];
  return (
    <svg role="img" aria-label={label} width={width} height={height} viewBox={`0 0 ${width} ${height}`} className={cn("overflow-visible", className)}>
      {showArea && <path d={area} fill={stroke} opacity={0.12} />}
      <path d={d} fill="none" stroke={stroke} strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lx} cy={ly} r={2.5} fill={stroke} stroke="var(--card)" strokeWidth={1.5} />
    </svg>
  );
}
