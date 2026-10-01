"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchHealth } from "./client";

export const queryKeys = {
  health: ["health"] as const,
};

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 60_000,
    retry: 1,
  });
}
