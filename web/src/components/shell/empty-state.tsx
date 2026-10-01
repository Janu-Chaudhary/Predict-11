import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * No dead ends (§3.3, §6): every empty state says why there is nothing, when data
 * arrives, and links to the nearest useful screen.
 */
export function EmptyState({
  icon: Icon,
  title,
  why,
  description,
  when,
  action,
  bullets,
  className,
  compact = false,
}: {
  icon: LucideIcon;
  title: string;
  /** Why there is nothing here yet. */
  why?: ReactNode;
  /** @deprecated alias of `why` (scaffold API). */
  description?: ReactNode;
  /** When data is expected to arrive. */
  when?: ReactNode;
  /** Nearest useful screen. */
  action?: { href: string; label: string };
  /** Optional "coming here" list. */
  bullets?: string[];
  className?: string;
  compact?: boolean;
}) {
  return (
    <section
      className={cn(
        "rounded-xl border border-dashed border-border bg-card/60 text-card-foreground",
        compact ? "p-4" : "p-5 md:p-6",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-muted-foreground">
          <Icon aria-hidden className="size-5" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{why ?? description}</p>
          {when && (
            <p className="mt-2 text-xs text-muted-foreground">
              <span className="font-semibold text-foreground">When: </span>
              {when}
            </p>
          )}
          {bullets && bullets.length > 0 && (
            <>
              <p className="text-overline mt-4 mb-2 text-muted-foreground">Coming here</p>
              <ul className="space-y-1.5 text-sm">
                {bullets.map((b) => (
                  <li key={b} className="flex gap-2">
                    <span aria-hidden className="mt-[7px] size-1.5 shrink-0 rounded-full bg-brand" />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {action && (
            <Link
              href={action.href}
              className="mt-4 inline-flex h-9 items-center gap-1 rounded-[10px] px-0 text-sm font-medium text-brand underline-offset-4 hover:underline"
            >
              {action.label} <span aria-hidden>→</span>
            </Link>
          )}
        </div>
      </div>
    </section>
  );
}
