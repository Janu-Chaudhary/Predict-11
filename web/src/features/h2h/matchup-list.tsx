import Link from "next/link";

import { ConfidenceBadge } from "@/components/data/confidence-badge";
import { cn } from "@/lib/utils";

import { fmt } from "../players/format";
import { H2H_THRESHOLDS, resolveConfidence } from "./confidence";
import type { MatchupRow } from "./types";

/**
 * Discovery list: "toughest bowlers for this batter" / "batters who dominate this bowler".
 * Each row opens that pair in the H2H card.
 */
export function MatchupList({
  title,
  subtitle,
  rows,
  hrefFor,
  activeId,
  empty,
  className,
}: {
  title: string;
  subtitle?: string;
  rows: MatchupRow[];
  hrefFor: (row: MatchupRow) => string;
  activeId?: string;
  empty: string;
  className?: string;
}) {
  return (
    <section aria-label={title} className={cn("min-w-0 rounded-xl border border-border bg-card shadow-e1", className)}>
      <header className="px-3 pt-3 md:px-4">
        <h2 className="text-overline text-muted-foreground">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
      </header>
      {rows.length === 0 ? (
        <p className="px-3 py-4 text-sm text-muted-foreground md:px-4">{empty}</p>
      ) : (
        <ol className="mt-2 divide-y divide-border">
          {rows.map((r, i) => {
            const active = r.player.id === activeId;
            return (
              <li key={r.player.id}>
                <Link
                  href={hrefFor(r)}
                  scroll={false}
                  aria-current={active ? "true" : undefined}
                  className={cn(
                    "flex min-h-[52px] items-center gap-3 px-3 py-1.5 outline-none hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset md:px-4",
                    active && "bg-surface-2",
                  )}
                >
                  <span className="num w-5 shrink-0 text-right text-xs text-faint">{i + 1}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{r.player.name}</span>
                    <span className="num block truncate text-xs text-muted-foreground">
                      {r.runs} off {r.balls} · SR {fmt(r.strike_rate, 0)} · dot {fmt(r.dot_pct, 0)}%
                    </span>
                  </span>
                  <span className="flex shrink-0 flex-col items-end gap-1">
                    <span className="num text-sm font-semibold">
                      {r.dismissals} <span className="text-xs font-normal text-muted-foreground">out{r.dismissals === 1 ? "" : "s"}</span>
                    </span>
                    <ConfidenceBadge n={r.balls} level={resolveConfidence(r.confidence, r.balls)} thresholds={H2H_THRESHOLDS} showN={false} className="h-5" />
                  </span>
                </Link>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
