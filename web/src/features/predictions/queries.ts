"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError } from "../players/api";
import { PRED_STALE_MS, fetchMatchPrediction, fetchSeasonPredictions, predKeys } from "./api";

/** Don't retry 4xx (404 = no honest prediction); retry a network blip once. */
const retry = (n: number, err: unknown) => !(err instanceof ApiError && err.status !== null && err.status < 500) && n < 1;

export function useSeasonPredictions(year: number) {
  return useQuery({
    queryKey: predKeys.season(year),
    queryFn: ({ signal }) => fetchSeasonPredictions(year, signal),
    staleTime: PRED_STALE_MS,
    placeholderData: keepPreviousData,
    retry,
  });
}

export function useMatchPrediction(id: number) {
  return useQuery({ queryKey: predKeys.match(id), queryFn: ({ signal }) => fetchMatchPrediction(id, signal), staleTime: PRED_STALE_MS, retry });
}

export const isNotFound = (err: unknown) => err instanceof ApiError && err.status === 404;
