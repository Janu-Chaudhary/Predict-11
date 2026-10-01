"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError } from "../players/api";
import type { StatFilter } from "../players/types";
import {
  FANTASY_STALE_MS,
  fantasyKeys,
  fetchLeaderboard,
  fetchMatchBestXi,
  fetchPlayerFantasy,
  fetchSeasonBestXis,
  fetchTeamOfSeason,
  type LeaderboardQuery,
} from "./api";

/** Don't retry 4xx; retry a network blip once. */
const retry = (n: number, err: unknown) => !(err instanceof ApiError && err.status !== null && err.status < 500) && n < 1;

export function useLeaderboard(q: LeaderboardQuery) {
  return useQuery({
    queryKey: fantasyKeys.leaderboard(q),
    queryFn: ({ signal }) => fetchLeaderboard(q, signal),
    placeholderData: keepPreviousData,
    staleTime: FANTASY_STALE_MS,
    retry,
  });
}

export function usePlayerFantasy(id: string, filter: StatFilter = {}) {
  return useQuery({
    queryKey: fantasyKeys.player(id, filter),
    queryFn: ({ signal }) => fetchPlayerFantasy(id, filter, signal),
    placeholderData: keepPreviousData,
    staleTime: FANTASY_STALE_MS,
    retry,
  });
}

export function useMatchBestXi(id: number) {
  return useQuery({ queryKey: fantasyKeys.matchXi(id), queryFn: ({ signal }) => fetchMatchBestXi(id, signal), staleTime: FANTASY_STALE_MS, retry });
}

export function useTeamOfSeason(season: number) {
  return useQuery({
    queryKey: fantasyKeys.teamOfSeason(season),
    queryFn: ({ signal }) => fetchTeamOfSeason(season, signal),
    placeholderData: keepPreviousData,
    staleTime: FANTASY_STALE_MS,
    retry,
  });
}

export function useSeasonBestXis(season: number) {
  return useQuery({
    queryKey: fantasyKeys.seasonXis(season),
    queryFn: ({ signal }) => fetchSeasonBestXis(season, signal),
    placeholderData: keepPreviousData,
    staleTime: FANTASY_STALE_MS,
    retry,
  });
}
