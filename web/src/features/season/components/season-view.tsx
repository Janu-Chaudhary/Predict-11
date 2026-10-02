"use client";

import { Trophy } from "lucide-react";

import { SeasonSelect, SEASONS } from "@/components/data/season-select";
import { TableSkeleton } from "@/components/loaders/page-skeletons";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { TabLinks } from "@/components/shell/tab-links";

import { SEASON_TABS, type SeasonTab } from "../tabs";
import { usePointsTable, useSeasons } from "../queries";
import { PointsTableView } from "./points-table";
import { ScenariosPanel } from "./scenarios-panel";
import { ErrorState } from "./states";
import { ChampionCard, PlayoffRecap, PointsRace, SeasonKpis, SeasonLeaders, useFinal } from "./season-rail";
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
  const { matches, final } = useFinal(season);
  const hasRows = q.isSuccess && q.data.rows.length > 0;

  return (
    <div className="grid gap-4 lg:gap-6">
      {hasRows && <SeasonKpis season={season} summary={summary} />}
      <div className="grid gap-4 lg:grid-cols-12 lg:gap-6">
        <div className="grid min-w-0 content-start gap-4 lg:col-span-8 lg:gap-6">
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
              <div>
                <PointsTableView rows={q.data.rows} caption={`IPL ${season} points table`} />
                <p className="mt-2 text-xs text-muted-foreground">
                  <span className="num">
                    {q.data.rows.reduce((n, r) => n + r.played, 0) / 2} of {q.data.league_matches}
                  </span>{" "}
                  league matches played. Ranked by {q.data.tiebreak}.
                </p>
              </div>
              <PointsRace season={season} rows={q.data.rows} />
            </>
          )}
        </div>
        <aside className="grid min-w-0 content-start gap-4 lg:col-span-4 lg:gap-6" aria-label="Season summary">
          {summary ? <ChampionCard summary={summary} final={final} /> : seasons.isPending ? <TableSkeleton rows={3} cols={2} /> : null}
          <PlayoffRecap matches={matches} />
          {hasRows && <SeasonLeaders season={season} />}
        </aside>
      </div>
    </div>
  );
}
