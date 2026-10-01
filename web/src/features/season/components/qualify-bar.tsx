import { cn } from "@/lib/utils";

import { formatPct } from "../format";

/**
 * Probability bar (§5.2 QualifyBar). Solid = qualifies on points alone; hatched extension =
 * possible only if NRR breaks a tie in their favour. Both numbers printed; colour isn't the signal.
 */
export function QualifyBar({
  label,
  sure,
  withTies,
  tone = "brand",
  pending = false,
  className,
}: {
  label: string;
  /** Probability on points alone. */
  sure: number;
  /** Probability including NRR-decided ties (≥ sure). */
  withTies: number;
  tone?: "brand" | "gold";
  pending?: boolean;
  className?: string;
}) {
  const a = Math.max(0, Math.min(1, sure));
  const b = Math.max(a, Math.min(1, withTies));
  const extra = b - a;
  const fill = tone === "gold" ? "bg-primary" : "bg-brand";
  const hatch =
    tone === "gold"
      ? "bg-[repeating-linear-gradient(135deg,var(--primary)_0_3px,transparent_3px_6px)]"
      : "bg-[repeating-linear-gradient(135deg,var(--brand)_0_3px,transparent_3px_6px)]";
  const aria =
    extra > 0.0005
      ? `${label}: ${formatPct(a)} on points alone, up to ${formatPct(b)} if net run rate breaks ties`
      : `${label}: ${formatPct(a)}`;
  return (
    <div className={cn("grid grid-cols-[3.25rem_1fr_auto] items-center gap-2", className)} role="img" aria-label={aria}>
      <span aria-hidden className="text-overline text-muted-foreground">
        {label}
      </span>
      <span aria-hidden className="relative flex h-2 overflow-hidden rounded-full bg-surface-3">
        <span className={cn("h-full transition-[width] duration-300 ease-emphasized motion-reduce:transition-none", fill)} style={{ width: `${a * 100}%` }} />
        <span className={cn("h-full opacity-70 transition-[width] duration-300 ease-emphasized motion-reduce:transition-none", hatch)} style={{ width: `${extra * 100}%` }} />
      </span>
      <span aria-hidden className={cn("num w-[6rem] text-right text-[13px] whitespace-nowrap", pending && "text-muted-foreground")}>
        {pending && <span className="mr-0.5">≈</span>}
        <span className="font-semibold">{formatPct(a)}</span>
        {extra > 0.0005 && <span className="text-xs text-muted-foreground"> → {formatPct(b)}</span>}
      </span>
    </div>
  );
}
