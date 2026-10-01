import Link from "next/link";
import type { ReactNode } from "react";

import { NumberRoll } from "@/components/loaders/number-roll";
import { cn } from "@/lib/utils";

/**
 * A single headline stat (§4.5 stat tiles). Label (overline) → big tabular value → hint.
 * Set `roll` to animate value changes with the scoreboard digit roll.
 */
export function StatTile({
  label,
  value,
  format,
  unit,
  hint,
  delta,
  roll = false,
  href,
  className,
}: {
  label: string;
  value: number | string | null | undefined;
  format?: (n: number) => string;
  unit?: string;
  hint?: ReactNode;
  /** Signed change vs a reference (e.g. last season). Shows ▲/▼ + colour. */
  delta?: { value: number; label?: string; format?: (n: number) => string };
  roll?: boolean;
  href?: string;
  className?: string;
}) {
  const fmt = format ?? ((n: number) => String(n));
  const empty = value === null || value === undefined || value === "";
  const body = (
    <>
      <div className="text-overline truncate text-muted-foreground">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="font-condensed num text-[1.75rem] leading-8 font-bold">
          {empty ? (
            <span className="text-faint" aria-label="No data">
              –
            </span>
          ) : typeof value === "number" && roll ? (
            <NumberRoll value={value} format={fmt} />
          ) : typeof value === "number" ? (
            fmt(value)
          ) : (
            value
          )}
        </span>
        {unit && !empty && <span className="text-xs font-medium text-muted-foreground">{unit}</span>}
      </div>
      {(hint || delta) && (
        <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
          {delta && (
            <span className={cn("num font-medium", delta.value > 0 ? "text-positive" : delta.value < 0 ? "text-negative" : "")}>
              <span aria-hidden>{delta.value > 0 ? "▲" : delta.value < 0 ? "▼" : "•"} </span>
              {(delta.format ?? ((n: number) => (n > 0 ? `+${n}` : String(n))))(delta.value)}
              {delta.label && <span className="font-normal text-muted-foreground"> {delta.label}</span>}
            </span>
          )}
          {hint && <span className="truncate">{hint}</span>}
        </div>
      )}
    </>
  );
  const cls = cn("block min-w-0 rounded-lg border border-border bg-card p-3 shadow-e1 md:p-4", className);
  return href ? (
    <Link href={href} className={cn(cls, "transition-colors hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring")}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}
