"use client";

import { useHealth } from "@/lib/api/queries";
import { cn } from "@/lib/utils";

type Tone = "ok" | "warn" | "down" | "pending";

const DOT: Record<Tone, string> = {
  ok: "bg-positive",
  warn: "bg-warning",
  down: "bg-negative",
  pending: "bg-faint motion-safe:animate-pulse",
};

/**
 * Data-freshness pill. For now it reflects API + DB health from /api/v1/health;
 * later it will read /api/v1/meta/freshness ("Provisional" / "XI confirmed ✓ 19:02").
 * Background refetches never show a loader — only this pill changes.
 */
export function FreshnessBadge({ className }: { className?: string }) {
  const { data, isPending, isError, dataUpdatedAt } = useHealth();

  const checked = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }) : null;

  let tone: Tone;
  let label: string;
  let detail: string;
  if (isPending) {
    tone = "pending";
    label = "Checking";
    detail = "Contacting API";
  } else if (isError || !data) {
    tone = "down";
    label = "Offline";
    detail = "The Predict-11 API is unreachable";
  } else if (data.status === "ok" && data.db === "ok") {
    tone = "ok";
    label = checked ? `Data ${checked}` : "Data ok";
    detail = `API ok · DB ok · v${data.version}`;
  } else {
    tone = "warn";
    label = "Degraded";
    detail = `API ${data.status} · DB ${data.db}`;
  }

  const title = checked ? `${detail} · checked ${checked}` : detail;

  return (
    <span
      role="status"
      aria-live="polite"
      title={title}
      className={cn(
        "num inline-flex h-7 items-center gap-1.5 rounded-full border border-border bg-surface-1/60 px-2.5 text-xs font-medium whitespace-nowrap text-foreground",
        className,
      )}
    >
      <span aria-hidden className={cn("size-2 rounded-full", DOT[tone])} />
      <span>{label}</span>
      <span className="sr-only">{title}</span>
    </span>
  );
}
