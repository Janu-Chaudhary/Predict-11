import { TIER_CLASS, tierFor } from "@/lib/tokens";
import { cn } from "@/lib/utils";

export type MatchResult = "W" | "L" | "NR" | "T";

const RESULT: Record<MatchResult, { cls: string; label: string }> = {
  W: { cls: "bg-positive/18 text-positive ring-positive/35", label: "Won" },
  L: { cls: "bg-negative/15 text-negative ring-negative/35", label: "Lost" },
  NR: { cls: "bg-surface-3 text-muted-foreground ring-border", label: "No result" },
  T: { cls: "bg-warning/15 text-warning ring-warning/35", label: "Tied" },
};

/**
 * Form strip (§2.7 "Form"), newest on the right.
 * - `results`: team form as W/L/NR pills (letter + colour).
 * - `scores`: fantasy scores as tier-coloured mini bars with the number printed.
 */
export function FormStrip(
  props:
    | { results: MatchResult[]; scores?: never; max?: number; className?: string }
    | { scores: number[]; results?: never; max?: number; scaleMax?: number; className?: string },
) {
  const max = props.max ?? 5;
  if (props.results) {
    const items = props.results.slice(-max);
    const label = `Last ${items.length}: ${items.map((r) => RESULT[r].label.toLowerCase()).join(", ")} (newest last)`;
    return (
      <ol aria-label={label} className={cn("inline-flex items-center gap-1", props.className)}>
        {items.map((r, i) => (
          <li
            key={i}
            aria-hidden
            className={cn("font-condensed flex size-6 items-center justify-center rounded-full text-[11px] font-bold ring-1 ring-inset", RESULT[r].cls)}
          >
            {r === "NR" ? "–" : r}
          </li>
        ))}
      </ol>
    );
  }
  const scores = props.scores.slice(-max);
  const top = "scaleMax" in props && props.scaleMax ? props.scaleMax : Math.max(100, ...scores);
  const label = `Last ${scores.length} fantasy scores: ${scores.join(", ")} (newest last)`;
  return (
    <ol aria-label={label} className={cn("inline-flex items-end gap-1", props.className)}>
      {scores.map((s, i) => {
        const tier = TIER_CLASS[tierFor(s)];
        return (
          <li key={i} aria-hidden className="flex w-6 flex-col items-center gap-0.5">
            <span className="flex h-7 w-full items-end overflow-hidden rounded-[3px] bg-surface-2">
              <span className={cn("w-full rounded-[3px]", tier.bg)} style={{ height: `${Math.max(8, Math.min(100, (s / top) * 100))}%` }} />
            </span>
            <span className="num text-[11px] leading-none text-muted-foreground">{s}</span>
          </li>
        );
      })}
    </ol>
  );
}
