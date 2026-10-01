"use client";

import { ArrowLeftRight } from "lucide-react";
import { useState } from "react";

import { RowsSkeleton } from "@/components/loaders/page-skeletons";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getTeam } from "@/lib/tokens";
import { cn } from "@/lib/utils";

import { longDate } from "../format";
import { useHeadToHead } from "../queries";
import type { HeadToHead, TeamRef, TeamSummary, TeamTotalRecord } from "../types";
import { replaceQuery } from "../url";
import { ErrorState, StatusPill } from "./states";

const ALL = "all";


/** Split bar in team colours (accent use), with both counts printed (§4.6). */
export function SplitBar({ a, b, h }: { a: TeamRef; b: TeamRef; h: Pick<HeadToHead, "team_a_won" | "team_b_won" | "no_result" | "played"> }) {
  const total = Math.max(1, h.team_a_won + h.team_b_won + h.no_result);
  const ca = getTeam(a.short_code).primary;
  const cb = getTeam(b.short_code).primary;
  return (
    <div>
      <div className="num flex items-end justify-between gap-2">
        <span className="flex items-center gap-2">
          <TeamBadge team={a.short_code} size="md" />
          <span className="font-condensed text-[2rem] leading-none font-bold">{h.team_a_won}</span>
        </span>
        <span className="text-overline pb-1 text-muted-foreground">
          {h.played} played{h.no_result ? ` · ${h.no_result} NR` : ""}
        </span>
        <span className="flex items-center gap-2">
          <span className="font-condensed text-[2rem] leading-none font-bold">{h.team_b_won}</span>
          <TeamBadge team={b.short_code} size="md" opponent={a.short_code} side="away" />
        </span>
      </div>
      <div
        role="img"
        aria-label={`${a.name} ${h.team_a_won} wins, ${b.name} ${h.team_b_won} wins${h.no_result ? `, ${h.no_result} no result` : ""}`}
        className="mt-3 flex h-2.5 gap-0.5 overflow-hidden rounded-full bg-surface-3"
      >
        <span style={{ width: `${(h.team_a_won / total) * 100}%`, backgroundColor: ca }} />
        {h.no_result > 0 && <span className="bg-surface-3" style={{ width: `${(h.no_result / total) * 100}%` }} />}
        <span
          className="bg-[repeating-linear-gradient(135deg,var(--away)_0_4px,color-mix(in_oklch,var(--away)_60%,transparent)_4px_7px)]"
          style={{ width: `${(h.team_b_won / total) * 100}%`, ["--away" as string]: cb }}
        />
      </div>
    </div>
  );
}

function TotalLine({ label, r }: { label: string; r: TeamTotalRecord | null }) {
  return (
    <div className="flex items-baseline justify-between gap-2 py-1.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="num text-right text-sm">
        {r ? (
          <>
            <span className="font-semibold">
              {r.runs}/{r.wickets}
            </span>{" "}
            <span className="text-muted-foreground">
              ({r.overs} ov) · {r.season}
              {r.venue ? ` · ${r.venue.city ?? r.venue.name}` : ""}
            </span>
          </>
        ) : (
          <span className="text-faint">–</span>
        )}
      </dd>
    </div>
  );
}

export function H2HResult({ h }: { h: HeadToHead }) {
  const a = h.team_a;
  const b = h.team_b;
  return (
    <div className="grid gap-4">
      <section className="rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4" aria-label="Head-to-head record">
        <SplitBar a={a} b={b} h={h} />
        {h.tied > 0 && <p className="mt-2 text-xs text-muted-foreground">{h.tied} tie(s) settled by super over, included in the wins.</p>}
      </section>

      <section className="rounded-xl border border-border bg-card shadow-e1" aria-labelledby="last5-h">
        <h3 id="last5-h" className="text-overline px-3 pt-3 text-muted-foreground md:px-4">
          Last {h.last5.length}
        </h3>
        {h.last5.length === 0 ? (
          <p className="px-4 py-3 text-sm text-muted-foreground">No meetings for this filter.</p>
        ) : (
          <ol className="mt-1 divide-y divide-border">
            {h.last5.map((m) => {
              const winner = m.winner_id === a.id ? a : m.winner_id === b.id ? b : null;
              return (
                <li key={m.match_id} className="flex min-h-[52px] items-center gap-3 px-3 py-1.5 md:px-4">
                  {winner ? <TeamBadge team={winner.short_code} /> : <StatusPill tone="muted">NR</StatusPill>}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm">{m.result_text}</p>
                    <p className="num truncate text-xs text-muted-foreground">
                      {longDate(m.date)}
                      {m.venue ? ` · ${m.venue.name}` : ""}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </section>

      <section className="rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4" aria-labelledby="totals-h">
        <h3 id="totals-h" className="text-overline mb-1 text-muted-foreground">
          Highest & lowest totals
        </h3>
        <dl className="divide-y divide-border">
          <TotalLine label={`${a.short_code} highest`} r={h.team_a_highest} />
          <TotalLine label={`${b.short_code} highest`} r={h.team_b_highest} />
          <TotalLine label={`${a.short_code} lowest`} r={h.team_a_lowest} />
          <TotalLine label={`${b.short_code} lowest`} r={h.team_b_lowest} />
        </dl>
      </section>

      {h.by_venue.length > 0 && (
        <section className="overflow-hidden rounded-xl border border-border bg-card shadow-e1" aria-labelledby="venues-h">
          <h3 id="venues-h" className="text-overline px-3 pt-3 text-muted-foreground md:px-4">
            By venue
          </h3>
          <div className="mt-2 max-h-80 overflow-auto">
            <table className="num w-full text-[13px]">
              <caption className="sr-only">Head-to-head by venue</caption>
              <thead>
                <tr className="text-overline text-muted-foreground">
                  <th scope="col" className="sticky top-0 bg-surface-2 px-3 py-2 text-left md:px-4">Venue</th>
                  <th scope="col" className="sticky top-0 bg-surface-2 px-2 py-2 text-right">P</th>
                  <th scope="col" className="sticky top-0 bg-surface-2 px-2 py-2 text-right">{a.short_code}</th>
                  <th scope="col" className="sticky top-0 bg-surface-2 px-3 py-2 text-right md:px-4">{b.short_code}</th>
                </tr>
              </thead>
              <tbody>
                {h.by_venue.map((v) => (
                  <tr key={v.venue.id} className="border-t border-border">
                    <td className="max-w-[12rem] truncate px-3 py-2 md:px-4" title={v.venue.name}>
                      {v.venue.name}
                      {v.venue.city && <span className="text-muted-foreground"> · {v.venue.city}</span>}
                    </td>
                    <td className="px-2 text-right">{v.played}</td>
                    <td className={cn("px-2 text-right", v.team_a_won > v.team_b_won && "font-semibold")}>{v.team_a_won}</td>
                    <td className={cn("px-3 text-right md:px-4", v.team_b_won > v.team_a_won && "font-semibold")}>{v.team_b_won}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

/** Team-vs-team picker for the team page: opponent + venue filter → /teams/{a}/vs/{b}. */
export function TeamH2H({
  team,
  teams,
  initialVs,
  initialVenue,
}: {
  team: TeamSummary;
  teams: TeamSummary[];
  initialVs: string | null;
  initialVenue: number | null;
}) {
  const opponents = teams
    .filter((t) => t.id !== team.id && t.seasons.some((s) => team.seasons.includes(s)))
    .sort((x, y) => Number(y.active) - Number(x.active) || x.name.localeCompare(y.name));
  const fallback = opponents.find((t) => t.active)?.short_code ?? opponents[0]?.short_code ?? null;
  const [vs, setVs] = useState<string | null>(
    initialVs && opponents.some((o) => o.short_code === initialVs.toUpperCase()) ? initialVs.toUpperCase() : fallback,
  );
  const [venue, setVenue] = useState<number | null>(initialVenue);

  const overall = useHeadToHead(team.short_code, vs, null); // venue list stays stable under the filter
  const q = useHeadToHead(team.short_code, vs, venue);

  const oppItems = opponents.map((o) => ({ value: o.short_code, label: `${o.name}${o.active ? "" : " (former)"}` }));
  const venueItems = [
    { value: ALL, label: "All venues" },
    ...(overall.data?.by_venue ?? []).map((v) => ({ value: String(v.venue.id), label: `${v.venue.name} (${v.played})` })),
  ];

  if (!opponents.length)
    return <EmptyState icon={ArrowLeftRight} title="No opponents to compare" why={`${team.name} never shared a season with another team in the data.`} />;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="flex items-center gap-2 text-sm font-medium">
          <TeamBadge team={team.short_code} size="md" /> <span className="text-muted-foreground">vs</span>
        </span>
        <Select
          items={oppItems}
          value={vs}
          onValueChange={(v) => {
            if (!v) return;
            setVs(v);
            setVenue(null);
            replaceQuery({ vs: v, venue: null });
          }}
        >
          <SelectTrigger aria-label="Opponent" className="h-10 min-w-44 rounded-[10px] bg-card">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {oppItems.map((i) => (
              <SelectItem key={i.value} value={i.value}>
                <TeamBadge team={i.value} /> {i.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          items={venueItems}
          value={venue ? String(venue) : ALL}
          onValueChange={(v) => {
            const id = v && v !== ALL ? Number(v) : null;
            setVenue(id);
            replaceQuery({ venue: id ? String(id) : null });
          }}
        >
          <SelectTrigger aria-label="Venue filter" className="h-10 max-w-full min-w-36 rounded-[10px] bg-card" disabled={!overall.data}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {venueItems.map((i) => (
              <SelectItem key={i.value} value={i.value}>
                {i.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {q.isPending ? (
        <div role="status" aria-busy="true" aria-label="Loading head-to-head" className="grid gap-4">
          <RowsSkeleton rows={2} />
          <RowsSkeleton rows={5} />
        </div>
      ) : q.isError ? (
        <ErrorState title="Couldn't load the head-to-head" error={q.error} onRetry={() => q.refetch()} />
      ) : q.data.played === 0 ? (
        <EmptyState
          compact
          icon={ArrowLeftRight}
          title="They've never met here"
          why="No completed match between these teams for this filter."
          when="Clear the venue filter to see every meeting."
        />
      ) : (
        <div className={cn(q.isPlaceholderData && "opacity-70 transition-opacity")}>
          <H2HResult h={q.data} />
        </div>
      )}
    </div>
  );
}
