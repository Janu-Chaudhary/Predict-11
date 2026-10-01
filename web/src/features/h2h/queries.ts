"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError, getJson } from "../players/api";
import type { H2HResponse } from "./types";

export type H2HQuery = { batter?: string; bowler?: string; since?: string };

export function fetchH2H(q: H2HQuery, signal?: AbortSignal) {
  return getJson<H2HResponse>("/h2h", { batter: q.batter, bowler: q.bowler, since: q.since, limit: 8 }, signal);
}

export function useH2H(q: H2HQuery) {
  return useQuery({
    queryKey: ["h2h", q.batter ?? null, q.bowler ?? null, q.since ?? null] as const,
    queryFn: ({ signal }) => fetchH2H(q, signal),
    enabled: Boolean(q.batter || q.bowler),
    placeholderData: keepPreviousData,
    staleTime: 10 * 60_000,
    retry: (n, err) => !(err instanceof ApiError && err.status !== null && err.status < 500) && n < 1,
  });
}
