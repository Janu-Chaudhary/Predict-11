"use client";

import { ConfidenceBadge } from "@/components/data/confidence-badge";
import { RowsSkeleton } from "@/components/loaders/page-skeletons";
import { cn } from "@/lib/utils";

import { fmt } from "../players/format";
import { typeLabel, unknownNote, useBatterVsTypes, useBowlerVsHands } from "../players/matchups";
import { QueryError } from "../players/ui";
import { H2H_THRESHOLDS, resolveConfidence } from "./confidence";

/**
 * D2 fallback for sparse pairs (§4.6): how the selected batter fares against each bowling type.
 * When a bowler is picked too, their type is highlighted, since that row usually has far more
 * balls than the 1-v-1 sample.
 */
export function BowlingTypeCard({ batterId, batterName, bowlerId, bowlerName, since }: { batterId: string; batterName: string; bowlerId?: string; bowlerName?: string; since?: string }) {
  const q = useBatterVsTypes(batterId, since);
  const bowler = useBowlerVsHands(bowlerId, since);
  const bowlerType = bowler.data?.bowling_type ?? null;

  return (
    <section aria-labelledby="h2h-types-h" className="min-w-0 rounded-xl border border-border bg-card shadow-e1">
      <header className="px-3 pt-3 md:px-4">
        <h2 id="h2h-types-h" className="text-overline text-muted-foreground">
          {batterName} v bowling types
        </h2>
        <p className="mt-0.5 text-xs text-muted-foreground">Strike rate and outs against every bowler of each type{since ? ` since ${since}` : ""}.</p>
      </header>
      {q.isPending ? (
        <RowsSkeleton rows={5} className="p-3" />
      ) : q.isError ? (
        <QueryError error={q.error} onRetry={() => q.refetch()} what="bowling-type splits" className="m-3" />
      ) : q.data.by_type.length === 0 ? (
        <p className="px-3 py-4 text-sm text-muted-foreground md:px-4">No balls faced against bowlers of a known type.</p>
      ) : (
        <div className="p-3 md:p-4">
          <dl className="num mb-3 grid grid-cols-2 gap-2">
            {q.data.by_group.map((g) => (
              <div key={g.bowling_type} className="rounded-lg bg-surface-2/60 p-2.5">
                <dt className="text-overline text-muted-foreground">v {g.bowling_type}</dt>
                <dd className="font-condensed text-2xl leading-8 font-bold">
                  {fmt(g.strike_rate, 0)} <span className="font-sans text-xs font-normal text-muted-foreground">SR</span>
                </dd>
                <dd className="text-xs text-muted-foreground">
                  {fmt(g.runs)} off {fmt(g.balls)} · {g.dismissals} outs · avg {fmt(g.average, 1)}
                </dd>
              </div>
            ))}
          </dl>
          <ul className="divide-y divide-border" aria-label={`${batterName} by bowling type`}>
            {[...q.data.by_type]
              .sort((a, b) => b.balls - a.balls)
              .map((t) => {
                const hit = bowlerType === t.bowling_type;
                return (
                  <li key={t.bowling_type} className={cn("flex min-h-11 items-center gap-3 py-1.5", hit && "-mx-2 rounded-lg bg-primary/10 px-2")}>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">
                        {typeLabel(t.bowling_type)}
                        {hit && <span className="ml-1.5 text-[11px] font-semibold text-gold-text">{bowlerName ? `${bowlerName}’s type` : "bowler’s type"}</span>}
                      </span>
                      <span className="num block truncate text-xs text-muted-foreground">
                        {fmt(t.runs)} off {fmt(t.balls)} · {t.dismissals} out{t.dismissals === 1 ? "" : "s"} · dot {fmt(t.dot_pct, 0)}%
                      </span>
                    </span>
                    <span className="num w-14 text-right text-sm font-semibold">
                      {fmt(t.strike_rate, 0)}
                      <span className="block text-[11px] leading-4 font-normal text-muted-foreground">SR</span>
                    </span>
                    <ConfidenceBadge n={t.balls} level={resolveConfidence(t.confidence, t.balls)} thresholds={H2H_THRESHOLDS} showN={false} className="h-5" />
                  </li>
                );
              })}
          </ul>
          {unknownNote(q.data.coverage, "bowling type") && <p className="mt-2 text-xs text-muted-foreground">{unknownNote(q.data.coverage, "bowling type")}</p>}
        </div>
      )}
    </section>
  );
}
