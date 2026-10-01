"use client";

import { AlertTriangle, RotateCw } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

import { ApiError } from "./api";

/**
 * Local ErrorState (§5.2 lists one under Shell, but it is not in components/ yet). Says what
 * failed, why, and offers Retry plus the nearest useful screen. Never a dead end (§6).
 */
export function ErrorState({
  title,
  error,
  onRetry,
  retrying = false,
  action,
  className,
}: {
  title: string;
  error: unknown;
  onRetry?: () => void;
  retrying?: boolean;
  action?: { href: string; label: string };
  className?: string;
}) {
  const status = error instanceof ApiError ? error.status : null;
  const cause =
    status === null
      ? "The stats API could not be reached. It may be restarting; the page retries automatically when you come back."
      : status === 404
        ? "The API has no record for this."
        : `The API returned an error (${error instanceof Error ? error.message : "unknown"}).`;
  return (
    <section role="alert" className={cn("rounded-xl border border-negative/30 bg-card p-5 md:p-6", className)}>
      <div className="flex items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-negative">
          <AlertTriangle aria-hidden className="size-5" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{cause}</p>
          <div className="mt-4 flex flex-wrap items-center gap-4">
            {onRetry && status !== 404 && (
              <button
                type="button"
                onClick={onRetry}
                disabled={retrying}
                className="inline-flex h-11 items-center gap-2 rounded-[10px] border border-border bg-surface-2 px-4 text-sm font-medium outline-none hover:bg-surface-3 focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
              >
                <RotateCw aria-hidden className={cn("size-4", retrying && "animate-spin motion-reduce:animate-none")} />
                {retrying ? "Retrying…" : "Retry"}
              </button>
            )}
            {action && (
              <Link href={action.href} className="inline-flex h-11 items-center text-sm font-medium text-brand underline-offset-4 hover:underline">
                {action.label} <span aria-hidden>&nbsp;→</span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
