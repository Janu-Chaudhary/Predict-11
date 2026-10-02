"use client";

import { Flame, Milestone, Trophy } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { TableSkeleton } from "@/components/loaders/page-skeletons";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

import { shortDate } from "../format";
import { useRecords, useVenueOptions } from "../queries";
import type {
  BattingInningsRecord,
  BattingLeader,
  BowlingFiguresRecord,
  BowlingLeader,
  FastestMilestone,
  MarginRecord,
  PartnershipRecord,
  PlayerRef,
  Records,
  TeamRef,
  TeamTotalRecord,
} from "../types";
import { replaceQuery } from "../url";
import { ErrorState } from "./states";
import { displayName } from "../../players/format";

const SEASON_OPTIONS = Array.from({ length: 2026 - 2008 + 1 }, (_, i) => 2026 - i);
const ALL = "all";


/* ---------- cells ---------- */

const Player = ({ p, team }: { p: PlayerRef; team?: TeamRef | null }) => (
  <span className="flex items-center gap-2">
    {team && <TeamBadge team={team.short_code} />}
    <Link href={`/players/${encodeURIComponent(p.id)}`} className="font-medium outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
      {displayName(p)}
    </Link>
  </span>
);
const Team = ({ t }: { t: TeamRef }) => (
  <Link href={`/teams/${encodeURIComponent(t.short_code)}`} className="inline-flex items-center gap-2 font-medium outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
    <TeamBadge team={t.short_code} />
    <span className="max-md:sr-only">{t.name}</span>
  </Link>
);
const Vs = ({ t }: { t: TeamRef }) => <span className="text-muted-foreground">v {t.short_code}</span>;
const When = ({ r }: { r: { season: number; date: string } }) => (
  <span className="text-muted-foreground" title={r.date}>
    {shortDate(r.date)} {r.season}
  </span>
);

/* ---------- column sets ---------- */

type Ranked<T> = T & { _rank: number };
const rank: StatColumn<Ranked<object>> = {
  key: "rank",
  header: "#",
  label: "Rank",
  value: (r) => r._rank,
  className: "w-8 text-muted-foreground",
  headerClassName: "w-8",
};
const col = <T,>(c: StatColumn<T>) => c;

const runsCols: StatColumn<Ranked<BattingLeader>>[] = [
  rank,
  col({ key: "p", header: "Player", align: "left", sticky: true, value: (r: BattingLeader) => displayName(r.player), cell: (r: BattingLeader) => <Player p={r.player} team={r.team} /> }),
  col({ key: "inn", header: "Inns", value: (r: BattingLeader) => r.innings, hideBelow: "sm" }),
  col({ key: "runs", header: "Runs", value: (r: BattingLeader) => r.runs, className: "font-semibold" }),
  col({ key: "sr", header: "SR", value: (r: BattingLeader) => r.strike_rate.toFixed(1) }),
];
const wktCols: StatColumn<Ranked<BowlingLeader>>[] = [
  rank,
  col({ key: "p", header: "Player", align: "left", sticky: true, value: (r: BowlingLeader) => displayName(r.player), cell: (r: BowlingLeader) => <Player p={r.player} team={r.team} /> }),
  col({ key: "inn", header: "Inns", value: (r: BowlingLeader) => r.innings, hideBelow: "sm" }),
  col({ key: "w", header: "Wkts", value: (r: BowlingLeader) => r.wickets, className: "font-semibold" }),
  col({ key: "econ", header: "Econ", value: (r: BowlingLeader) => r.economy.toFixed(2) }),
];
const totalCols: StatColumn<Ranked<TeamTotalRecord>>[] = [
  rank,
  col({ key: "t", header: "Team", align: "left", sticky: true, value: (r: TeamTotalRecord) => r.team.name, cell: (r: TeamTotalRecord) => <Team t={r.team} /> }),
  col({ key: "s", header: "Score", value: (r: TeamTotalRecord) => r.runs, cell: (r: TeamTotalRecord) => <span className="font-semibold">{r.runs}/{r.wickets}</span> }),
  col({ key: "o", header: "Ov", label: "Overs", value: (r: TeamTotalRecord) => r.overs }),
  col({ key: "v", header: "Opp", label: "Opponent", align: "left", value: (r: TeamTotalRecord) => r.opponent.short_code, cell: (r: TeamTotalRecord) => <Vs t={r.opponent} /> }),
  col({ key: "d", header: "Date", value: (r: TeamTotalRecord) => r.date, cell: (r: TeamTotalRecord) => <When r={r} /> }),
];
const marginCols = (unit: string): StatColumn<Ranked<MarginRecord>>[] => [
  rank,
  col({ key: "t", header: "Winner", align: "left", sticky: true, value: (r: MarginRecord) => r.winner.name, cell: (r: MarginRecord) => <Team t={r.winner} /> }),
  col({
    key: "m",
    header: "Margin",
    value: (r: MarginRecord) => r.margin,
    cell: (r: MarginRecord) => (
      <span>
        <span className="font-semibold">{r.margin}</span> {unit}
        {r.balls_remaining !== null && <span className="text-muted-foreground"> · {r.balls_remaining}b left</span>}
      </span>
    ),
  }),
  col({ key: "v", header: "Opp", label: "Opponent", align: "left", value: (r: MarginRecord) => r.loser.short_code, cell: (r: MarginRecord) => <Vs t={r.loser} /> }),
  col({ key: "d", header: "Date", value: (r: MarginRecord) => r.date, cell: (r: MarginRecord) => <When r={r} /> }),
];
const hsCols: StatColumn<Ranked<BattingInningsRecord>>[] = [
  rank,
  col({ key: "p", header: "Player", align: "left", sticky: true, value: (r: BattingInningsRecord) => displayName(r.player), cell: (r: BattingInningsRecord) => <Player p={r.player} team={r.team} /> }),
  col({ key: "r", header: "Runs", value: (r: BattingInningsRecord) => r.runs, cell: (r: BattingInningsRecord) => <span className="font-semibold">{r.runs}{r.not_out ? "*" : ""}</span> }),
  col({ key: "b", header: "Balls", value: (r: BattingInningsRecord) => r.balls }),
  col({ key: "46", header: "4s/6s", value: (r: BattingInningsRecord) => `${r.fours}/${r.sixes}`, hideBelow: "sm" }),
  col({ key: "v", header: "Opp", label: "Opponent", align: "left", value: (r: BattingInningsRecord) => r.opponent.short_code, cell: (r: BattingInningsRecord) => <Vs t={r.opponent} /> }),
  col({ key: "d", header: "Date", value: (r: BattingInningsRecord) => r.date, cell: (r: BattingInningsRecord) => <When r={r} /> }),
];
const bbCols: StatColumn<Ranked<BowlingFiguresRecord>>[] = [
  rank,
  col({ key: "p", header: "Player", align: "left", sticky: true, value: (r: BowlingFiguresRecord) => displayName(r.player), cell: (r: BowlingFiguresRecord) => <Player p={r.player} team={r.team} /> }),
  col({ key: "f", header: "Figures", value: (r: BowlingFiguresRecord) => r.wickets, cell: (r: BowlingFiguresRecord) => <span className="font-semibold">{r.wickets}/{r.runs}</span> }),
  col({ key: "o", header: "Ov", label: "Overs", value: (r: BowlingFiguresRecord) => r.overs }),
  col({ key: "v", header: "Opp", label: "Opponent", align: "left", value: (r: BowlingFiguresRecord) => r.opponent.short_code, cell: (r: BowlingFiguresRecord) => <Vs t={r.opponent} /> }),
  col({ key: "d", header: "Date", value: (r: BowlingFiguresRecord) => r.date, cell: (r: BowlingFiguresRecord) => <When r={r} /> }),
];
const pshipCols: StatColumn<Ranked<PartnershipRecord>>[] = [
  rank,
  col({
    key: "p",
    header: "Pair",
    align: "left",
    sticky: true,
    value: (r: PartnershipRecord) => displayName(r.batter1),
    cell: (r: PartnershipRecord) => (
      <span className="flex items-center gap-2">
        <TeamBadge team={r.team.short_code} />
        <span className="font-medium">
          {displayName(r.batter1)} <span className="text-muted-foreground">({r.batter1_runs})</span> & {displayName(r.batter2)}{" "}
          <span className="text-muted-foreground">({r.batter2_runs})</span>
        </span>
      </span>
    ),
  }),
  col({ key: "r", header: "Runs", value: (r: PartnershipRecord) => r.runs, className: "font-semibold" }),
  col({ key: "b", header: "Balls", value: (r: PartnershipRecord) => r.balls }),
  col({ key: "w", header: "Wkt", label: "For wicket", value: (r: PartnershipRecord) => r.wicket, hideBelow: "sm" }),
  col({ key: "d", header: "Date", value: (r: PartnershipRecord) => r.date, cell: (r: PartnershipRecord) => <When r={r} /> }),
];
const fastCols: StatColumn<Ranked<FastestMilestone>>[] = [
  rank,
  col({ key: "p", header: "Player", align: "left", sticky: true, value: (r: FastestMilestone) => displayName(r.player), cell: (r: FastestMilestone) => <Player p={r.player} team={r.team} /> }),
  col({ key: "b", header: "Balls", value: (r: FastestMilestone) => r.balls, className: "font-semibold" }),
  col({ key: "f", header: "Final", label: "Final score", value: (r: FastestMilestone) => r.final_runs }),
  col({ key: "v", header: "Opp", label: "Opponent", align: "left", value: (r: FastestMilestone) => r.opponent.short_code, cell: (r: FastestMilestone) => <Vs t={r.opponent} /> }),
  col({ key: "d", header: "Date", value: (r: FastestMilestone) => r.date, cell: (r: FastestMilestone) => <When r={r} /> }),
];

type Section = { key: keyof Records; title: string; cols: StatColumn<Ranked<never>>[] };
const SECTIONS: Section[] = [
  { key: "most_runs", title: "Most runs", cols: runsCols as never },
  { key: "most_wickets", title: "Most wickets", cols: wktCols as never },
  { key: "highest_individual_scores", title: "Highest individual scores", cols: hsCols as never },
  { key: "best_bowling_figures", title: "Best bowling figures", cols: bbCols as never },
  { key: "highest_totals", title: "Highest team totals", cols: totalCols as never },
  { key: "lowest_totals", title: "Lowest team totals", cols: totalCols as never },
  { key: "highest_partnerships", title: "Highest partnerships", cols: pshipCols as never },
  { key: "biggest_wins_by_runs", title: "Biggest wins by runs", cols: marginCols("runs") as never },
  { key: "biggest_wins_by_wickets", title: "Biggest wins by wickets", cols: marginCols("wkts") as never },
  { key: "fastest_fifties", title: "Fastest fifties", cols: fastCols as never },
  { key: "fastest_hundreds", title: "Fastest hundreds", cols: fastCols as never },
];

function RecordTable({ title, rows, cols }: { title: string; rows: object[]; cols: StatColumn<Ranked<never>>[] }) {
  const ranked = rows.map((r, i) => ({ ...r, _rank: i + 1 }));
  return (
    <section aria-label={title} className="min-w-0">
      <h2 className="text-overline mb-2 text-muted-foreground">{title}</h2>
      {ranked.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border bg-card/60 px-4 py-6 text-sm text-muted-foreground">No qualifying entries for this filter.</p>
      ) : (
        <StatTable caption={title} columns={cols as StatColumn<object>[]} rows={ranked} rowKey={(_, i) => String(i)} maxHeight="none" />
      )}
    </section>
  );
}

/* ---------- page ---------- */

export function RecordsView({ initialSeason, initialVenue }: { initialSeason: number | null; initialVenue: number | null }) {
  const [season, setSeason] = useState<number | null>(initialSeason);
  const [venue, setVenue] = useState<number | null>(initialVenue);
  const q = useRecords(season, venue);
  const venues = useVenueOptions();

  const seasonItems = [{ value: ALL, label: "All time" }, ...SEASON_OPTIONS.map((s) => ({ value: String(s), label: `IPL ${s}` }))];
  const venueItems = [{ value: ALL, label: "All venues" }, ...(venues.data ?? []).map((v) => ({ value: String(v.id), label: v.city ? `${v.name}, ${v.city}` : v.name }))];
  const venueName = venueItems.find((v) => v.value === String(venue))?.label;
  const scopeText = `${season ? `IPL ${season}` : "All time (2008–2026)"}${venue && venueName ? ` · ${venueName}` : ""}`;

  return (
    <>
      <PageHeader overline="Records" title="Records & stat explorer" subtitle="Settle any trivia argument: leaders, totals, margins and milestones." />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Select
          items={seasonItems}
          value={season ? String(season) : ALL}
          onValueChange={(v) => {
            const s = v && v !== ALL ? Number(v) : null;
            setSeason(s);
            replaceQuery({ season: s ? String(s) : null });
          }}
        >
          <SelectTrigger aria-label="Season filter" className="num h-10 min-w-36 rounded-[10px] bg-card">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {seasonItems.map((i) => (
              <SelectItem key={i.value} value={i.value} className="num">
                {i.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {!venues.isError && (
          <Select
            items={venueItems}
            value={venue ? String(venue) : ALL}
            onValueChange={(v) => {
              const id = v && v !== ALL ? Number(v) : null;
              setVenue(id);
              replaceQuery({ venue: id ? String(id) : null });
            }}
          >
            <SelectTrigger aria-label="Venue filter" className="h-10 max-w-[min(100%,22rem)] min-w-36 rounded-[10px] bg-card" disabled={venues.isPending}>
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
        )}
        <div className="flex gap-2 sm:ml-auto">
          <Link
            href="/records/milestones"
            className="inline-flex h-10 items-center gap-1.5 rounded-[10px] border border-border bg-card px-3 text-sm font-medium outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Milestone aria-hidden className="size-4 text-muted-foreground" /> Milestones
          </Link>
          <Link
            href="/records/streaks"
            className="inline-flex h-10 items-center gap-1.5 rounded-[10px] border border-border bg-card px-3 text-sm font-medium outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Flame aria-hidden className="size-4 text-muted-foreground" /> Streaks
          </Link>
        </div>
      </div>

      <p className="mb-4 text-xs text-muted-foreground" aria-live="polite">
        Showing <span className="font-medium text-foreground">{scopeText}</span>
        {q.isFetching && q.isPlaceholderData && " · updating…"}
      </p>

      {q.isPending ? (
        <div role="status" aria-busy="true" aria-label="Loading records" className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }, (_, i) => (
            <TableSkeleton key={i} rows={10} cols={5} />
          ))}
        </div>
      ) : q.isError ? (
        <ErrorState title="Couldn't load records" error={q.error} onRetry={() => q.refetch()} />
      ) : SECTIONS.every((s) => (q.data[s.key] as unknown[]).length === 0) ? (
        <EmptyState
          icon={Trophy}
          title="No records for this filter"
          why={`No completed matches match ${scopeText}.`}
          when="Try another season or clear the venue filter."
        />
      ) : (
        <div className={cn("grid gap-x-4 gap-y-6 lg:grid-cols-2", q.isPlaceholderData && "opacity-70 transition-opacity")}>
          {SECTIONS.map((s) => (
            <RecordTable key={s.key} title={s.title} rows={q.data[s.key] as object[]} cols={s.cols} />
          ))}
        </div>
      )}
    </>
  );
}
