import { cn } from "@/lib/utils";

export type FormBarItem = {
  key: string | number;
  value: number;
  /** printed under the bar, e.g. "75*" or "2/24" */
  label: string;
  /** full description for the accessible summary */
  title: string;
  emphasis?: "high" | "low" | null;
};

/**
 * Last-N mini bars (§2.7 "Form"): newest on the right, number always printed. Used for runs and
 * wickets (not fantasy tiers, so a single brand hue; ≥50 runs / 3+ wkts in gold).
 */
export function FormBars({ items, max, label, className, stretch = false }: { items: FormBarItem[]; max?: number; label: string; className?: string; /** Fill the row: wider, taller bars on desktop. */ stretch?: boolean }) {
  const top = max ?? Math.max(1, ...items.map((i) => i.value));
  return (
    <figure className={cn("min-w-0", className)}>
      <ol aria-label={label} className={cn("flex items-end gap-1 overflow-x-auto pb-1 sm:gap-1.5", stretch && "lg:gap-2.5")}>
        {items.map((it) => (
          <li key={it.key} title={it.title} className={cn("flex shrink-0 flex-col items-center gap-1", stretch ? "w-7 sm:w-auto sm:max-w-16 sm:min-w-8 sm:flex-1 sm:shrink" : "w-7 sm:w-8")}>
            <span className="sr-only">{it.title}</span>
            <span aria-hidden className={cn("flex h-14 w-full items-end overflow-hidden rounded-[4px] bg-surface-2", stretch && "lg:h-24 lg:rounded-md")}>
              <span
                className={cn("w-full rounded-[4px]", it.emphasis === "high" ? "bg-primary" : it.emphasis === "low" ? "bg-faint/60" : "bg-brand")}
                style={{ height: `${Math.max(it.value > 0 ? 8 : 3, Math.min(100, (it.value / top) * 100))}%` }}
              />
            </span>
            <span aria-hidden className={cn("num text-[11px] leading-none whitespace-nowrap text-muted-foreground", stretch && "lg:text-[13px] lg:font-medium lg:text-foreground")}>
              {it.label}
            </span>
          </li>
        ))}
      </ol>
    </figure>
  );
}
