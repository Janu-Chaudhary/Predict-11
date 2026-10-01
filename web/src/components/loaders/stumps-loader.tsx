import { cn } from "@/lib/utils";

/**
 * Stumps & bails — the inline action loader (§7.2 #2). Three stumps, two gold bails that hop
 * and settle. Sits inside the control that triggered the work (button, sticky builder bar).
 */
export function StumpsLoader({
  size = 28,
  label = "Working",
  className,
}: {
  size?: number;
  /** Screen-reader text. Pass `null` when the surrounding control already announces the state. */
  label?: string | null;
  className?: string;
}) {
  return (
    <span
      role={label ? "status" : undefined}
      className={cn("stumps-loader inline-flex shrink-0 items-center justify-center", className)}
    >
      <svg viewBox="0 0 40 40" width={size} height={size} aria-hidden>
        <g className="fill-[oklch(0.72_0.08_75)] dark:fill-[oklch(0.86_0.06_80)]">
          <rect x="9" y="12" width="4" height="26" rx="1.5" />
          <rect x="18" y="12" width="4" height="26" rx="1.5" />
          <rect x="27" y="12" width="4" height="26" rx="1.5" />
        </g>
        <rect className="stumps-bail stumps-bail-1 fill-primary" x="9" y="8.5" width="11" height="2.6" rx="1.3" />
        <rect className="stumps-bail stumps-bail-2 fill-primary" x="20" y="8.5" width="11" height="2.6" rx="1.3" />
      </svg>
      {label && <span className="sr-only">{label}</span>}
    </span>
  );
}
