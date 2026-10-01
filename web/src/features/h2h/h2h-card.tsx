import { ConfidenceBadge } from "@/components/data/confidence-badge";
import { cn } from "@/lib/utils";

import { PlayerAvatar } from "@/components/player/player-avatar";

import { displayName, fmt, fmtDate, photoOf } from "../players/format";
import type { PlayerRef } from "../players/types";
import { H2H_THRESHOLDS, resolveConfidence } from "./confidence";
import type { PairStats } from "./types";

/** "caught 3 · lbw 2" style list, most common first. */
export function howOutList(howOut: Record<string, number>): { kind: string; n: number }[] {
  return Object.entries(howOut)
    .map(([kind, n]) => ({ kind, n }))
    .filter((x) => x.n > 0)
    .sort((a, b) => b.n - a.n || a.kind.localeCompare(b.kind));
}

/**
 * Batter v bowler result card (D1): headline balls / runs / outs / SR, secondary dot%, boundary%,
 * 4s/6s, dismissal types, a ball-count confidence badge, by-season table and last encounters.
 */
export function H2HCard({ batter, bowler, pair }: { batter: PlayerRef; bowler: PlayerRef; pair: PairStats }) {
  const level = resolveConfidence(pair.confidence, pair.balls);
  const outs = howOutList(pair.how_out);
  const low = level === "low";
  const bat = displayName(batter);
  const bowl = displayName(bowler);
  return (
    <article aria-labelledby="h2h-title" className="min-w-0 rounded-xl border border-border bg-card shadow-e1">
      <header className="flex flex-wrap items-start justify-between gap-2 border-b border-border px-3 py-3 md:px-4">
        <div className="flex min-w-0 items-center gap-3">
          <span aria-hidden className="flex shrink-0 -space-x-2">
            <PlayerAvatar name={bat} src={photoOf(batter)} size="md" className="ring-2 ring-card" />
            <PlayerAvatar name={bowl} src={photoOf(bowler)} size="md" className="ring-2 ring-card" />
          </span>
          <div className="min-w-0">
          <p className="text-overline text-muted-foreground">Batter v bowler · IPL</p>
          <h2 id="h2h-title" className="text-title truncate">
            {bat} <span className="text-muted-foreground">v</span> {bowl}
          </h2>
          <p className="num text-xs text-muted-foreground">
            {pair.matches} matches · {pair.innings} innings
          </p>
          </div>
        </div>
        <ConfidenceBadge n={pair.balls} level={level} thresholds={H2H_THRESHOLDS} />
      </header>

      <div className={cn("p-3 md:p-4", low && "opacity-80")}>
        <dl className="grid grid-cols-4 gap-2 text-center">
          <Big label="Balls" value={fmt(pair.balls)} />
          <Big label="Runs" value={fmt(pair.runs)} />
          <Big label="Outs" value={fmt(pair.dismissals)} tone={pair.dismissals > 0 ? "negative" : undefined} />
          <Big label="SR" value={fmt(pair.strike_rate, 1)} />
        </dl>

        <dl className="num mt-3 grid grid-cols-3 gap-x-3 gap-y-2 rounded-lg bg-surface-2/60 p-3 text-sm sm:grid-cols-6">
          <Small label="Dot %" value={fmt(pair.dot_pct, 1)} />
          <Small label="Boundary %" value={fmt(pair.boundary_pct, 1)} />
          <Small label="4s" value={fmt(pair.fours)} />
          <Small label="6s" value={fmt(pair.sixes)} />
          <Small label="Average" value={fmt(pair.average, 1)} />
          <Small label="Balls / out" value={pair.dismissals ? fmt(pair.balls / pair.dismissals, 1) : "–"} />
        </dl>

        <div className="mt-3">
          <h3 className="text-overline mb-1.5 text-muted-foreground">How out</h3>
          {outs.length ? (
            <ul className="flex flex-wrap gap-1.5" aria-label="Dismissals by type">
              {outs.map((o) => (
                <li key={o.kind} className="num inline-flex h-7 items-center gap-1.5 rounded-full bg-negative/12 px-2.5 text-xs font-medium text-negative ring-1 ring-negative/30 ring-inset">
                  <span className="capitalize">{o.kind}</span>
                  <span className="font-bold">{o.n}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Never dismissed by {bowl}.</p>
          )}
        </div>

        {low && (
          <p className="mt-3 rounded-lg border border-warning/30 bg-warning/8 px-3 py-2 text-xs">
            <span className="font-semibold">Small sample.</span> Under 12 balls is anecdote, not evidence. Lean on each player’s phase and venue splits instead.
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 border-t border-border p-3 md:grid-cols-2 md:p-4">
        <section aria-labelledby="h2h-seasons-h" className="min-w-0">
          <h3 id="h2h-seasons-h" className="text-overline mb-2 text-muted-foreground">
            By season
          </h3>
          <div className="max-h-72 overflow-auto rounded-lg border border-border" role="region" aria-label="By-season breakdown" tabIndex={0}>
            <table className="num w-full border-separate border-spacing-0 text-[13px]">
              <caption className="sr-only">
                {bat} against {bowl} by season
              </caption>
              <thead>
                <tr>
                  {["Season", "Balls", "Runs", "Outs", "SR"].map((h, i) => (
                    <th key={h} scope="col" className={cn("text-overline sticky top-0 h-8 border-b border-border bg-surface-2 px-2.5 text-muted-foreground", i === 0 ? "text-left" : "text-right")}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...pair.by_season]
                  .sort((a, b) => b.season - a.season)
                  .map((s) => (
                    <tr key={s.season}>
                      <th scope="row" className="h-8 border-b border-border px-2.5 text-left font-medium">
                        {s.season}
                      </th>
                      <td className="border-b border-border px-2.5 text-right">{s.balls}</td>
                      <td className="border-b border-border px-2.5 text-right">{s.runs}</td>
                      <td className={cn("border-b border-border px-2.5 text-right", s.dismissals > 0 && "font-semibold text-negative")}>{s.dismissals}</td>
                      <td className="border-b border-border px-2.5 text-right">{fmt(s.strike_rate, 1)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="h2h-last-h" className="min-w-0">
          <h3 id="h2h-last-h" className="text-overline mb-2 text-muted-foreground">
            Last {pair.last_encounters.length} encounters
          </h3>
          <ol className="divide-y divide-border rounded-lg border border-border">
            {pair.last_encounters.map((e) => (
              <li key={`${e.match_id}`} className="flex min-h-11 items-center gap-3 px-2.5 py-1.5">
                <span className="min-w-0 flex-1">
                  <span className="num block text-sm">{fmtDate(e.date)}</span>
                  <span className="block truncate text-xs text-muted-foreground">{e.venue ?? "Venue unknown"}</span>
                </span>
                <span className="num text-right text-sm">
                  <span className="font-semibold">{e.runs}</span>
                  <span className="text-muted-foreground"> ({e.balls})</span>
                </span>
                <span
                  className={cn(
                    "inline-flex h-6 min-w-14 items-center justify-center rounded-full px-2 text-[11px] font-semibold ring-1 ring-inset",
                    e.out ? "bg-negative/12 text-negative ring-negative/30" : "bg-surface-2 text-muted-foreground ring-border",
                  )}
                >
                  {e.out ? <>W · {e.how_out ?? "out"}</> : "not out"}
                </span>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </article>
  );
}

function Big({ label, value, tone }: { label: string; value: string; tone?: "negative" }) {
  return (
    <div className="min-w-0 rounded-lg bg-surface-2/60 px-1 py-2">
      <dt className="text-overline text-muted-foreground">{label}</dt>
      <dd className={cn("font-condensed num text-[1.75rem] leading-8 font-bold md:text-[2.25rem] md:leading-10", tone === "negative" && "text-negative")}>{value}</dd>
    </div>
  );
}

function Small({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="truncate text-xs text-muted-foreground">{label}</dt>
      <dd className="font-semibold">{value}</dd>
    </div>
  );
}
