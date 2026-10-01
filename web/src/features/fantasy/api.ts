import { getJson } from "../players/api";
import type { StatFilter } from "../players/types";
import { leaderboard, matchBestXi, playerFantasy, seasonBestXis, teamOfSeason } from "./normalize";
import type { Leaderboard, MatchBestXi, PlayerFantasy, RoleFilter, SeasonBestXis, TeamOfSeason } from "./types";

export type LeaderboardQuery = { season: number | null; role: RoleFilter; minMatches: number };

export const fantasyKeys = {
  leaderboard: (q: LeaderboardQuery) => ["fantasy", "leaderboard", q.season, q.role, q.minMatches] as const,
  player: (id: string, f: StatFilter = {}) => ["fantasy", "player", id, f.season ?? null, f.since ?? null] as const,
  matchXi: (id: number) => ["fantasy", "match-xi", id] as const,
  teamOfSeason: (season: number) => ["fantasy", "team-of-season", season] as const,
  seasonXis: (season: number) => ["fantasy", "season-xis", season] as const,
};

/** Fantasy points change once per harvested match; the API also sends an ETag. */
export const FANTASY_STALE_MS = 10 * 60_000;

/** Enough rows that client-side re-sorting never hides a player the server ranked lower. */
const LEADERBOARD_LIMIT = 500;

export async function fetchLeaderboard(q: LeaderboardQuery, signal?: AbortSignal): Promise<Leaderboard> {
  const raw = await getJson("/fantasy/leaderboard", { season: q.season, role: q.role === "ALL" ? undefined : q.role, min_matches: q.minMatches, limit: LEADERBOARD_LIMIT }, signal);
  return leaderboard(raw);
}

export async function fetchPlayerFantasy(id: string, filter: StatFilter = {}, signal?: AbortSignal): Promise<PlayerFantasy> {
  return playerFantasy(await getJson(`/fantasy/players/${encodeURIComponent(id)}`, { season: filter.season, since: filter.since }, signal));
}

export async function fetchMatchBestXi(matchId: number, signal?: AbortSignal): Promise<MatchBestXi> {
  return matchBestXi(await getJson(`/fantasy/matches/${matchId}/best-xi`, {}, signal));
}

export async function fetchTeamOfSeason(season: number, signal?: AbortSignal): Promise<TeamOfSeason> {
  return teamOfSeason(await getJson(`/fantasy/seasons/${season}/team-of-season`, {}, signal));
}

export async function fetchSeasonBestXis(season: number, signal?: AbortSignal): Promise<SeasonBestXis> {
  return seasonBestXis(await getJson(`/fantasy/seasons/${season}/best-xis`, {}, signal));
}
