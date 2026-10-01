"use client";

import { AlertTriangle, RotateCw } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { ApiError } from "./api";
import type { StatFilter } from "./types";

/** Flat card with an overline heading (§2.5). */
export function Panel({
  title,
  action,
  children,
  className,
  bodyClassName,
  id,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  id?: string;
}) {
  const headingId = id ? `${id}-h` : undefined;
  return (
    <section aria-labelledby={headingId} className={cn("min-w-0 rounded-xl border border-border bg-card shadow-e1", className)}>
      {(title || action) && (
        <header className="flex min-h-11 flex-wrap items-center justify-between gap-2 px-3 pt-3 md:px-4">
          {title && (
            <h2 id={headingId} className="text-overline text-muted-foreground">
              {title}
            </h2>
          )}
          {action}
        </header>
      )}
      <div className={cn("p-3 md:p-4", title && "pt-2 md:pt-2", bodyClassName)}>{children}</div>
    </section>
  );
}

/**
 * ErrorState (§7.2): the cause, what to do, Retry. Never an infinite spinner.
 * (Local stand-in: the shell has no shared ErrorState yet.)
 */
export function QueryError({ error, onRetry, what = "these stats", className }: { error: unknown; onRetry?: () => void; what?: string; className?: string }) {
  const status = error instanceof ApiError ? error.status : null;
  const reason =
    status === null
      ? "The stats API didn’t answer. It may be restarting; it usually comes back within a minute."
      : status === 404
        ? (error as ApiError).message
        : `The API returned an error (${(error as Error).message}).`;
  return (
    <div role="alert" className={cn("flex items-start gap-3 rounded-xl border border-negative/30 bg-negative/8 p-4", className)}>
      <AlertTriangle aria-hidden className="mt-0.5 size-5 shrink-0 text-negative" strokeWidth={1.75} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">Couldn’t load {what}</p>
        <p className="mt-1 text-sm text-muted-foreground">{reason}</p>
        {onRetry && status !== 404 && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 inline-flex h-9 items-center gap-1.5 rounded-[10px] border border-border bg-card px-3 text-sm font-medium outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
          >
            <RotateCw aria-hidden className="size-4" /> Retry
          </button>
        )}
      </div>
    </div>
  );
}

const CURRENT = 2026;
const SEASONS = Array.from({ length: CURRENT - 2008 + 1 }, (_, i) => CURRENT - i);

export function encodeFilter(f: StatFilter): string {
  if (f.season) return `season:${f.season}`;
  if (f.since) return `since:${f.since}`;
  return "all";
}

export function decodeFilter(v: string): StatFilter {
  const [k, val] = v.split(":");
  if (k === "season" && val) return { season: Number(val) };
  if (k === "since" && val) return { since: val };
  return {};
}

export function filterLabel(f: StatFilter): string {
  if (f.season) return `IPL ${f.season}`;
  if (f.since) return `Since ${f.since}`;
  return "Career";
}

/** Career / since / single-season scope. Native select: robust on touch and with screen readers. */
export function ScopeSelect({ value, onChange, seasons = SEASONS, className }: { value: StatFilter; onChange: (f: StatFilter) => void; seasons?: number[]; className?: string }) {
  return (
    <label className={cn("inline-flex items-center gap-2", className)}>
      <span className="text-overline text-muted-foreground">Scope</span>
      <select
        value={encodeFilter(value)}
        onChange={(e) => onChange(decodeFilter(e.target.value))}
        className="num h-9 rounded-[10px] border border-input bg-card px-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <option value="all">Career</option>
        <optgroup label="Since">
          <option value={`since:${CURRENT - 2}`}>Last 3 seasons ({CURRENT - 2}+)</option>
          <option value="since:2023">Impact-sub era (2023+)</option>
        </optgroup>
        <optgroup label="Season">
          {seasons.map((s) => (
            <option key={s} value={`season:${s}`}>
              {s}
            </option>
          ))}
        </optgroup>
      </select>
    </label>
  );
}

/** Horizontal metric bar with the number printed (colour never the only signal). */
export function MetricBar({
  label,
  value,
  max,
  display,
  hint,
  tone = "brand",
}: {
  label: ReactNode;
  value: number | null;
  max: number;
  display: string;
  hint?: ReactNode;
  tone?: "brand" | "primary" | "positive" | "negative" | "muted";
}) {
  const w = value === null || max <= 0 ? 0 : Math.max(2, Math.min(100, (value / max) * 100));
  const bg = { brand: "bg-brand", primary: "bg-primary", positive: "bg-positive", negative: "bg-negative", muted: "bg-faint" }[tone];
  return (
    <div className="grid grid-cols-[minmax(0,7.5rem)_1fr_auto] items-center gap-x-3 gap-y-0.5 py-1.5 sm:grid-cols-[10rem_1fr_auto]">
      <span className="truncate text-sm">{label}</span>
      <span aria-hidden className="h-2 overflow-hidden rounded-full bg-surface-2">
        <span className={cn("block h-full rounded-full", bg, value === null && "opacity-0")} style={{ width: `${w}%` }} />
      </span>
      <span className="num w-14 text-right text-sm font-semibold">{display}</span>
      {hint && <span className="num col-start-2 col-end-4 text-xs text-muted-foreground">{hint}</span>}
    </div>
  );
}
