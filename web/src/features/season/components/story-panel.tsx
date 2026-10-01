"use client";

import { BookOpen } from "lucide-react";
import Link from "next/link";

import { StatLineChart, type Series } from "@/components/charts/stat-charts";
import { ChartSkeleton, RowsSkeleton } from "@/components/loaders/page-skeletons";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { SectionHeader } from "@/components/shell/page-header";

import { shortDate } from "../format";
import { useSeasonStory } from "../queries";
import type { BattingLeader, BowlingLeader, CapRace, PlayerRef, TeamRef } from "../types";
import { ErrorState } from "./states";

export function raceToChart(race: CapRace, top = 5) {
  const leaders = race.leaders.slice(0, top);
  const series: Series[] = leaders.map((l, i) => ({
    key: `p${i}`,
    label: `${l.player.name}${l.team ? ` (${l.team.short_code})` : ""}`,
    dashed: i >= 3, // shape cue beyond the first three colours
  }));
  const data = race.dates.map((d, di) => {
    const row: Record<string, string | number | null> = { date: shortDate(d) };
    leaders.forEach((l, i) => (row[`p${i}`] = l.cumulative[di] ?? null));
    return row;
  });
  return { series, data, leaders };
}

function CapRaceChart({ title, race, unit }: { title: string; race: CapRace; unit: string }) {
  const { series, data, leaders } = raceToChart(race);
  if (!leaders.length) return null;
  const lead = leaders[0];
  const summary = `${title}: ${lead.player.name} leads with ${lead.total} ${unit}; ${leaders
    .slice(1)
    .map((l) => `${l.player.name} ${l.total}`)
    .join(", ")}.`;
  return <StatLineChart title={title} summary={summary} data={data} xKey="date" series={series} height={260} />;
}

function PlayerCell({ player, team }: { player: PlayerRef; team: TeamRef | null }) {
  return (
    <span className="flex min-w-0 items-center gap-2">
      {team && <TeamBadge team={team.short_code} />}
      <Link href={`/players/${encodeURIComponent(player.id)}`} className="truncate font-medium outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
        {player.name}
      </Link>
    </span>
  );
}

/** Compact ranked list: rank · player · context · headline stat (weight, not colour). */
function Leaderboard<T extends { player: PlayerRef; team: TeamRef | null }>({
  title,
  rows,
  stat,
  meta,
  note,
}: {
  title: string;
  rows: T[];
  stat: (r: T) => string | number;
  meta: (r: T) => string;
  note?: string;
}) {
  return (
    <section aria-label={title} className="rounded-xl border border-border bg-card shadow-e1">
      <h3 className="text-overline px-3 pt-3 text-muted-foreground md:px-4">{title}</h3>
      {rows.length === 0 ? (
        <p className="px-4 py-4 text-sm text-muted-foreground">Nobody qualifies yet.</p>
      ) : (
        <ol className="mt-1 divide-y divide-border">
          {rows.slice(0, 5).map((r, i) => (
            <li key={r.player.id} className="flex min-h-[52px] items-center gap-3 px-3 md:px-4">
              <span className="num w-4 shrink-0 text-xs text-muted-foreground">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <PlayerCell player={r.player} team={r.team} />
                <div className="num mt-0.5 truncate text-xs text-muted-foreground">{meta(r)}</div>
              </div>
              <span className="num shrink-0 text-base font-semibold">{stat(r)}</span>
            </li>
          ))}
        </ol>
      )}
      {note && <p className="border-t border-border px-3 py-2 text-[11px] text-muted-foreground md:px-4">{note}</p>}
    </section>
  );
}

export function StoryPanel({ season }: { season: number }) {
  const q = useSeasonStory(season);
  if (q.isPending)
    return (
      <div role="status" aria-busy="true" aria-label="Loading season story" className="grid gap-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <RowsSkeleton rows={5} />
          <RowsSkeleton rows={5} />
          <RowsSkeleton rows={5} />
        </div>
      </div>
    );
  if (q.isError) return <ErrorState title="Couldn't load the season story" error={q.error} onRetry={() => q.refetch()} />;
  const s = q.data;
  if (!s.orange_cap.leaders.length && !s.purple_cap.leaders.length)
    return <EmptyState icon={BookOpen} title="No story yet" why="No ball-by-ball data has been harvested for this season yet." when="It fills in about an hour after each result." />;

  const bat = (r: BattingLeader) => `${r.runs} runs · ${r.balls} balls · ${r.innings} inns`;
  const bowl = (r: BowlingLeader) => `${r.wickets} wkts · ${r.overs} ov · ${r.runs} runs`;
  return (
    <div className="grid gap-6">
      <section aria-labelledby="caps-h">
        <SectionHeader id="caps-h" title="Cap races · top 5, cumulative" />
        <div className="grid gap-4 lg:grid-cols-2">
          <CapRaceChart title="Orange cap · runs" race={s.orange_cap} unit="runs" />
          <CapRaceChart title="Purple cap · wickets" race={s.purple_cap} unit="wickets" />
        </div>
      </section>
      <section aria-labelledby="lb-h">
        <SectionHeader id="lb-h" title="Leaderboards" />
        <div className="grid gap-4 md:grid-cols-3">
          <Leaderboard title="Most sixes" rows={s.most_sixes} stat={(r) => r.sixes} meta={bat} />
          <Leaderboard
            title="Best strike rate"
            rows={s.best_strike_rate}
            stat={(r) => r.strike_rate.toFixed(1)}
            meta={bat}
            note={`Min ${s.min_balls_for_strike_rate} balls faced.`}
          />
          <Leaderboard
            title="Best economy"
            rows={s.best_economy}
            stat={(r) => r.economy.toFixed(2)}
            meta={bowl}
            note={`Min ${s.min_overs_for_economy} overs bowled.`}
          />
        </div>
      </section>
    </div>
  );
}
