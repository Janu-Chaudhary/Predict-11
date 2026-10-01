import type { Metadata } from "next";

import { FANTASY_STALE_MS, fantasyKeys, fetchLeaderboard } from "@/features/fantasy/api";
import { parseMinMatches, parseRole, parseSort } from "@/features/fantasy/format";
import { CURRENT_FANTASY_SEASON, FantasyLeaderboard } from "@/features/fantasy/leaderboard-view";
import { firstParam } from "@/features/players/format";
import { parseSeason, Prefetched } from "@/features/venues/prefetch";

export const metadata: Metadata = {
  title: "Fantasy leaderboards",
  description: "Dream11 points leaderboards: season totals, floor–median–ceiling, consistency and points per credit.",
};

export default async function FantasyPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const state = {
    season: parseSeason(sp.season) ?? CURRENT_FANTASY_SEASON,
    sort: parseSort(firstParam(sp.sort)),
    role: parseRole(firstParam(sp.role)),
    min: parseMinMatches(firstParam(sp.min)),
  };
  const query = { season: state.season, role: state.role, minMatches: state.min };
  return (
    <Prefetched queries={[{ queryKey: fantasyKeys.leaderboard(query), queryFn: (signal) => fetchLeaderboard(query, signal), staleTime: FANTASY_STALE_MS }]}>
      <FantasyLeaderboard state={state} />
    </Prefetched>
  );
}
