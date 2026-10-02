"use client";

import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";

import { fmt } from "../format";
import { typeLabel, useBatterVsTypes, useBowlerVsHands } from "../matchups";
import type { PlayerProfile } from "../types";
import { MetricBar, Panel } from "../ui";

/**
 * Overview side-rail card: pace v spin (batters) or right- v left-handers (bowlers), with a link
 * to the full tables on the Splits tab. Quietly hides itself on error; the Splits tab shows it.
 */
export function MatchupSummary({ p, skill, splitsHref }: { p: PlayerProfile; skill: "bat" | "bowl"; splitsHref: string }) {
  const since = p.filters.since ?? undefined;
  const season = p.filters.season ?? undefined;
  const bat = useBatterVsTypes(p.id, since, skill === "bat" && p.batting.balls > 0, season);
  const bowl = useBowlerVsHands(p.id, since, skill === "bowl" && p.bowling.balls > 0, season);
  const q = skill === "bat" ? bat : bowl;
  if ((skill === "bat" ? p.batting.balls : p.bowling.balls) === 0 || q.isError) return null;

  const more = (
    <Link href={splitsHref} className="rounded text-xs font-medium text-brand outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
      All splits →
    </Link>
  );

  if (q.isPending || !q.data) {
    return (
      <Panel title={skill === "bat" ? "Pace v spin" : "V batting hands"} action={more}>
        <div role="status" aria-busy="true" aria-label="Loading matchup splits" className="grid gap-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-24" />
        </div>
      </Panel>
    );
  }

  if (skill === "bat" && bat.data) {
    const d = bat.data;
    const types = [...d.by_type].sort((a, b) => b.balls - a.balls).slice(0, 5);
    const max = Math.max(200, ...types.map((t) => t.strike_rate ?? 0));
    if (d.by_group.length === 0) return null;
    return (
      <Panel title="Pace v spin" action={more}>
        <dl className="num grid grid-cols-2 gap-2">
          {d.by_group.map((g) => (
            <div key={g.bowling_type} className="rounded-lg bg-surface-2/60 p-3">
              <dt className="text-overline text-muted-foreground">v {g.bowling_type}</dt>
              <dd className="font-condensed text-[1.75rem] leading-8 font-bold">
                {fmt(g.strike_rate, 1)} <span className="font-sans text-xs font-normal text-muted-foreground">SR</span>
              </dd>
              <dd className="text-xs text-muted-foreground">
                {g.dismissals} outs · avg {fmt(g.average, 1)}
              </dd>
            </div>
          ))}
        </dl>
        <h3 className="text-overline mt-4 mb-1 text-muted-foreground">Strike rate by bowling type · most faced</h3>
        <div role="list" aria-label="Strike rate against the most-faced bowling types">
          {types.map((t) => (
            <div role="listitem" key={t.bowling_type}>
              <MetricBar label={typeLabel(t.bowling_type)} value={t.strike_rate} max={max} display={fmt(t.strike_rate, 1)} hint={`${fmt(t.runs)} off ${fmt(t.balls)} · ${t.dismissals} outs`} />
            </div>
          ))}
        </div>
      </Panel>
    );
  }

  const d = bowl.data;
  if (!d || d.by_hand.length === 0) return null;
  const max = Math.max(12, ...d.by_hand.map((h) => h.economy ?? 0));
  return (
    <Panel title={`V batting hands${d.bowling_type ? ` · ${d.bowling_type}` : ""}`} action={more}>
      <dl className="num grid grid-cols-2 gap-2">
        {d.by_hand.map((h) => (
          <div key={h.hand} className="rounded-lg bg-surface-2/60 p-3">
            <dt className="text-overline text-muted-foreground">v {h.hand === "L" ? "left" : "right"}-handers</dt>
            <dd className="font-condensed text-[1.75rem] leading-8 font-bold">
              {h.wickets} <span className="font-sans text-xs font-normal text-muted-foreground">wkts</span>
            </dd>
            <dd className="text-xs text-muted-foreground">
              SR {fmt(h.strike_rate, 1)} · avg {fmt(h.average, 1)}
            </dd>
          </div>
        ))}
      </dl>
      <h3 className="text-overline mt-4 mb-1 text-muted-foreground">Economy (lower is better)</h3>
      <div role="list" aria-label="Economy against right- and left-handed batters">
        {d.by_hand.map((h) => (
          <div role="listitem" key={h.hand}>
            <MetricBar label={h.hand === "L" ? "Left-handers" : "Right-handers"} value={h.economy} max={max} tone="primary" display={fmt(h.economy, 2)} hint={`${fmt(h.balls)} balls · dot ${fmt(h.dot_pct, 1)}%`} />
          </div>
        ))}
      </div>
    </Panel>
  );
}
