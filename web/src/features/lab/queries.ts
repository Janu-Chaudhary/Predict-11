"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError } from "../players/api";
import { RUN_STALE_MS, RUNS_STALE_MS, fetchCompare, fetchExplain, fetchMatch, fetchMatches, fetchRuns, fetchTelemetry, labKeys } from "./api";
import type { Phase } from "./types";

/** Don't retry 4xx; retry a network blip once. */
const retry = (n: number, err: unknown) => !(err instanceof ApiError && err.status !== null && err.status < 500) && n < 1;

export function useRuns() {
  return useQuery({ queryKey: labKeys.runs(), queryFn: ({ signal }) => fetchRuns(signal), staleTime: RUNS_STALE_MS, retry });
}

export function useTelemetry(version: string | null) {
  return useQuery({
    queryKey: labKeys.telemetry(version ?? ""),
    queryFn: ({ signal }) => fetchTelemetry(version!, signal),
    enabled: Boolean(version),
    staleTime: RUN_STALE_MS,
    retry,
  });
}

export function useMatches(version: string | null, phase: Phase) {
  return useQuery({
    queryKey: labKeys.matches(version ?? "", phase),
    queryFn: ({ signal }) => fetchMatches(version!, phase, signal),
    enabled: Boolean(version),
    staleTime: RUN_STALE_MS,
    placeholderData: keepPreviousData,
    retry,
  });
}

export function useMatch(version: string | null, id: number | null) {
  return useQuery({
    queryKey: labKeys.match(version ?? "", id ?? 0),
    queryFn: ({ signal }) => fetchMatch(version!, id!, signal),
    enabled: Boolean(version) && id !== null,
    staleTime: RUN_STALE_MS,
    placeholderData: keepPreviousData,
    retry,
  });
}

export function useExplain(version: string | null, matchId: number | null, playerId: string | null) {
  return useQuery({
    queryKey: labKeys.explain(version ?? "", matchId ?? 0, playerId ?? ""),
    queryFn: ({ signal }) => fetchExplain(version!, matchId!, playerId!, signal),
    enabled: Boolean(version) && matchId !== null && Boolean(playerId),
    staleTime: RUN_STALE_MS,
    placeholderData: keepPreviousData,
    retry,
  });
}

export function useCompare(a: string | null, b: string | null) {
  return useQuery({
    queryKey: labKeys.compare(a ?? "", b ?? ""),
    queryFn: ({ signal }) => fetchCompare(a!, b!, signal),
    enabled: Boolean(a) && Boolean(b) && a !== b,
    staleTime: RUN_STALE_MS,
    retry,
  });
}
