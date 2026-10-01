"use client";

import { ListOrdered, Trophy } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { StatLineChart } from "@/components/charts/stat-charts";
import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { StatTile } from "@/components/data/stat-tile";
import { SeasonSelect } from "@/components/data/season-select";
import { ChartSkeleton, TableSkeleton, TilesSkeleton } from "@/components/loaders/page-skeletons";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { displayName, fmt, fmtDate } from "../players/format";
import { Panel, QueryError } from "../players/ui";
import { fmtPts, signed } from "./format";
import { CURRENT_FANTASY_SEASON, FANTASY_SEASONS } from "./leaderboard-view";
import { useSeasonBestXis, useTeamOfSeason } from "./queries";
import type { SeasonBestXis, SeasonMatchXi, TeamOfSeason } from "./types";
import { FantasySubnav, Segmented } from "./ui";
import { XiPanel } from "./xi-view";

export function bestXiHref(season: number) {
  return season === CURRENT_FANTASY_SEASON ? "/fantasy/best-xi" : `/fantasy/best-xi?season=${season}`;
}

/**
 * Best XIs (F3 + H2): the season's team of the season on the pitch, then every match's
 * hindsight Dream Team total against the naive "pick on recent form" XI.
 */
export function BestXiView({ season }: { season: number }) {
  const tos = useTeamOfSeason(season);
  const xis = useSeasonBestXis(season);
  return (
    <>
      <PageHeader
        overline="Fantasy · Hindsight"
        title={`Best XIs · IPL ${season}`}
        subtitle="The best possible Dream11 teams, picked with hindsight, and how far a pick-on-form team fell short."
        actions={<SeasonSelect value={season} seasons={FANTASY_SEASONS} hrefFor={bestXiHref} />}
      />
      <FantasySubnav active="best-xi" season={season !== CURRENT_FANTASY_SEASON ? season : null} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        <div className="min-w-0 lg:col-span-5">
          {tos.isError ? (
            <QueryError error={tos.error} onRetry={() => tos.refetch()} what="the team of the season" />
          ) : tos.isPending || !tos.data ? (
            <Skeleton className="h-[34rem] rounded-2xl" />
          ) : (
            <TeamOfSeasonCard data={tos.data} stale={tos.isPlaceholderData} />
          )}
        </div>
        <div className="grid min-w-0 grid-cols-1 content-start gap-4 lg:col-span-7">
          {xis.isError ? (
            <QueryError error={xis.error} onRetry={() => xis.refetch()} what="the match best XIs" />
          ) : xis.isPending || !xis.data ? (
            <div role="status" aria-busy="true" aria-label="Loading match best XIs" className="grid gap-4">
              <TilesSkeleton count={4} />
              <ChartSkeleton />
              <TableSkeleton rows={8} cols={5} />
            </div>
          ) : xis.data.matches.length === 0 ? (
            <EmptyState icon={ListOrdered} title={`No scored matches in ${season}`} why="Best XIs need completed matches with stored fantasy points." action={{ href: bestXiHref(CURRENT_FANTASY_SEASON), label: `Open ${CURRENT_FANTASY_SEASON}` }} />
          ) : (
            <SeasonMatches data={xis.data} stale={xis.isPlaceholderData} />
          )}
        </div>
      </div>
    </>
  );
}

export function TeamOfSeasonCard({ data, stale = false }: { data: TeamOfSeason; stale?: boolean }) {
  const [metric, setMetric] = useState<"total" | "mean">("total");
  const xi = metric === "mean" ? (data.by_mean ?? data.by_total) : (data.by_total ?? data.by_mean);
  if (!xi || xi.picks.length === 0) {
    return <EmptyState compact icon={Trophy} title="No team of the season yet" why={`No player has stored fantasy points in IPL ${data.season}.`} />;
  }
  const withMult = xi.picks.reduce((s, p) => s + (metric === "mean" ? (p.mean ?? 0) * (p.captain ? 2 : p.vice_captain ? 1.5 : 1) : p.effective), 0);
  const raw = metric === "mean" ? xi.sum_mean : xi.sum_total;
  return (
    <Panel
      id="tos"
      title={`Team of the season · ${data.season}`}
      className={cn("transition-opacity", stale && "opacity-60")}
      action={
        <Segmented<"total" | "mean">
          label="Rank the team of the season by"
          value={metric}
          onChange={setMetric}
          options={[
            { key: "total", label: "Season total" },
            { key: "mean", label: "Per match", title: `Mean points per match, min ${data.by_mean?.min_matches ?? 1} matches` },
          ]}
        />
      }
    >
      <dl className="num mb-3 grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-surface-2/60 p-2.5">
          <dt className="text-overline text-muted-foreground">{metric === "mean" ? "Points / match" : "Season points"}</dt>
          <dd className="font-condensed text-[1.75rem] leading-8 font-bold">{fmtPts(Math.round(withMult * 10) / 10)}</dd>
          <dd className="text-xs text-muted-foreground">with C ×2, VC ×1.5</dd>
        </div>
        <div className="rounded-lg bg-surface-2/60 p-2.5">
          <dt className="text-overline text-muted-foreground">Without C/VC</dt>
          <dd className="font-condensed text-[1.75rem] leading-8 font-bold">{fmtPts(Math.round(raw * 10) / 10)}</dd>
          <dd className="text-xs text-muted-foreground">sum of 11 {metric === "mean" ? "means" : "totals"}</dd>
        </div>
      </dl>
      <XiPanel
        xi={metric === "mean" ? xi.picks.map((p) => ({ ...p, points: Math.round((p.mean ?? 0) * 10) / 10, effective: (p.mean ?? 0) * (p.captain ? 2 : p.vice_captain ? 1.5 : 1) })) : xi.picks}
        title={`Team of the season ${data.season}`}
        unit={metric === "mean" ? "avg" : "pts"}
      />
      <p className="mt-2 text-xs text-muted-foreground">
        Dream11 shape (1–8 per role, 11 players), no credit cap. C and VC go to the two biggest {metric === "mean" ? "per-match averages" : "season totals"}.
        {metric === "mean" && data.by_mean && ` Min ${data.by_mean.min_matches} matches.`}
      </p>
    </Panel>
  );
}

export function SeasonMatches({ data, stale = false }: { data: SeasonBestXis; stale?: boolean }) {
  const ms = [...data.matches].sort((a, b) => (a.date ?? "").localeCompare(b.date ?? "") || (a.match_number ?? 0) - (b.match_number ?? 0));
  const label = (m: SeasonMatchXi, i: number) => (m.match_number ? `M${m.match_number}` : m.stage ? m.stage : `#${i + 1}`);
  const chart = ms.map((m, i) => ({ match: label(m, i), best: Math.round(m.best_total), naive: m.naive_total === null ? null : Math.round(m.naive_total) }));
  const beat = ms.reduce((best, m) => (best === null || m.best_total > best.best_total ? m : best), null as SeasonMatchXi | null);

  const cols: StatColumn<SeasonMatchXi>[] = [
    { key: "n", header: "#", value: (m) => m.match_number ?? null, align: "left", sortable: true, defaultDir: "asc", sticky: true, cell: (m) => <span className="text-muted-foreground">{m.match_number ?? m.stage ?? "–"}</span> },
    {
      key: "match",
      header: "Match",
      align: "left",
      value: (m) => `${m.home} v ${m.away}`,
      cell: (m) => (
        <Link
          href={`/fantasy/match/${m.match_id}`}
          aria-label={`${m.home_name ?? m.home} v ${m.away_name ?? m.away}, ${fmtDate(m.date)}: best XI`}
          className="inline-flex items-center gap-1.5 rounded font-medium outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          {m.home && <TeamBadge team={m.home} />}
          <span className="text-muted-foreground">v</span>
          {m.away && <TeamBadge team={m.away} />}
        </Link>
      ),
    },
    { key: "date", header: "Date", value: (m) => m.date, align: "left", sortable: true, hideBelow: "sm", cell: (m) => fmtDate(m.date, { day: "numeric", month: "short" }) },
    { key: "best", header: "Best", value: (m) => m.best_total, sortable: true, cell: (m) => <span className="font-semibold">{fmtPts(m.best_total)}</span> },
    { key: "naive", header: "Form XI", value: (m) => m.naive_total, sortable: true, hideBelow: "sm", cell: (m) => fmtPts(m.naive_total) },
    { key: "gap", header: "Gap", value: (m) => m.gap, sortable: true, cell: (m) => <span className="text-muted-foreground">{signed(m.gap)}</span> },
    {
      key: "top",
      header: "Top scorer",
      align: "left",
      value: (m) => m.top_points,
      sortable: true,
      hideBelow: "md",
      cell: (m) => (m.top_scorer ? <span className="truncate">{displayName(m.top_scorer)} <span className="text-muted-foreground">{fmt(m.top_points)}</span></span> : "–"),
    },
  ];

  return (
    <div className={cn("grid min-w-0 grid-cols-1 gap-4 transition-opacity", stale && "opacity-60")}>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:gap-3">
        <StatTile label="Avg best XI" value={data.mean_best} format={(n) => fmt(n)} hint={`${ms.length} matches`} />
        <StatTile label="Avg form XI" value={data.mean_naive} format={(n) => fmt(n)} hint="last-5 form picks" />
        <StatTile label="Avg gap" value={data.mean_gap} format={(n) => fmt(n)} hint="points left on the table" />
        <StatTile label="Best of season" value={data.max_best} format={(n) => fmt(n)} hint={beat ? `${beat.home} v ${beat.away}` : undefined} href={beat ? `/fantasy/match/${beat.match_id}` : undefined} />
      </div>
      <StatLineChart
        title="Per match · hindsight best XI vs form XI"
        summary={`Across ${ms.length} matches of IPL ${data.season}, the hindsight best XI averaged ${fmt(data.mean_best)} points and the naive form XI ${fmt(data.mean_naive)}, a gap of ${fmt(data.mean_gap)}.`}
        data={chart}
        xKey="match"
        series={[
          { key: "best", label: "Hindsight best XI", color: "var(--primary)" },
          { key: "naive", label: "Form XI (last-5 mean)", color: "var(--brand)", dashed: true },
        ]}
        height={240}
      />
      <section aria-labelledby="matches-h" className="min-w-0">
        <h2 id="matches-h" className="text-overline mb-2 text-muted-foreground">
          Every match · open one for its Dream Team
        </h2>
        <StatTable
          caption={`IPL ${data.season}: best XI and form XI totals per match`}
          columns={cols}
          rows={ms}
          rowKey={(m) => String(m.match_id)}
          initialSort={{ key: "date", dir: "desc" }}
          maxHeight="32rem"
          footer={
            <>
              Totals include C ×2 and VC ×1.5. Form XI = best XI by each player’s last-5 mean before the match, scored on what they actually got.
              {data.no_result_matches > 0 && ` ${data.no_result_matches} no-result ${data.no_result_matches === 1 ? "match is" : "matches are"} left out.`}
            </>
          }
        />
      </section>
    </div>
  );
}
