"use client";

import { Trophy } from "lucide-react";
import Link from "next/link";

import { StatLineChart, type Series } from "@/components/charts/stat-charts";
import { StatTile } from "@/components/data/stat-tile";
import { ChartSkeleton, RowsSkeleton } from "@/components/loaders/page-skeletons";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { TeamBadge } from "@/components/player/team-badge";
import { useResolvedTheme } from "@/hooks/use-resolved-theme";
import { getTeam, teamChartColour } from "@/lib/tokens";
import { cn } from "@/lib/utils";

import { longDate, shortDate } from "../format";
import { useFantasyLeaders, useMatches, useRecords } from "../queries";
import type { MatchSummary, PlayerRef, PointsRow, SeasonSummary, TeamRef } from "../types";

/** Locally cached cut-out (`p11 media cache`); PlayerAvatar falls back to initials if absent. */
const photo = (id: string) => `/players/${id}-256.webp`;

const CARD = "min-w-0 rounded-xl border border-border bg-card shadow-e1";

/* ─────────────────────────────── KPI row ─────────────────────────────── */

/**
 * Full-width headline row for a season: matches, orange cap, purple cap, fantasy MVP, highest
 * total and top individual score. Every value comes from an existing endpoint; missing data shows "–".
 */
export function SeasonKpis({ season, summary }: { season: number; summary: SeasonSummary | undefined }) {
  const rec = useRecords(season, null);
  const fan = useFantasyLeaders(season);
  const runs = rec.data?.most_runs[0];
  const wkts = rec.data?.most_wickets[0];
  const total = rec.data?.highest_totals[0];
  const hs = rec.data?.highest_individual_scores[0];
  const mvp = fan.data?.rows[0];
  const name = (p: PlayerRef & { display_name?: string | null }) => p.display_name || p.name;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-4 xl:grid-cols-6">
      <StatTile
        label="Matches"
        value={summary?.match_count}
        hint={summary ? `${summary.league_match_count} league · ${summary.team_count} teams` : undefined}
      />
      <StatTile label="Orange cap" value={runs?.runs} unit="runs" hint={runs ? `${runs.player.name} · ${runs.team?.short_code ?? ""}` : undefined} href={runs ? `/players/${encodeURIComponent(runs.player.id)}` : undefined} />
      <StatTile label="Purple cap" value={wkts?.wickets} unit="wkts" hint={wkts ? `${wkts.player.name} · ${wkts.team?.short_code ?? ""}` : undefined} href={wkts ? `/players/${encodeURIComponent(wkts.player.id)}` : undefined} />
      <StatTile label="Fantasy MVP" value={mvp?.total} unit="pts" hint={mvp ? `${name(mvp.player)} · ${mvp.n} games` : fan.isError ? "Not available" : undefined} href={mvp ? `/players/${encodeURIComponent(mvp.player.id)}` : undefined} />
      <StatTile
        label="Highest total"
        value={total ? `${total.runs}/${total.wickets}` : undefined}
        hint={total ? `${total.team.short_code} v ${total.opponent.short_code} · ${shortDate(total.date)}` : undefined}
        href={total ? `/matches/${total.match_id}` : undefined}
      />
      <StatTile
        label="Top score"
        value={hs ? `${hs.runs}${hs.not_out ? "*" : ""}` : undefined}
        hint={hs ? `${hs.player.name} · ${hs.balls} balls v ${hs.opponent.short_code}` : undefined}
        href={hs ? `/matches/${hs.match_id}` : undefined}
      />
    </div>
  );
}

/* ─────────────────────────────── Champion ─────────────────────────────── */

/** Champion card: large crest with a faint team-colour wash, final result and season dates. */
export function ChampionCard({ summary, final }: { summary: SeasonSummary; final: MatchSummary | undefined }) {
  const champ = summary.champion;
  const theme = champ ? getTeam(champ.short_code) : null;
  return (
    <section aria-labelledby="champ-h" className={cn(CARD, "relative overflow-hidden p-4 md:p-5")}>
      {theme && (
        <>
          <span aria-hidden className="absolute inset-x-0 top-0 h-1" style={{ backgroundColor: theme.primary }} />
          <span aria-hidden className="pointer-events-none absolute -top-20 -right-20 size-64 rounded-full opacity-[0.1] blur-2xl" style={{ backgroundColor: theme.primary }} />
        </>
      )}
      <h2 id="champ-h" className="text-overline flex items-center gap-1.5 text-muted-foreground">
        <Trophy aria-hidden className="size-4 text-gold-text" /> {summary.label} {champ ? "champions" : ""}
      </h2>
      {champ ? (
        <div className="mt-3 flex items-center gap-4">
          <TeamBadge team={champ.short_code} size="2xl" />
          <div className="min-w-0">
            <Link href={`/teams/${encodeURIComponent(champ.short_code)}`} className="font-display block text-2xl leading-7 font-bold [font-stretch:85%] outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
              {champ.name}
            </Link>
            {summary.runner_up && <p className="mt-1 text-sm text-muted-foreground">Beat {summary.runner_up.name} in the final</p>}
          </div>
        </div>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">No champion yet: the season is still running.</p>
      )}
      {final && (
        <Link
          href={`/matches/${final.id}`}
          className="mt-4 flex items-center justify-between gap-3 rounded-lg bg-surface-2/70 px-3 py-2.5 text-sm outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="min-w-0">
            <span className="block truncate font-medium">{final.result_text}</span>
            <span className="num block truncate text-xs text-muted-foreground">
              Final · {longDate(final.date)}
              {final.venue ? ` · ${final.venue.city ?? final.venue.name}` : ""}
            </span>
          </span>
          <ScoreStack m={final} />
        </Link>
      )}
      <p className="num mt-3 text-xs text-muted-foreground">
        {longDate(summary.start_date)} – {longDate(summary.end_date)} · {summary.team_count} teams
      </p>
    </section>
  );
}

function ScoreStack({ m }: { m: MatchSummary }) {
  const line = (t: TeamRef) => {
    const s = m.scores.filter((x) => x.team_id === t.id);
    return s.length ? s.map((x) => `${x.runs}/${x.wickets}`).join(" & ") : "–";
  };
  return (
    <span className="num shrink-0 text-right text-xs leading-4">
      {[m.team1, m.team2].map((t) => (
        <span key={t.id} className={cn("block", m.winner_id === t.id ? "font-semibold" : "text-muted-foreground")}>
          {t.short_code} {line(t)}
        </span>
      ))}
    </span>
  );
}

/* ─────────────────────────────── Playoffs ─────────────────────────────── */

const STAGE_ORDER = ["Qualifier 1", "Eliminator", "Semi Final", "Qualifier 2", "3rd Place Play-Off", "Final"];

/** Playoff recap: every knockout match in order (Q1, Eliminator / semis, Q2, Final), winner bold. */
export function PlayoffRecap({ matches }: { matches: MatchSummary[] }) {
  const ko = matches.filter((m) => m.stage).sort((a, b) => STAGE_ORDER.indexOf(a.stage!) - STAGE_ORDER.indexOf(b.stage!) || a.date.localeCompare(b.date));
  if (!ko.length) return null;
  return (
    <section aria-labelledby="po-h" className={CARD}>
      <h2 id="po-h" className="text-overline px-4 pt-4 text-muted-foreground">
        Playoffs
      </h2>
      <ol className="mt-2 divide-y divide-border">
        {ko.map((m) => (
          <li key={m.id}>
            <Link href={`/matches/${m.id}`} className="flex items-center gap-3 px-4 py-3 outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset">
              <span className={cn("font-condensed w-12 shrink-0 text-xs font-bold uppercase", m.stage === "Final" ? "text-gold-text" : "text-muted-foreground")}>
                {stageCode(m.stage!)}
              </span>
              <span className="grid min-w-0 flex-1 gap-1">
                {[m.team1, m.team2].map((t) => (
                  <span key={t.id} className={cn("flex items-center justify-between gap-2 text-sm", m.winner_id === t.id ? "font-semibold" : "text-muted-foreground")}>
                    <span className="flex min-w-0 items-center gap-2">
                      <TeamBadge team={t.short_code} size="md" />
                      <span className="truncate">{t.name}</span>
                    </span>
                    <span className="num shrink-0">
                      {m.scores
                        .filter((s) => s.team_id === t.id)
                        .map((s) => `${s.runs}/${s.wickets}`)
                        .join(" & ") || "–"}
                    </span>
                  </span>
                ))}
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}

function stageCode(stage: string) {
  return { "Qualifier 1": "Q1", "Qualifier 2": "Q2", Eliminator: "Elim", "Semi Final": "SF", "3rd Place Play-Off": "3rd", Final: "Final" }[stage] ?? stage;
}

/* ─────────────────────────────── Leaders ─────────────────────────────── */

type LeaderRow = { id: string; name: string; team: TeamRef | null; value: number | string; meta: string; image?: string | null };

function LeaderList({ title, unit, rows }: { title: string; unit: string; rows: LeaderRow[] }) {
  if (!rows.length) return null;
  const [top, ...rest] = rows;
  return (
    <div className="min-w-0">
      <h3 className="text-overline px-4 text-muted-foreground">{title}</h3>
      <Link
        href={`/players/${encodeURIComponent(top.id)}`}
        className="mt-1 flex items-end gap-3 px-4 pt-1 outline-none hover:bg-surface-2/60 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
      >
        <PlayerAvatar name={top.name} src={top.image ?? photo(top.id)} team={top.team?.short_code} size="xl" />
        <span className="min-w-0 flex-1 pb-2">
          <span className="block truncate font-semibold">{top.name}</span>
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            {top.team && <TeamBadge team={top.team.short_code} />}
            <span className="num truncate">{top.meta}</span>
          </span>
        </span>
        <span className="pb-2 text-right">
          <span className="font-condensed num block text-3xl leading-8 font-bold">{top.value}</span>
          <span className="text-[11px] text-muted-foreground">{unit}</span>
        </span>
      </Link>
      <ol className="divide-y divide-border border-t border-border" start={2}>
        {rest.map((r, i) => (
          <li key={r.id}>
            <Link href={`/players/${encodeURIComponent(r.id)}`} className="flex h-10 items-center gap-2 px-4 text-sm outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset">
              <span className="num w-4 shrink-0 text-xs text-muted-foreground">{i + 2}</span>
              {r.team && <TeamBadge team={r.team.short_code} />}
              <span className="min-w-0 flex-1 truncate">{r.name}</span>
              <span className="num shrink-0 font-semibold">{r.value}</span>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Season leaders: runs, wickets and fantasy points (top 4 each), photo for the leader. */
export function SeasonLeaders({ season }: { season: number }) {
  const rec = useRecords(season, null);
  const fan = useFantasyLeaders(season);
  if (rec.isPending)
    return (
      <div role="status" aria-busy="true" aria-label="Loading season leaders">
        <RowsSkeleton rows={6} />
      </div>
    );
  if (rec.isError || !rec.data) return null;
  const runs: LeaderRow[] = rec.data.most_runs.slice(0, 4).map((r) => ({ id: r.player.id, name: r.player.name, team: r.team, value: r.runs, meta: `${r.innings} inns · SR ${r.strike_rate.toFixed(1)}` }));
  const wkts: LeaderRow[] = rec.data.most_wickets.slice(0, 4).map((r) => ({ id: r.player.id, name: r.player.name, team: r.team, value: r.wickets, meta: `${r.overs} ov · econ ${r.economy.toFixed(2)}` }));
  const fpts: LeaderRow[] = (fan.data?.rows ?? []).slice(0, 4).map((r) => ({
    id: r.player.id,
    name: r.player.display_name || r.player.name,
    team: r.team,
    value: r.total,
    meta: `${r.n} games · avg ${r.mean.toFixed(1)}`,
    image: r.player.image_url,
  }));
  if (!runs.length && !wkts.length) return null;
  return (
    <section aria-labelledby="leaders-h" className={cn(CARD, "grid gap-4 pt-4 pb-1")}>
      <h2 id="leaders-h" className="sr-only">
        Season leaders
      </h2>
      <LeaderList title="Most runs" unit="runs" rows={runs} />
      <LeaderList title="Most wickets" unit="wkts" rows={wkts} />
      <LeaderList title="Fantasy points" unit="pts" rows={fpts} />
    </section>
  );
}

/* ─────────────────────────────── Points race ─────────────────────────────── */

/** Cumulative league points after each of a team's games (2 per win, 1 per no result / tie). */
export function pointsRace(matches: MatchSummary[], teams: TeamRef[]) {
  const league = matches.filter((m) => !m.stage).sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id);
  const per = new Map<number, number[]>(teams.map((t) => [t.id, []]));
  for (const m of league) {
    for (const t of [m.team1, m.team2]) {
      const arr = per.get(t.id);
      if (!arr) continue;
      const prev = arr[arr.length - 1] ?? 0;
      const pts = m.result === "no_result" || m.winner_id === null ? 1 : m.winner_id === t.id ? 2 : 0;
      arr.push(prev + pts);
    }
  }
  const games = Math.max(0, ...[...per.values()].map((a) => a.length));
  const data = Array.from({ length: games + 1 }, (_, g) => {
    const row: Record<string, number | string | null> = { game: g };
    teams.forEach((t) => (row[`t${t.id}`] = g === 0 ? 0 : (per.get(t.id)?.[g - 1] ?? null)));
    return row;
  });
  return data;
}

/** Points race for the four playoff teams in team colours (dashes on 3rd–4th as a shape cue). */
export function PointsRace({ season, rows }: { season: number; rows: PointsRow[] }) {
  const q = useMatches(season, null);
  const theme = useResolvedTheme();
  if (q.isPending) return <ChartSkeleton />;
  if (q.isError || !q.data.length) return null;
  const top = rows.slice(0, 4).map((r) => r.team);
  const data = pointsRace(q.data, top);
  const series: Series[] = top.map((t, i) => ({ key: `t${t.id}`, label: t.short_code, color: teamChartColour(t.short_code, theme), dashed: i >= 2 }));
  const summary = `League points after each game for the top four: ${rows
    .slice(0, 4)
    .map((r) => `${r.team.short_code} ${r.points}`)
    .join(", ")}.`;
  return <StatLineChart title="Points race · top 4" summary={summary} data={data} xKey="game" series={series} height={280} />;
}

/** Final match (if played) from the season's match list. */
export function useFinal(season: number) {
  const q = useMatches(season, null);
  return { matches: q.data ?? [], final: q.data?.find((m) => m.stage === "Final") };
}
