"use client";

import { useHealth } from "@/lib/api/queries";
import { cn } from "@/lib/utils";

type Tone = "ok" | "warn" | "down" | "pending";

const DOT: Record<Tone, string> = {
  ok: "bg-emerald-500",
  warn: "bg-amber-500",
  down: "bg-red-500",
  pending: "bg-muted-foreground/50 animate-pulse",
};

/**
 * Data-freshness badge. For now it reflects API + DB health from /api/v1/health;
 * later it will read /api/v1/meta/freshness ("Pre-toss projection" / "Lineups confirmed ✓ 19:02").
 */
export function FreshnessBadge({ className }: { className?: string }) {
  const { data, isPending, isError, dataUpdatedAt } = useHealth();

  let tone: Tone;
  let label: string;
  let detail: string;
  if (isPending) {
    tone = "pending";
    label = "Checking…";
    detail = "Contacting API";
  } else if (isError || !data) {
    tone = "down";
    label = "API offline";
    detail = "The Predict-11 API is unreachable";
  } else if (data.status === "ok" && data.db === "ok") {
    tone = "ok";
    label = "Live";
    detail = `API ok · DB ok · v${data.version}`;
  } else {
    tone = "warn";
    label = "Degraded";
    detail = `API ${data.status} · DB ${data.db}`;
  }

  const checked = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : null;
  const title = checked ? `${detail} · checked ${checked}` : detail;

  return (
    <span
      role="status"
      aria-live="polite"
      title={title}
      className={cn(
        "inline-flex h-7 items-center gap-2 rounded-full border bg-background px-2.5 text-xs font-medium",
        className,
      )}
    >
      <span aria-hidden className={cn("size-2 rounded-full", DOT[tone])} />
      <span>{label}</span>
      <span className="sr-only">{title}</span>
    </span>
  );
}
