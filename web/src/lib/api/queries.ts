"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchHealth } from "./client";
import { searchPlayers } from "./search";

export const queryKeys = {
  health: ["health"] as const,
  playerSearch: (q: string) => ["players", "search", q] as const,
};

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 60_000,
    retry: 1,
  });
}

/** Player search for the ⌘K palette. Disabled under 2 characters; keeps previous hits while typing. */
export function usePlayerSearch(q: string) {
  const term = q.trim();
  return useQuery({
    queryKey: queryKeys.playerSearch(term.toLowerCase()),
    queryFn: ({ signal }) => searchPlayers(term, signal),
    enabled: term.length >= 2,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
    retry: false,
  });
}
