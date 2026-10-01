"use client";

import { useQuery } from "@tanstack/react-query";

import { ApiError, VENUE_STALE_MS, fetchVenue, fetchVenues, venueKeys } from "./api";

const retry = (n: number, e: Error) => !(e instanceof ApiError && e.status === 404) && n < 2;

export function useVenues() {
  return useQuery({
    queryKey: venueKeys.list,
    queryFn: ({ signal }) => fetchVenues(signal),
    staleTime: VENUE_STALE_MS,
    retry,
  });
}

export function useVenue(id: number) {
  return useQuery({
    queryKey: venueKeys.card(id),
    queryFn: ({ signal }) => fetchVenue(id, signal),
    staleTime: VENUE_STALE_MS,
    retry,
  });
}
