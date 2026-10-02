"use client";

import { keepPreviousData, useQueries, useQuery } from "@tanstack/react-query";

import { fantasyKeys, FANTASY_STALE_MS, fetchPlayerFantasy } from "../../fantasy/api";
import { ApiError, fetchPlayerProfile, filterParams, getJson } from "../api";
import { fetchBatterVsTypes, fetchBowlerVsHands } from "../matchups";
import { playerKeys } from "../queries";
import type { Filters, PlayerProfile, StatFilter } from "../types";

/** Mirrors backend/src/p11/analytics/players_percentiles.py (GET /players/percentiles). */
export type PercentileAxis = { key: string; label: string; better: "high" | "low"; sample: string; population: number };
export type PercentileValue = { key: string; value: number | null; percentile: number | null };
export type PercentilesResponse = { filters: Filters; axes: PercentileAxis[]; players: { id: string; axes: PercentileValue[] }[] };

export const fetchPercentiles = (ids: string[], f: StatFilter = {}, signal?: AbortSignal) =>
  getJson<PercentilesResponse>("/players/percentiles", { ids: ids.join(","), ...filterParams(f) }, signal);

const STALE = 10 * 60_000;
/** Don't retry 4xx; retry a network blip once. */
const retry = (n: number, err: unknown) => !(err instanceof ApiError && err.status !== null && err.status < 500) && n < 1;

/** One profile per player (same cache entries as the profile page). */
export function useProfiles(ids: string[], filter: StatFilter) {
  return useQueries({
    queries: ids.map((id) => ({
      queryKey: playerKeys.profile(id, filter),
      queryFn: ({ signal }: { signal: AbortSignal }) => fetchPlayerProfile(id, filter, signal),
      placeholderData: keepPreviousData,
      staleTime: STALE,
      retry,
    })),
  });
}

export function useFantasies(ids: string[], filter: StatFilter) {
  return useQueries({
    queries: ids.map((id) => ({
      queryKey: fantasyKeys.player(id, filter),
      queryFn: ({ signal }: { signal: AbortSignal }) => fetchPlayerFantasy(id, filter, signal),
      placeholderData: keepPreviousData,
      staleTime: FANTASY_STALE_MS,
      retry,
    })),
  });
}

/** Batter vs pace/spin for players who batted, bowler vs RHB/LHB for players who bowled. */
export function useMatchups(players: (PlayerProfile | undefined)[], filter: StatFilter) {
  const since = filter.since;
  const season = filter.season;
  const bat = useQueries({
    queries: players.map((p) => ({
      queryKey: ["matchups", "batter-types", p?.id ?? null, since ?? null, season ?? null] as const,
      queryFn: ({ signal }: { signal: AbortSignal }) => fetchBatterVsTypes(p!.id, since, signal, season),
      enabled: Boolean(p && p.batting.balls > 0),
      staleTime: STALE,
      retry,
    })),
  });
  const bowl = useQueries({
    queries: players.map((p) => ({
      queryKey: ["matchups", "bowler-hands", p?.id ?? null, since ?? null, season ?? null] as const,
      queryFn: ({ signal }: { signal: AbortSignal }) => fetchBowlerVsHands(p!.id, since, signal, season),
      enabled: Boolean(p && p.bowling.balls > 0),
      staleTime: STALE,
      retry,
    })),
  });
  return { bat, bowl };
}

export function usePercentiles(ids: string[], filter: StatFilter) {
  return useQuery({
    queryKey: ["players", "percentiles", ids.join(","), filter.season ?? null, filter.since ?? null] as const,
    queryFn: ({ signal }) => fetchPercentiles(ids, filter, signal),
    enabled: ids.length >= 1,
    placeholderData: keepPreviousData,
    staleTime: STALE,
    retry,
  });
}
