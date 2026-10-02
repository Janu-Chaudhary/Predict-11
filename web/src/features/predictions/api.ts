import { API_URL } from "@/lib/env";

import { ApiError, getJson } from "../players/api";
import type { MatchPrediction, OptimiseResult, SeasonPredictions } from "./types";

export const predKeys = {
  season: (year: number) => ["predictions", "season", year] as const,
  match: (id: number) => ["predictions", "match", id] as const,
};

/** A run's out-of-sample predictions never change; a new run lands at most a few times a day. */
export const PRED_STALE_MS = 10 * 60_000;

export const DEFAULT_SEASON = 2026;

export function fetchSeasonPredictions(year: number, signal?: AbortSignal): Promise<SeasonPredictions> {
  return getJson<SeasonPredictions>(`/predictions/seasons/${year}`, {}, signal);
}

export function fetchMatchPrediction(id: number, signal?: AbortSignal): Promise<MatchPrediction> {
  return getJson<MatchPrediction>(`/predictions/matches/${id}`, {}, signal);
}

/** Re-run the optimiser on a match's honest predictions with the builder's locks / excludes. */
export async function optimiseMatch(id: number, locks: string[], excludes: string[], signal?: AbortSignal): Promise<OptimiseResult> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1/predictions/matches/${id}/optimise`, {
      method: "POST",
      signal,
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify({ locks, excludes }),
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError("The stats API is unreachable.", null);
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep status */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as OptimiseResult;
}
