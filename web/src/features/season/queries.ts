"use client";

import { keepPreviousData, useQueries, useQuery } from "@tanstack/react-query";

import { seasonApi } from "./api";
import type { ScenarioPick } from "./types";

const STATIC = 10 * 60_000; // historical data barely moves; the API also sends ETags

export const seasonKeys = {
  seasons: ["seasons"] as const,
  teams: ["teams"] as const,
  table: (year: number, after: number | null) => ["seasons", year, "table", after] as const,
  scenarios: (year: number, after: number | null) => ["seasons", year, "scenarios", after] as const,
  story: (year: number) => ["seasons", year, "story"] as const,
  h2h: (a: string, b: string, venue: number | null) => ["teams", a, "vs", b, venue] as const,
  records: (season: number | null, venue: number | null) => ["records", season, venue] as const,
  matches: (season: number | null, team: string | null) => ["matches", season, team] as const,
  venues: ["venues"] as const,
  squad: (teamId: number) => ["teams", teamId, "squad"] as const,
  fantasyLeaders: (season: number) => ["fantasy", "leaderboard", season, "top"] as const,
  worm: (matchId: number) => ["matches", matchId, "worm"] as const,
};

export function useSeasons() {
  return useQuery({ queryKey: seasonKeys.seasons, queryFn: ({ signal }) => seasonApi.seasons(signal), staleTime: STATIC });
}

export function useTeams() {
  return useQuery({ queryKey: seasonKeys.teams, queryFn: ({ signal }) => seasonApi.teams(signal), staleTime: STATIC });
}

export function usePointsTable(year: number, after: number | null = null) {
  return useQuery({
    queryKey: seasonKeys.table(year, after),
    queryFn: ({ signal }) => seasonApi.table(year, after, signal),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });
}

/** Final tables for several seasons at once (team page "season by season"). */
export function usePointsTables(years: number[]) {
  return useQueries({
    queries: years.map((y) => ({
      queryKey: seasonKeys.table(y, null),
      queryFn: ({ signal }: { signal: AbortSignal }) => seasonApi.table(y, null, signal),
      staleTime: STATIC,
    })),
  });
}

export function useScenarios(year: number, after: number | null) {
  return useQuery({
    queryKey: seasonKeys.scenarios(year, after),
    queryFn: ({ signal }) => seasonApi.scenarios(year, after, signal),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });
}

/**
 * "Pick the winners": POST the picks and keep the last good result on screen while the next one
 * computes (placeholderData). Keyed on the picks, so a newer pick cancels the in-flight request
 * via the query signal and only the latest result ever lands.
 */
export function useScenarioPicks(year: number, after: number | null, picks: ScenarioPick[]) {
  const sorted = [...picks].sort((a, b) => a.match_id - b.match_id);
  return useQuery({
    queryKey: [...seasonKeys.scenarios(year, after), "picks", sorted.map((p) => `${p.match_id}:${p.winner_id}`).join(",")],
    queryFn: ({ signal }) => seasonApi.pickScenarios(year, { after_match: after, picks: sorted }, signal),
    enabled: picks.length > 0,
    staleTime: Infinity,
    placeholderData: keepPreviousData,
    retry: 1,
  });
}

export function useSeasonStory(year: number) {
  return useQuery({ queryKey: seasonKeys.story(year), queryFn: ({ signal }) => seasonApi.story(year, signal), staleTime: STATIC });
}

export function useHeadToHead(a: string, b: string | null, venue: number | null) {
  return useQuery({
    queryKey: seasonKeys.h2h(a, b ?? "", venue),
    queryFn: ({ signal }) => seasonApi.headToHead(a, b!, { venue }, signal),
    enabled: Boolean(b),
    staleTime: STATIC,
    placeholderData: keepPreviousData,
  });
}

export function useRecords(season: number | null, venue: number | null) {
  return useQuery({
    queryKey: seasonKeys.records(season, venue),
    queryFn: ({ signal }) => seasonApi.records({ season, venue }, signal),
    staleTime: STATIC,
    placeholderData: keepPreviousData,
  });
}

export function useMatches(season: number | null, team: string | null) {
  return useQuery({
    queryKey: seasonKeys.matches(season, team),
    queryFn: ({ signal }) => seasonApi.matches({ season, team }, signal),
    staleTime: STATIC,
    placeholderData: keepPreviousData,
  });
}

/** Venue list for filters (owned by the venues API; failure just hides the filter). */
export function useVenueOptions() {
  return useQuery({
    queryKey: seasonKeys.venues,
    queryFn: ({ signal }) => seasonApi.venues(signal),
    staleTime: STATIC,
    retry: false,
    select: (d) => [...d.venues].sort((a, b) => b.matches - a.matches),
  });
}

export function useTeamSquad(teamId: number) {
  return useQuery({ queryKey: seasonKeys.squad(teamId), queryFn: ({ signal }) => seasonApi.squad(teamId, signal), staleTime: 10 * 60_000 });
}

/** Season fantasy points leaders (side rail). Optional: failure just hides the card. */
export function useFantasyLeaders(season: number) {
  return useQuery({
    queryKey: seasonKeys.fantasyLeaders(season),
    queryFn: ({ signal }) => seasonApi.fantasyLeaders(season, 5, signal),
    staleTime: STATIC,
    retry: false,
  });
}

/** Match header + ball-by-ball worm for the match centre. */
export function useMatchWorm(matchId: number | null) {
  return useQuery({
    queryKey: seasonKeys.worm(matchId ?? 0),
    queryFn: ({ signal }) => seasonApi.worm(matchId!, signal),
    enabled: matchId !== null,
    staleTime: STATIC,
    retry: (n, e) => n < 1 && !(e instanceof Error && "status" in e && (e as { status: number }).status === 404),
  });
}
