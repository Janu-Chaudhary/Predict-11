"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError, fetchCompare, fetchPlayerProfile, fetchPlayerSearch } from "./api";
import type { StatFilter } from "./types";

export const playerKeys = {
  search: (q: string) => ["players", "search-hits", q] as const,
  profile: (id: string, f: StatFilter) => ["players", "profile", id, f.season ?? null, f.since ?? null] as const,
  compare: (ids: string[], f: StatFilter) => ["players", "compare", ids.join(","), f.season ?? null, f.since ?? null] as const,
};

/** Don't retry 4xx (bad id, validation); retry network blips once. */
const retry = (count: number, err: unknown) => !(err instanceof ApiError && err.status !== null && err.status < 500) && count < 1;

export function usePlayerSearchHits(q: string, limit = 8) {
  const term = q.trim();
  return useQuery({
    queryKey: playerKeys.search(`${term.toLowerCase()}|${limit}`),
    queryFn: ({ signal }) => fetchPlayerSearch(term, limit, signal),
    enabled: term.length >= 2,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
    retry,
  });
}

export function usePlayerProfile(id: string, filter: StatFilter = {}) {
  return useQuery({
    queryKey: playerKeys.profile(id, filter),
    queryFn: ({ signal }) => fetchPlayerProfile(id, filter, signal),
    placeholderData: keepPreviousData,
    staleTime: 10 * 60_000,
    retry,
  });
}

export function usePlayerCompare(ids: string[], filter: StatFilter = {}) {
  return useQuery({
    queryKey: playerKeys.compare(ids, filter),
    queryFn: ({ signal }) => fetchCompare(ids, filter, signal),
    enabled: ids.length >= 1,
    placeholderData: keepPreviousData,
    staleTime: 10 * 60_000,
    retry,
  });
}
