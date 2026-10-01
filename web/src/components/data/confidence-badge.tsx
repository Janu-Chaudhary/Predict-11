import { confidenceFor, type ConfidenceLevel, type ConfidenceThresholds } from "@/lib/confidence";
import { cn } from "@/lib/utils";

const STYLE: Record<ConfidenceLevel, { cls: string; bars: number; text: string }> = {
  low: { cls: "text-warning ring-warning/35 bg-warning/10", bars: 1, text: "Low" },
  medium: { cls: "text-info ring-info/35 bg-info/10", bars: 2, text: "Medium" },
  high: { cls: "text-positive ring-positive/35 bg-positive/10", bars: 3, text: "High" },
};

/**
 * Confidence cue for a stat resting on sample size n (§4.6 "n=64 · medium confidence").
 * Signal bars + text, so colour is never the only signal. Pass `level` to override the n rule.
 */
export function ConfidenceBadge({
  n,
  level,
  thresholds,
  showN = true,
  className,
}: {
  n?: number;
  level?: ConfidenceLevel;
  thresholds?: ConfidenceThresholds;
  showN?: boolean;
  className?: string;
}) {
  const lvl = level ?? confidenceFor(n ?? 0, thresholds);
  const s = STYLE[lvl];
  const label = `${s.text} confidence${n !== undefined ? `, sample size ${n}` : ""}`;
  return (
    <span
      title={label}
      data-level={lvl}
      className={cn("inline-flex h-6 items-center gap-1.5 rounded-full px-2 text-[11px] leading-none font-semibold ring-1 ring-inset", s.cls, className)}
    >
      <svg aria-hidden viewBox="0 0 12 10" className="h-2.5 w-3">
        {[0, 1, 2].map((i) => (
          <rect key={i} x={i * 4} y={6 - i * 3} width="3" height={4 + i * 3} rx="0.75" fill="currentColor" opacity={i < s.bars ? 1 : 0.25} />
        ))}
      </svg>
      <span aria-hidden>
        {showN && n !== undefined && <span className="num font-medium">n={n} · </span>}
        {s.text.toLowerCase()}
      </span>
      <span className="sr-only">{label}</span>
    </span>
  );
}
