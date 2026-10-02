"use client";

import { CalendarDays, ChevronLeft, Shield } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { SeasonSelect } from "@/components/data/season-select";
import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { StatTile } from "@/components/data/stat-tile";
import { ProfilePageSkeleton, RowsSkeleton, TableSkeleton } from "@/components/loaders/page-skeletons";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { SectionHeader } from "@/components/shell/page-header";
import { TabLinks } from "@/components/shell/tab-links";
import { getTeam } from "@/lib/tokens";
import { cn } from "@/lib/utils";

import { findTeam, formatNrr, nrrTone, ordinal, shortDate } from "../format";
import { useMatches, usePointsTables, useSeasons, useTeams } from "../queries";
import type { MatchSummary, PointsRow, SeasonSummary, TeamSummary } from "../types";
import { TEAM_TABS, type TeamTab } from "../tabs";
import { replaceQuery } from "../url";
import { ErrorState, StatusPill } from "./states";
import { TeamH2H } from "./team-h2h";
import { TeamSquadView } from "./team-squad";
import { seasonSpan } from "./teams-grid";

const TAB_LABEL: Record<TeamTab, string> = { overview: "Overview", squad: "Squad", matches: "Matches", h2h: "Head-to-head" };

export type SeasonFinish = {
  season: number;
  row: PointsRow | null;
  teams: number;
  outcome: "champion" | "runner_up" | "playoffs" | "league" | null;
};

/** Season-by-season finishes from each season's final table plus the champion/runner-up list. */
export function buildFinishes(team: TeamSummary, tables: ({ season: number; rows: PointsRow[] } | undefined)[], seasons: SeasonSummary[] | undefined): SeasonFinish[] {
  return team.seasons
    .map((season, i) => {
      const t = tables[i];
      const row = t?.rows.find((r) => r.team.id === team.id) ?? null;
      const s = seasons?.find((x) => x.year === season);
      const outcome: SeasonFinish["outcome"] = !row
        ? null
        : s?.champion?.id === team.id
          ? "champion"
          : s?.runner_up?.id === team.id
            ? "runner_up"
            : row.qualified
              ? "playoffs"
              : "league";
      return { season, row, teams: t?.rows.length ?? 0, outcome };
    })
    .reverse();
}

const OUTCOME: Record<NonNullable<SeasonFinish["outcome"]>, { label: string; tone: "gold" | "brand" | "positive" | "muted" }> = {
  champion: { label: "Champion", tone: "gold" },
  runner_up: { label: "Runner-up", tone: "brand" },
  playoffs: { label: "Playoffs", tone: "positive" },
  league: { label: "League stage", tone: "muted" },
};

const finishCols: StatColumn<SeasonFinish>[] = [
  {
    key: "season",
    header: "Season",
    align: "left",
    sticky: true,
    sortable: true,
    defaultDir: "desc",
    value: (r) => r.season,
    cell: (r) => (
      <Link href={`/table/${r.season}`} className="font-medium outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
        {r.season}
      </Link>
    ),
  },
  { key: "pos", header: "Pos", label: "League position", sortable: true, defaultDir: "asc", value: (r) => r.row?.position, cell: (r) => (r.row ? <span className="font-semibold">{ordinal(r.row.position)}<span className="font-normal text-muted-foreground">/{r.teams}</span></span> : <span className="text-faint">–</span>) },
  { key: "p", header: "P", label: "Played", value: (r) => r.row?.played, hideBelow: "sm" },
  { key: "w", header: "W", label: "Won", sortable: true, value: (r) => r.row?.won },
  { key: "l", header: "L", label: "Lost", value: (r) => r.row?.lost },
  { key: "pts", header: "Pts", label: "Points", sortable: true, value: (r) => r.row?.points, className: "font-semibold" },
  {
    key: "nrr",
    header: "NRR",
    label: "Net run rate",
    sortable: true,
    value: (r) => r.row?.nrr,
    cell: (r) =>
      r.row ? (
        <span className={cn(nrrTone(r.row.nrr) === "positive" && "text-positive", nrrTone(r.row.nrr) === "negative" && "text-negative")}>{formatNrr(r.row.nrr)}</span>
      ) : (
        <span className="text-faint">–</span>
      ),
  },
  {
    key: "out",
    header: "Finish",
    align: "left",
    value: (r) => (r.outcome ? OUTCOME[r.outcome].label : null),
    cell: (r) => (r.outcome ? <StatusPill tone={OUTCOME[r.outcome].tone}>{OUTCOME[r.outcome].label}</StatusPill> : <span className="text-faint">–</span>),
  },
];

function Overview({ team }: { team: TeamSummary }) {
  const tableQs = usePointsTables(team.seasons);
  const seasons = useSeasons();
  const loading = tableQs.some((q) => q.isPending) || seasons.isPending;
  const failed = tableQs.find((q) => q.isError);
  const finishes = buildFinishes(team, tableQs.map((q) => q.data), seasons.data);
  const done = finishes.filter((f) => f.row);
  const playoffs = done.filter((f) => f.outcome && f.outcome !== "league").length;
  const best = done.reduce<SeasonFinish | null>((b, f) => (!b || f.row!.position < b.row!.position ? f : b), null);
  const last = done[0];

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        <StatTile label="Titles" value={team.titles.length} hint={team.titles.length ? team.titles.join(", ") : "None yet"} />
        <StatTile label="Playoffs" value={loading ? null : playoffs} hint={loading ? "…" : `in ${done.length} season${done.length === 1 ? "" : "s"}`} />
        <StatTile label="Best league finish" value={best ? ordinal(best.row!.position) : null} hint={best ? String(best.season) : undefined} />
        <StatTile
          label={`Last season · ${last?.season ?? "–"}`}
          value={last ? ordinal(last.row!.position) : null}
          hint={last ? `${last.row!.points} pts · ${formatNrr(last.row!.nrr)} NRR` : undefined}
        />
      </div>
      <section aria-labelledby="finishes-h">
        <SectionHeader id="finishes-h" title="Season by season" />
        {failed ? (
          <ErrorState title="Couldn't load every season's table" error={failed.error} onRetry={() => tableQs.forEach((q) => q.isError && q.refetch())} />
        ) : loading ? (
          <TableSkeleton rows={Math.min(10, team.seasons.length)} cols={7} />
        ) : (
          <StatTable
            caption={`${team.name}: league finish by season`}
            columns={finishCols}
            rows={finishes}
            rowKey={(r) => String(r.season)}
            initialSort={{ key: "season", dir: "desc" }}
            maxHeight="none"
          />
        )}
      </section>
    </div>
  );
}

function MatchRow({ m, teamId }: { m: MatchSummary; teamId: number }) {
  const home = m.team1.id === teamId;
  const opp = home ? m.team2 : m.team1;
  const result = m.result === "no_result" ? "NR" : m.winner_id === teamId ? "W" : m.winner_id === null ? "T" : "L";
  const tone = result === "W" ? "positive" : result === "L" ? "negative" : "muted";
  const score = (id: number) =>
    m.scores
      .filter((s) => s.team_id === id)
      .map((s) => `${s.runs}/${s.wickets}${s.overs !== "20" ? ` (${s.overs})` : ""}`)
      .join(" & ");
  return (
    <li className="flex min-h-[52px] items-center gap-3 px-3 py-2 md:px-4">
      <StatusPill tone={tone} className="w-7 justify-center px-0">
        <span aria-hidden>{result}</span>
        <span className="sr-only">{{ W: "Won", L: "Lost", NR: "No result", T: "Tied" }[result]}</span>
      </StatusPill>
      <div className="w-14 shrink-0 text-[11px] leading-4 text-muted-foreground">
        <div className="num font-semibold text-foreground">{m.match_number ? `M${m.match_number}` : (m.stage ?? "–")}</div>
        <div className="num">{shortDate(m.date)}</div>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">v</span>
          <TeamBadge team={opp.short_code} />
          <span className="truncate font-medium max-sm:hidden">{opp.name}</span>
        </div>
        <p className="truncate text-xs text-muted-foreground">
          {m.result_text}
          {m.venue ? ` · ${m.venue.city ?? m.venue.name}` : ""}
        </p>
      </div>
      <div className="num shrink-0 text-right text-xs leading-4">
        <div className="font-semibold">{score(teamId) || "–"}</div>
        <div className="text-muted-foreground">{score(opp.id) || "–"}</div>
      </div>
    </li>
  );
}

function Matches({ team, initialSeason }: { team: TeamSummary; initialSeason: number | null }) {
  const seasons = [...team.seasons].reverse();
  const [season, setSeason] = useState(initialSeason && team.seasons.includes(initialSeason) ? initialSeason : seasons[0]);
  const q = useMatches(season, String(team.id));
  return (
    <section aria-labelledby="matches-h">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id="matches-h" className="text-overline text-muted-foreground">
          Matches{q.data ? ` · ${q.data.length}` : ""}
        </h2>
        <SeasonSelect
          value={season}
          seasons={seasons}
          onValueChange={(s) => {
            setSeason(s);
            replaceQuery({ season: String(s) });
          }}
        />
      </div>
      {q.isPending ? (
        <RowsSkeleton rows={8} />
      ) : q.isError ? (
        <ErrorState title="Couldn't load matches" error={q.error} onRetry={() => q.refetch()} />
      ) : q.data.length === 0 ? (
        <EmptyState compact icon={CalendarDays} title={`No ${season} matches`} why={`${team.name} have no completed matches in ${season} in the data.`} />
      ) : (
        <ol className={cn("divide-y divide-border overflow-hidden rounded-xl border border-border bg-card shadow-e1", q.isPlaceholderData && "opacity-70")}>
          {q.data.map((m) => (
            <MatchRow key={m.id} m={m} teamId={team.id} />
          ))}
        </ol>
      )}
    </section>
  );
}

export function TeamView({
  slug,
  tab,
  initialSeason,
  initialVs,
  initialVenue,
}: {
  slug: string;
  tab: TeamTab;
  initialSeason: number | null;
  initialVs: string | null;
  initialVenue: number | null;
}) {
  const teams = useTeams();
  if (teams.isPending) return <ProfilePageSkeleton label="Loading team" />;
  if (teams.isError) return <ErrorState title="Couldn't load teams" error={teams.error} onRetry={() => teams.refetch()} action={{ href: "/teams", label: "All teams" }} />;
  const team = findTeam(teams.data, slug);
  if (!team)
    return (
      <EmptyState
        icon={Shield}
        title="Team not found"
        why={`No IPL franchise matches "${decodeURIComponent(slug)}".`}
        action={{ href: "/teams", label: "Browse all teams" }}
      />
    );
  const theme = getTeam(team.short_code);
  const base = `/teams/${encodeURIComponent(team.short_code)}`;
  return (
    <>
      <Link href="/teams" className="mb-3 inline-flex h-8 items-center gap-1 text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring">
        <ChevronLeft aria-hidden className="size-4" /> Teams
      </Link>
      {/* Team page header: 2 px top border in team colour (§2.3 allowed accent). */}
      <header className="mb-4 rounded-xl border border-border bg-card p-4 shadow-e1" style={{ borderTop: `2px solid ${theme.primary}` }}>
        <div className="flex items-center gap-4">
          <TeamBadge team={team.short_code} size="2xl" />
          <div className="min-w-0">
            <p className="text-overline text-muted-foreground">
              {team.active ? "Current franchise" : "Former franchise"} · <span className="num">{seasonSpan(team.seasons)}</span>
            </p>
            <h1 className="text-display truncate">{team.name}</h1>
            {team.former_names.length > 0 && (
              <p className="truncate text-xs text-muted-foreground">
                {team.former_names.map((e) => `${e.name} (${e.from_season}–${e.to_season})`).join(" · ")}
              </p>
            )}
          </div>
        </div>
      </header>
      <TabLinks label="Team views" tabs={TEAM_TABS.map((k) => ({ key: k, label: TAB_LABEL[k] }))} active={tab} hrefFor={(k) => (k === "overview" ? base : `${base}?tab=${k}`)} />
      {tab === "overview" && <Overview team={team} />}
      {tab === "squad" && <TeamSquadView team={team} />}
      {tab === "matches" && <Matches team={team} initialSeason={initialSeason} />}
      {tab === "h2h" && <TeamH2H team={team} teams={teams.data} initialVs={initialVs} initialVenue={initialVenue} />}
    </>
  );
}
