"use client";

import { CircleAlert, RotateCcw } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { TeamBadge } from "@/components/player/team-badge";
import { cn } from "@/lib/utils";

import { ApiError } from "../api";
import type { TeamRef } from "../types";

/**
 * Local ErrorState (§5.2 lists one under Shell; not in components/shell yet). Says what failed,
 * why if known, and offers Retry. Never an infinite spinner.
 */
export function ErrorState({
  title = "Couldn't load this",
  error,
  onRetry,
  action,
  className,
}: {
  title?: string;
  error: unknown;
  onRetry?: () => void;
  action?: { href: string; label: string };
  className?: string;
}) {
  const msg =
    error instanceof ApiError
      ? error.status === 0
        ? error.message
        : `${error.message} (HTTP ${error.status})`
      : error instanceof Error
        ? error.message
        : "Unknown error";
  return (
    <section role="alert" className={cn("rounded-xl border border-negative/30 bg-card p-4 md:p-5", className)}>
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-negative/12 text-negative">
          <CircleAlert aria-hidden className="size-5" strokeWidth={1.75} />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">{msg}</p>
          <div className="mt-3 flex flex-wrap gap-3">
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex h-9 items-center gap-1.5 rounded-[10px] border border-border bg-surface-2 px-3 text-sm font-medium outline-none hover:bg-surface-3 focus-visible:ring-2 focus-visible:ring-ring"
              >
                <RotateCcw aria-hidden className="size-4" /> Retry
              </button>
            )}
            {action && (
              <Link href={action.href} className="inline-flex h-9 items-center text-sm font-medium text-brand underline-offset-4 hover:underline">
                {action.label} <span aria-hidden>&nbsp;→</span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

/** Badge + name linking to the team page. `short` shows the code only below `sm`. */
export function TeamName({
  team,
  link = true,
  short = "responsive",
  size = "sm",
  className,
}: {
  team: TeamRef;
  link?: boolean;
  short?: "responsive" | "always" | "never";
  size?: "sm" | "md";
  className?: string;
}) {
  // The badge already prints the short code, so the name is the only extra text.
  const label = (
    <>
      <TeamBadge team={team.short_code} size={size} />
      {short !== "always" && (
        <span className={cn("truncate font-medium", short === "responsive" && "max-sm:sr-only")}>{team.name}</span>
      )}
    </>
  );
  const cls = cn("inline-flex min-w-0 items-center gap-2", className);
  return link ? (
    <Link
      href={`/teams/${encodeURIComponent(team.short_code)}`}
      className={cn(cls, "rounded outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring")}
    >
      {label}
    </Link>
  ) : (
    <span className={cls}>{label}</span>
  );
}

/** Small pill used for clinched / eliminated / champion markers. Text always carries the meaning. */
export function StatusPill({
  tone,
  children,
  className,
}: {
  tone: "positive" | "negative" | "gold" | "brand" | "muted";
  children: ReactNode;
  className?: string;
}) {
  const cls = {
    positive: "bg-positive/14 text-positive ring-positive/30",
    negative: "bg-negative/12 text-negative ring-negative/30",
    gold: "bg-primary/14 text-gold-text ring-primary/35",
    brand: "bg-brand/14 text-brand ring-brand/30",
    muted: "bg-surface-2 text-muted-foreground ring-border",
  }[tone];
  return (
    <span className={cn("inline-flex h-5 shrink-0 items-center rounded-full px-2 text-[11px] font-semibold whitespace-nowrap ring-1 ring-inset", cls, className)}>
      {children}
    </span>
  );
}
