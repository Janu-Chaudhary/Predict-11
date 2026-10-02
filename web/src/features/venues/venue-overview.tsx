import Link from "next/link";

import { StatTile } from "@/components/data/stat-tile";
import { cn } from "@/lib/utils";

import { fmtInt, fmtPct, fmtRuns, isNum, shortVenueName } from "./format";
import type { VenueSummary } from "./types";

/**
 * Venue list overview (derived only from GET /venues): a KPI row and two ranked side-rail
 * ladders. Rankings only use grounds with at least `minMatches` recent games so a two-match
 * sample can never top a ladder.
 */

type Ranked = { v: VenueSummary; value: number };

function ranked(venues: VenueSummary[], pick: (v: VenueSummary) => number | null, minMatches: number): Ranked[] {
  return venues
    .filter((v) => v.matches_recent >= minMatches)
    .flatMap((v) => {
      const value = pick(v);
      return isNum(value) ? [{ v, value }] : [];
    })
    .sort((a, b) => b.value - a.value);
}

export function VenueKpis({ venues, recentFrom, minMatches }: { venues: VenueSummary[]; recentFrom: number; minMatches: number }) {
  const active = venues.filter((v) => v.matches_recent > 0);
  const par = ranked(venues, (v) => v.par_recent, minMatches);
  const chase = ranked(venues, (v) => v.chase_win_pct_recent, minMatches);
  const games = active.reduce((s, v) => s + v.matches_recent, 0);
  const weighted = active.filter((v) => isNum(v.par_recent));
  const wSum = weighted.reduce((s, v) => s + v.matches_recent, 0);
  const avgPar = wSum > 0 ? weighted.reduce((s, v) => s + (v.par_recent as number) * v.matches_recent, 0) / wSum : null;
  const hi = par[0];
  const lo = par.at(-1);
  const ch = chase[0];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-4 xl:grid-cols-5">
      <StatTile label={`Grounds used ${recentFrom}+`} value={active.length} hint={<>{fmtInt(games)} matches · {venues.length} all-time</>} />
      <StatTile label={`League par ${recentFrom}+`} value={isNum(avgPar) ? Math.round(avgPar) : null} hint="1st innings, weighted by matches" />
      <StatTile label="Highest par" value={hi ? fmtRuns(hi.value) : null} hint={hi ? shortVenueName(hi.v.name) : undefined} href={hi ? `/venues/${hi.v.id}` : undefined} />
      <StatTile label="Lowest par" value={lo ? fmtRuns(lo.value) : null} hint={lo ? shortVenueName(lo.v.name) : undefined} href={lo ? `/venues/${lo.v.id}` : undefined} />
      <StatTile
        label="Best for chasing"
        value={ch ? fmtPct(ch.value) : null}
        hint={ch ? shortVenueName(ch.v.name) : undefined}
        href={ch ? `/venues/${ch.v.id}` : undefined}
        className="col-span-2 md:col-span-1"
      />
    </div>
  );
}

function Ladder({
  id,
  title,
  note,
  rows,
  format,
  scale,
  centre,
}: {
  id: string;
  title: string;
  note: string;
  rows: Ranked[];
  format: (n: number) => string;
  /** [min, max] of the bar axis. */
  scale: [number, number];
  /** Optional reference line (e.g. 50% for chase win). */
  centre?: number;
}) {
  const [lo, hi] = scale;
  const pct = (n: number) => Math.max(2, Math.min(100, ((n - lo) / (hi - lo)) * 100));
  return (
    <section aria-labelledby={id} className="min-w-0 rounded-xl border border-border bg-card p-4 shadow-e1">
      <header className="mb-3">
        <h2 id={id} className="text-overline text-muted-foreground">
          {title}
        </h2>
        <p className="mt-0.5 text-xs text-muted-foreground">{note}</p>
      </header>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">Not enough recent matches to rank.</p>
      ) : (
        <ol className="grid grid-cols-[minmax(0,1fr)] gap-2.5">
          {rows.map(({ v, value }, i) => (
            <li key={v.id}>
              <Link href={`/venues/${v.id}`} className="group block rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <div className="flex items-baseline gap-2 text-sm">
                  <span className="num w-4 shrink-0 text-xs text-muted-foreground">{i + 1}</span>
                  <span className="min-w-0 flex-1 truncate group-hover:underline">{shortVenueName(v.name)}</span>
                  <span className="num shrink-0 font-semibold">{format(value)}</span>
                </div>
                <div aria-hidden className="relative mt-1 ml-6 h-1.5 overflow-hidden rounded-full bg-surface-3">
                  <div
                    className={cn("h-full rounded-full", centre === undefined ? "bg-chart-1" : value >= centre ? "bg-positive" : "bg-chart-5")}
                    style={{ width: `${pct(value)}%` }}
                  />
                  {centre !== undefined && <span className="absolute inset-y-0 w-px bg-foreground/50" style={{ left: `${pct(centre)}%` }} />}
                </div>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export function VenueRail({ venues, recentFrom, minMatches }: { venues: VenueSummary[]; recentFrom: number; minMatches: number }) {
  const par = ranked(venues, (v) => v.par_recent, minMatches);
  const chase = ranked(venues, (v) => v.chase_win_pct_recent, minMatches);
  const parVals = par.map((r) => r.value);
  const parScale: [number, number] = parVals.length ? [Math.floor(Math.min(...parVals) / 10) * 10 - 10, Math.ceil(Math.max(...parVals) / 10) * 10] : [0, 1];
  return (
    <div className="grid content-start gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-1">
      <Ladder
        id="par-ladder"
        title={`Par ladder ${recentFrom}+`}
        note={`Average first-innings score, grounds with ${minMatches}+ matches since ${recentFrom}.`}
        rows={par}
        format={(n) => fmtRuns(n)}
        scale={parScale}
      />
      <Ladder
        id="chase-ladder"
        title={`Chase win ${recentFrom}+`}
        note={`Share of results won by the chasing side. Line marks 50%.`}
        rows={chase}
        format={(n) => fmtPct(n)}
        scale={[0, 100]}
        centre={50}
      />
    </div>
  );
}
