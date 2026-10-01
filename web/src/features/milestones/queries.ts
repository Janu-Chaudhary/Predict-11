"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError } from "@/features/venues/api";

import { RECORDS_STALE_MS, fetchMilestones, fetchStreaks, recordKeys } from "./api";

const retry = (n: number, e: Error) => !(e instanceof ApiError && e.status === 404) && n < 2;

export function useMilestones(season: number | null) {
  return useQuery({
    queryKey: recordKeys.milestones(season),
    queryFn: ({ signal }) => fetchMilestones(season, signal),
    staleTime: RECORDS_STALE_MS,
    placeholderData: keepPreviousData,
    retry,
  });
}

export function useStreaks(season: number | null) {
  return useQuery({
    queryKey: recordKeys.streaks(season),
    queryFn: ({ signal }) => fetchStreaks(season, signal),
    staleTime: RECORDS_STALE_MS,
    placeholderData: keepPreviousData,
    retry,
  });
}
