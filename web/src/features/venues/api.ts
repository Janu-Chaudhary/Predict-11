import { API_URL } from "@/lib/env";

import type { VenueCard, VenueList } from "./types";

/** Error carrying the HTTP status so the UI can tell "not found" from "API down". */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** GET a JSON body from the Predict-11 API. Works in server and client components. */
export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1${path}`, { signal, headers: { accept: "application/json" } });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError("The API is unreachable.", null);
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const venueKeys = {
  list: ["venues", "list"] as const,
  card: (id: number) => ["venues", "card", id] as const,
};

export const fetchVenues = (signal?: AbortSignal) => getJson<VenueList>("/venues", signal);
export const fetchVenue = (id: number, signal?: AbortSignal) => getJson<VenueCard>(`/venues/${id}`, signal);

/** Venue data changes once per harvested match: keep it for 10 minutes. */
export const VENUE_STALE_MS = 10 * 60_000;
