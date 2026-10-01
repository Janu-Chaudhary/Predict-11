"use client";

import { useQuery } from "@tanstack/react-query";

import { ApiError, VENUE_STALE_MS } from "./api";
import { conditionKeys, fetchDew, fetchPaceSpin, fetchTossTrend } from "./conditions-api";

const retry = (n: number, e: Error) => !(e instanceof ApiError && e.status === 404) && n < 2;

export const useTossTrend = (id: number) => useQuery({ queryKey: conditionKeys.toss(id), queryFn: ({ signal }) => fetchTossTrend(id, signal), staleTime: VENUE_STALE_MS, retry });
export const usePaceSpin = (id: number) => useQuery({ queryKey: conditionKeys.paceSpin(id), queryFn: ({ signal }) => fetchPaceSpin(id, signal), staleTime: VENUE_STALE_MS, retry });
export const useDew = (id: number) => useQuery({ queryKey: conditionKeys.dew(id), queryFn: ({ signal }) => fetchDew(id, signal), staleTime: VENUE_STALE_MS, retry });
