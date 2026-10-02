import { Trophy } from "lucide-react";
import Link from "next/link";
import { Fragment } from "react";

import { FormStrip } from "@/components/data/form-strip";
import { cn } from "@/lib/utils";

import { formatNrr, formToResult, nrrTone } from "../format";
import type { PlayoffResult, PointsRow } from "../types";
import { TeamName } from "./states";

export const PLAYOFF_SPOTS = 4;
const ZONE_KEY_ID = "points-zone-key";

type Zone = "q1" | "elim" | null;
export function zoneFor(position: number): Zone {
  if (position <= 2) return "q1";
  if (position <= PLAYOFF_SPOTS) return "elim";
  return null;
}

const ZONE: Record<Exclude<Zone, null>, { cls: string; label: string }> = {
  q1: { cls: "bg-primary", label: "Qualifier 1 (top 2)" },
  elim: { cls: "bg-brand", label: "Eliminator (3rd–4th)" },
};

const TH = "text-overline sticky top-0 z-10 h-11 border-b border-border bg-surface-2 px-2 whitespace-nowrap text-muted-foreground";
const TD = "h-12 border-b border-border bg-card px-3 whitespace-nowrap lg:h-14";

/**
 * Points table (§4.7): zone stripe (gold top 2, violet 3–4) with a key, sticky header and team
 * column, right-aligned tabular numbers, signed + coloured NRR, last-5 form, and a labelled
 * playoff line after 4th. Scrolls horizontally inside its card, never the page.
 */
export function PointsTableView({
  rows,
  caption,
  highlightTeamId,
  className,
}: {
  rows: PointsRow[];
  caption: string;
  highlightTeamId?: number;
  className?: string;
}) {
  const hasPlayoffs = rows.some((r) => (r.playoffs?.length ?? 0) > 0);
  return (
    <div className={cn("overflow-hidden rounded-xl border border-border bg-card shadow-e1", className)}>
      <div className="overflow-x-auto overscroll-x-contain" role="region" aria-label={caption} tabIndex={0}>
        <table className="num w-full border-separate border-spacing-0 text-sm leading-5 lg:text-base lg:leading-6" aria-describedby={ZONE_KEY_ID}>
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              <th scope="col" className={cn(TH, "sticky left-0 z-20 w-9 pl-4 text-left")}>
                <abbr title="Position" className="no-underline">#</abbr>
              </th>
              <th scope="col" className={cn(TH, "sticky left-9 z-20 text-left")}>Team</th>
              <th scope="col" className={cn(TH, "text-right")}><abbr title="Played" className="no-underline">P</abbr></th>
              <th scope="col" className={cn(TH, "text-right")}><abbr title="Won" className="no-underline">W</abbr></th>
              <th scope="col" className={cn(TH, "text-right")}><abbr title="Lost" className="no-underline">L</abbr></th>
              <th scope="col" className={cn(TH, "text-right max-sm:hidden")}><abbr title="No result" className="no-underline">NR</abbr></th>
              <th scope="col" className={cn(TH, "text-right")}><abbr title="Net run rate" className="no-underline">NRR</abbr></th>
              <th scope="col" className={cn(TH, "text-right")}><abbr title="Points" className="no-underline">Pts</abbr></th>
              <th scope="col" className={cn(TH, "text-left")}>Form</th>
              {hasPlayoffs && <th scope="col" className={cn(TH, "pr-4 text-left")}>Playoffs</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const zone = zoneFor(r.position);
              const tone = nrrTone(r.nrr);
              const hl = r.team.id === highlightTeamId;
              return (
                <Fragment key={r.team.id}>
                  <tr className={cn("group/row", hl && "[&>td]:bg-surface-2")} data-zone={zone ?? undefined} aria-current={hl ? "true" : undefined}>
                    <td className={cn(TD, "sticky left-0 z-[5] w-9 pl-4 text-left font-medium text-muted-foreground group-hover/row:bg-surface-2")}>
                      {zone && <span aria-hidden className={cn("absolute inset-y-1.5 left-0 w-[3px] rounded-r-full", ZONE[zone].cls)} />}
                      <span>{r.position}</span>
                      {zone && <span className="sr-only">, {ZONE[zone].label}</span>}
                    </td>
                    <td className={cn(TD, "sticky left-9 z-[5] max-w-[16rem] text-left group-hover/row:bg-surface-2 md:max-w-none")}>
                      <span className="inline-flex items-center gap-2">
                        <TeamName team={r.team} />
                        {r.finish === "champion" && (
                          <span title="Champions" className="text-gold-text inline-flex items-center gap-1 text-xs font-semibold">
                            <Trophy aria-hidden className="size-4" />
                            <span className="max-md:sr-only">Champions</span>
                          </span>
                        )}
                        {r.finish === "runner_up" && <span className="text-xs text-muted-foreground max-md:sr-only">Runner-up</span>}
                      </span>
                    </td>
                    <td className={cn(TD, "text-right group-hover/row:bg-surface-2")}>{r.played}</td>
                    <td className={cn(TD, "text-right group-hover/row:bg-surface-2")}>{r.won}</td>
                    <td className={cn(TD, "text-right group-hover/row:bg-surface-2")}>{r.lost}</td>
                    <td className={cn(TD, "text-right text-muted-foreground group-hover/row:bg-surface-2 max-sm:hidden")}>{r.no_result}</td>
                    <td
                      className={cn(
                        TD,
                        "text-right group-hover/row:bg-surface-2",
                        tone === "positive" && "text-positive",
                        tone === "negative" && "text-negative",
                      )}
                      title={`${r.runs_for}/${r.overs_for} ov for · ${r.runs_against}/${r.overs_against} ov against`}
                    >
                      {formatNrr(r.nrr)}
                    </td>
                    <td className={cn(TD, "text-right font-semibold group-hover/row:bg-surface-2")}>{r.points}</td>
                    <td className={cn(TD, "text-left group-hover/row:bg-surface-2", !hasPlayoffs && "pr-4")}>
                      {r.form.length ? <FormStrip results={r.form.map(formToResult)} /> : <span className="text-faint">–</span>}
                    </td>
                    {hasPlayoffs && (
                      <td className={cn(TD, "pr-4 text-left group-hover/row:bg-surface-2")}>
                        {r.playoffs?.length ? <PlayoffStrip games={r.playoffs} /> : <span className="text-faint">–</span>}
                      </td>
                    )}
                  </tr>
                  {r.position === PLAYOFF_SPOTS && rows.length > PLAYOFF_SPOTS && (
                    <tr aria-hidden data-testid="playoff-line">
                      <td colSpan={hasPlayoffs ? 10 : 9} className="h-0 p-0">
                        <div className="h-px bg-[repeating-linear-gradient(90deg,var(--brand)_0_6px,transparent_6px_10px)]" />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <ZoneKey />
    </div>
  );
}

const PO_TONE = { W: "bg-positive/18 text-positive ring-positive/35", L: "bg-negative/15 text-negative ring-negative/35", N: "bg-surface-3 text-muted-foreground ring-border" } as const;

/** Playoff results after the league stage: stage code + W/L, linking to the match. */
function PlayoffStrip({ games }: { games: PlayoffResult[] }) {
  return (
    <ol className="inline-flex items-center gap-1" aria-label={games.map((g) => `${g.stage}: ${g.result === "W" ? "won" : g.result === "L" ? "lost" : "no result"} v ${g.opponent.name}`).join(", ")}>
      {games.map((g) => (
        <li key={g.match_id}>
          <Link
            href={`/matches/${g.match_id}`}
            title={`${g.stage} v ${g.opponent.short_code}`}
            className={cn("font-condensed flex h-6 items-center gap-0.5 rounded-full px-2 text-[11px] font-bold ring-1 ring-inset outline-none focus-visible:ring-2 focus-visible:ring-ring", PO_TONE[g.result])}
          >
            <span className="opacity-75">{g.code}</span> {g.result === "N" ? "–" : g.result}
          </Link>
        </li>
      ))}
    </ol>
  );
}

export function ZoneKey() {
  return (
    <p id={ZONE_KEY_ID} className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border px-4 py-2.5 text-xs text-muted-foreground">
      <span className="sr-only">Zone key:</span>
      {Object.values(ZONE).map((z) => (
        <span key={z.label} className="inline-flex items-center gap-1.5">
          <span aria-hidden className={cn("h-3 w-[3px] rounded-full", z.cls)} />
          {z.label}
        </span>
      ))}
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="w-4 border-t border-dashed border-brand" />
        Playoff line
      </span>
    </p>
  );
}
