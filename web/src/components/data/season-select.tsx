"use client";

import { useRouter } from "next/navigation";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SEASONS } from "@/lib/seasons";
import { cn } from "@/lib/utils";

export { CURRENT_SEASON, SEASONS } from "@/lib/seasons";

/**
 * Season switcher. Controlled (`value` + `onValueChange`) or navigational (`hrefFor`).
 */
export function SeasonSelect({
  value,
  seasons = SEASONS,
  onValueChange,
  hrefFor,
  label = "Season",
  className,
}: {
  value: number;
  seasons?: number[];
  onValueChange?: (season: number) => void;
  hrefFor?: (season: number) => string;
  label?: string;
  className?: string;
}) {
  const router = useRouter();
  return (
    <Select
      value={String(value)}
      onValueChange={(v) => {
        if (v === null) return;
        const s = Number(v);
        onValueChange?.(s);
        if (hrefFor) router.push(hrefFor(s));
      }}
    >
      <SelectTrigger aria-label={label} className={cn("num h-9 min-w-28 rounded-[10px] bg-card", className)}>
        <span className="text-xs text-muted-foreground">IPL</span>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {seasons.map((s) => (
          <SelectItem key={s} value={String(s)} className="num">
            {s}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
