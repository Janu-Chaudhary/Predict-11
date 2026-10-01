"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

import { SEASONS } from "@/components/data/season-select";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

/**
 * Season filter for the records pages. Writes `?season=` (shareable, back-button friendly).
 * `allLabel` adds an "all seasons" option that removes the param.
 */
export function RecordsSeasonSelect({ value, allLabel, className }: { value: number | null; allLabel?: string; className?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, start] = useTransition();
  const current = value === null ? "all" : String(value);
  return (
    <Select
      value={current}
      onValueChange={(v) => {
        if (v === null) return;
        const next = new URLSearchParams(params.toString());
        if (v === "all") next.delete("season");
        else next.set("season", String(v));
        const qs = next.toString();
        start(() => router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false }));
      }}
    >
      <SelectTrigger aria-label="Season" aria-busy={pending || undefined} className={cn("num h-11 min-w-36 rounded-[10px] bg-card", className)}>
        <span className="text-xs text-muted-foreground">IPL</span>
        <SelectValue>{(v: string) => (v === "all" ? (allLabel ?? "All seasons") : v)}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {allLabel && <SelectItem value="all">{allLabel}</SelectItem>}
        {SEASONS.map((s) => (
          <SelectItem key={s} value={String(s)} className="num">
            {s}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/** Segmented filter chips (aria-pressed). 44 px tall on touch, scroll inside their own row. */
export function FilterChips<K extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { key: K; label: string; count?: number }[];
  value: K;
  onChange: (k: K) => void;
}) {
  return (
    <div role="group" aria-label={label} className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:px-0">
      {options.map((o) => {
        const on = o.key === value;
        return (
          <button
            key={o.key}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.key)}
            className={cn(
              "inline-flex h-11 shrink-0 items-center gap-1.5 rounded-full border px-4 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring md:h-9",
              on ? "border-transparent bg-foreground text-background" : "border-border bg-card text-muted-foreground hover:text-foreground",
            )}
          >
            {o.label}
            {o.count !== undefined && <span className={cn("num text-xs", on ? "text-background/70" : "text-faint")}>{o.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
