import Link from "next/link";
import { Fragment } from "react";

import { TeamBadge } from "@/components/player/team-badge";
import { cn } from "@/lib/utils";

import { fmt, teamCode } from "../format";
import type { CompareEntry } from "../types";
import { rowBest, visibleRows } from "./metrics";

/**
 * Side-by-side metric rows (FotMob-style comparison). The best value in each row is bold with a
 * gold tint and a ▲ marker plus screen-reader text, so colour is never the only cue.
 * Rates only compete above a minimum sample (see metrics.ts).
 */
export function CompareTable({ players, caption }: { players: CompareEntry[]; caption: string }) {
  const rows = visibleRows(players);
  const groups = [...new Set(rows.map((r) => r.group))];
  return (
    <div className="w-full min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-e1">
      <div className="relative overflow-x-auto overscroll-x-contain" role="region" aria-label={caption} tabIndex={0}>
        <table className="num w-full min-w-[22rem] border-separate border-spacing-0 text-[13px] leading-[18px] md:text-sm md:leading-5">
          <caption className="sr-only">{caption}. The best value in each row is marked “best”.</caption>
          <thead>
            <tr>
              <th scope="col" className="text-overline sticky left-0 z-20 h-12 w-[7.5rem] border-b border-border bg-surface-2 px-3 text-left text-muted-foreground sm:w-48 sm:px-4">
                Metric
              </th>
              {players.map((p) => (
                <th key={p.id} scope="col" className="h-12 border-b border-border bg-surface-2 px-3 text-right align-middle">
                  <Link
                    href={`/players/${encodeURIComponent(p.id)}`}
                    className="inline-flex max-w-[9rem] items-center justify-end gap-1.5 rounded font-semibold outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring sm:max-w-none"
                  >
                    {p.last_team && <TeamBadge team={teamCode(p.last_team) ?? ""} className="max-sm:hidden" />}
                    <span className="truncate">{p.name}</span>
                  </Link>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <Fragment key={g}>
                <tr>
                  <th scope="rowgroup" colSpan={players.length + 1} className="text-overline sticky left-0 h-8 border-b border-border bg-card px-3 pt-3 text-left text-brand sm:px-4">
                    {g}
                  </th>
                </tr>
                {rows
                  .filter((r) => r.group === g)
                  .map((r) => {
                    const best = rowBest(r, players);
                    return (
                      <tr key={r.key} className="group/row" data-row={r.key}>
                        <th scope="row" className="sticky left-0 z-10 h-9 border-b border-border bg-card px-3 text-left font-normal whitespace-nowrap text-muted-foreground group-hover/row:bg-surface-2 sm:px-4">
                          {r.label}
                          {r.better === "low" && <span className="ml-1 text-[11px] text-faint">(lower better)</span>}
                        </th>
                        {players.map((p, i) => {
                          const isBest = best.includes(i);
                          const v = r.value(p);
                          const text = r.display ? r.display(p) : fmt(v);
                          return (
                            <td
                              key={p.id}
                              data-best={isBest || undefined}
                              className={cn(
                                "h-9 border-b border-border bg-card px-3 text-right whitespace-nowrap group-hover/row:bg-surface-2",
                                isBest && "bg-primary/10 font-semibold text-foreground group-hover/row:bg-primary/15",
                              )}
                            >
                              {isBest && (
                                <span aria-hidden className="mr-1 text-[11px] text-gold-text">
                                  ▲
                                </span>
                              )}
                              {text}
                              {isBest && <span className="sr-only"> (best)</span>}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border-t border-border px-4 py-2.5 text-xs text-muted-foreground">
        <span aria-hidden className="text-gold-text">▲</span> best in row. Rates compete only with ≥30 balls (≥5 innings for batting average, ≥3 wickets for bowling average / SR).
      </p>
    </div>
  );
}
