"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { RowsSkeleton } from "@/components/loaders/page-skeletons";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { TeamBadge } from "@/components/player/team-badge";

import { DEFAULT_MIN_MATCHES } from "../fantasy/format";
import { useLeaderboard } from "../fantasy/queries";
import { ApiError, getJson } from "./api";
import { displayName, fmt, photoOf } from "./format";
import { Panel, QueryError } from "./ui";

/** Slice of GET /records?scope=season (backend records_models). Only the two leader lists are read. */
type RecordsLeaders = {
  most_runs: { player: { id: string; name: string }; team: { short_code: string } | null; innings: number; runs: number; strike_rate: number | null }[];
  most_wickets: { player: { id: string; name: string }; team: { short_code: string } | null; innings: number; wickets: number; economy: number | null }[];
};

const retry = (n: number, err: unknown) => !(err instanceof ApiError && err.status !== null && err.status < 500) && n < 1;

function useSeasonRecords(season: number) {
  return useQuery({
    queryKey: ["players", "season-leaders", season],
    queryFn: ({ signal }) => getJson<RecordsLeaders>("/records", { scope: "season", season, limit: 5 }, signal),
    staleTime: 10 * 60_000,
    retry,
  });
}

type Item = { id: string; name: string; team: string | null; photo?: string | null; value: string; unit: string; meta: string };

function LeaderList({ label, items }: { label: string; items: Item[] }) {
  return (
    <ol aria-label={label} className="divide-y divide-border">
      {items.map((it, i) => (
        <li key={it.id}>
          <Link
            href={`/players/${encodeURIComponent(it.id)}`}
            className="flex min-h-[52px] items-center gap-3 px-3 py-1.5 outline-none hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset md:px-4"
          >
            <span className="num w-4 text-right text-xs text-faint">{i + 1}</span>
            <PlayerAvatar name={it.name} src={it.photo ?? `/players/${it.id}-256.webp`} team={it.team ?? undefined} size="md" />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium">{it.name}</span>
              <span className="num flex items-center gap-1.5 text-xs text-muted-foreground">
                {it.team && <TeamBadge team={it.team} />}
                <span className="truncate">{it.meta}</span>
              </span>
            </span>
            <span className="num text-right">
              <span className="font-condensed block text-xl leading-6 font-bold">{it.value}</span>
              <span className="block text-[11px] leading-4 text-muted-foreground">{it.unit}</span>
            </span>
          </Link>
        </li>
      ))}
    </ol>
  );
}

/** Players index side rail: the season's run, wicket and Dream11 points leaders. */
export function SeasonLeaders({ season }: { season: number }) {
  const rec = useSeasonRecords(season);
  const fan = useLeaderboard({ season, role: "ALL", minMatches: DEFAULT_MIN_MATCHES });

  const runs: Item[] = (rec.data?.most_runs ?? []).slice(0, 5).map((r) => ({
    id: r.player.id,
    name: r.player.name,
    team: r.team?.short_code ?? null,
    value: fmt(r.runs),
    unit: "runs",
    meta: `${r.innings} inns · SR ${fmt(r.strike_rate, 1)}`,
  }));
  const wkts: Item[] = (rec.data?.most_wickets ?? []).slice(0, 5).map((r) => ({
    id: r.player.id,
    name: r.player.name,
    team: r.team?.short_code ?? null,
    value: fmt(r.wickets),
    unit: "wkts",
    meta: `${r.innings} inns · econ ${fmt(r.economy, 2)}`,
  }));
  const pts: Item[] = [...(fan.data?.rows ?? [])]
    .sort((a, b) => (b.total ?? 0) - (a.total ?? 0))
    .slice(0, 5)
    .map((r) => ({
      id: r.player.id,
      name: displayName(r.player),
      team: r.team,
      photo: photoOf(r.player),
      value: fmt(r.total),
      unit: "pts",
      meta: `${r.matches} m · ${fmt(r.mean, 1)} avg`,
    }));

  const recBody = (items: Item[], label: string) =>
    rec.isPending ? <RowsSkeleton rows={5} className="p-3" /> : rec.isError ? <QueryError error={rec.error} onRetry={() => rec.refetch()} what="season leaders" className="m-3" /> : <LeaderList label={label} items={items} />;

  const more = (href: string, text: string) => (
    <Link href={href} className="rounded text-xs font-medium text-brand outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring">
      {text} →
    </Link>
  );

  return (
    <>
      <Panel title={`Most runs · IPL ${season}`} id="lead-runs" bodyClassName="px-0 pb-1 md:px-0" action={more("/records", "Records")}>
        {recBody(runs, `Most runs in IPL ${season}`)}
      </Panel>
      <Panel title={`Most wickets · IPL ${season}`} id="lead-wkts" bodyClassName="px-0 pb-1 md:px-0" action={more("/records", "Records")}>
        {recBody(wkts, `Most wickets in IPL ${season}`)}
      </Panel>
      <Panel title={`Fantasy points · IPL ${season}`} id="lead-pts" bodyClassName="px-0 pb-1 md:px-0" action={more("/fantasy", "Leaderboards")}>
        {fan.isPending ? (
          <RowsSkeleton rows={5} className="p-3" />
        ) : fan.isError ? (
          <QueryError error={fan.error} onRetry={() => fan.refetch()} what="fantasy leaders" className="m-3" />
        ) : (
          <LeaderList label={`Most Dream11 points in IPL ${season}`} items={pts} />
        )}
      </Panel>
    </>
  );
}
