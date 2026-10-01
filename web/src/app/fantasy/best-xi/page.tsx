import type { Metadata } from "next";

import { FANTASY_STALE_MS, fantasyKeys, fetchSeasonBestXis, fetchTeamOfSeason } from "@/features/fantasy/api";
import { BestXiView } from "@/features/fantasy/best-xi-view";
import { CURRENT_FANTASY_SEASON } from "@/features/fantasy/leaderboard-view";
import { parseSeason, Prefetched } from "@/features/venues/prefetch";

export const metadata: Metadata = {
  title: "Best XIs",
  description: "Team of the season and the hindsight Dream Team for every IPL match, against a pick-on-form XI.",
};

export default async function BestXiPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const season = parseSeason((await searchParams).season) ?? CURRENT_FANTASY_SEASON;
  return (
    <Prefetched
      queries={[
        { queryKey: fantasyKeys.teamOfSeason(season), queryFn: (signal) => fetchTeamOfSeason(season, signal), staleTime: FANTASY_STALE_MS },
        { queryKey: fantasyKeys.seasonXis(season), queryFn: (signal) => fetchSeasonBestXis(season, signal), staleTime: FANTASY_STALE_MS },
      ]}
    >
      <BestXiView season={season} />
    </Prefetched>
  );
}
