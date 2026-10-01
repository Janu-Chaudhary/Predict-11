"use client";

import { Trophy } from "lucide-react";

import { SeasonSelect, SEASONS } from "@/components/data/season-select";
import { TableSkeleton } from "@/components/loaders/page-skeletons";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader, SectionHeader } from "@/components/shell/page-header";
import { TabLinks } from "@/components/shell/tab-links";

import { longDate } from "../format";
import { SEASON_TABS, type SeasonTab } from "../tabs";
import { usePointsTable, useSeasons } from "../queries";
import type { SeasonSummary } from "../types";
import { PointsTableView } from "./points-table";
import { ScenariosPanel } from "./scenarios-panel";
import { ErrorState, TeamName } from "./states";
import { StoryPanel } from "./story-panel";


const TAB_LABEL: Record<SeasonTab, string> = { table: "Table", scenarios: "Scenarios", story: "Story" };

export function SeasonView({ season, tab, after }: { season: number; tab: SeasonTab; after: number | null }) {
  const href = (s: number, t: SeasonTab) => `/table/${s}${t === "table" ? "" : `?tab=${t}`}`;
  return (
    <>
      <PageHeader
        overline={`IPL ${season}`}
        title="Points table"
        actions={<SeasonSelect value={season} seasons={SEASONS} hrefFor={(s) => href(s, tab)} label="Season" />}
        className="mb-4"
      />
      <TabLinks
        label="Season views"
        tabs={SEASON_TABS.map((k) => ({ key: k, label: TAB_LABEL[k] }))}
        active={tab}
        hrefFor={(k) => href(season, k as SeasonTab)}
      />
      {tab === "table" && <TableTab season={season} />}
      {tab === "scenarios" && <ScenariosPanel key={season} season={season} initialAfter={after} />}
      {tab === "story" && <StoryPanel season={season} />}
    </>
  );
}

function TableTab({ season }: { season: number }) {
  const q = usePointsTable(season);
  const seasons = useSeasons();
  const summary = seasons.data?.find((s) => s.year === season);

  return (
    <div className="grid gap-4 lg:grid-cols-12 lg:gap-6">
      <div className="min-w-0 lg:col-span-8">
        {q.isPending ? (
          <div role="status" aria-busy="true" aria-label="Loading points table">
            <TableSkeleton rows={10} cols={8} />
          </div>
        ) : q.isError ? (
          <ErrorState title="Couldn't load the points table" error={q.error} onRetry={() => q.refetch()} />
        ) : q.data.rows.length === 0 ? (
          <EmptyState
            icon={Trophy}
            title={`No IPL ${season} results yet`}
            why="No league match of this season has a result in the database."
            when="The table fills itself about an hour after the first result."
            action={{ href: `/table/${season - 1}`, label: `See IPL ${season - 1}` }}
          />
        ) : (
          <>
            <PointsTableView rows={q.data.rows} caption={`IPL ${season} points table`} />
            <p className="mt-2 text-xs text-muted-foreground">
              <span className="num">
                {q.data.rows.reduce((n, r) => n + r.played, 0) / 2} of {q.data.league_matches}
              </span>{" "}
              league matches played. Ranked by {q.data.tiebreak}.
            </p>
          </>
        )}
      </div>
      <aside className="grid min-w-0 content-start gap-4 lg:col-span-4" aria-label="Season summary">
        {summary ? <SeasonCard s={summary} /> : seasons.isPending ? <TableSkeleton rows={3} cols={2} /> : null}
      </aside>
    </div>
  );
}

function SeasonCard({ s }: { s: SeasonSummary }) {
  return (
    <section className="min-w-0 rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4">
      <SectionHeader title={s.label} />
      <dl className="grid grid-cols-[minmax(0,1fr)] gap-2 text-sm">
        {s.champion && (
          <div className="flex items-center justify-between gap-2">
            <dt className="flex shrink-0 items-center gap-1.5 text-muted-foreground">
              <Trophy aria-hidden className="size-4 text-gold-text" /> Champion
            </dt>
            <dd className="flex min-w-0 justify-end">
              <TeamName team={s.champion} short="never" />
            </dd>
          </div>
        )}
        {s.runner_up && (
          <div className="flex items-center justify-between gap-2">
            <dt className="shrink-0 text-muted-foreground">Runner-up</dt>
            <dd className="flex min-w-0 justify-end">
              <TeamName team={s.runner_up} short="never" />
            </dd>
          </div>
        )}
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Matches</dt>
          <dd className="num">
            {s.match_count} <span className="text-muted-foreground">({s.league_match_count} league)</span>
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Teams</dt>
          <dd className="num">{s.team_count}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground">Dates</dt>
          <dd className="num text-right">
            {longDate(s.start_date)} – {longDate(s.end_date)}
          </dd>
        </div>
      </dl>
    </section>
  );
}
