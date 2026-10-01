import { getJson } from "@/features/venues/api";

import type { MilestonesResponse, StreaksResponse } from "./types";

export const recordKeys = {
  milestones: (season: number | null) => ["records", "milestones", season ?? "latest"] as const,
  streaks: (season: number | null) => ["records", "streaks", season ?? "all"] as const,
};

export const fetchMilestones = (season: number | null, signal?: AbortSignal) =>
  getJson<MilestonesResponse>(season ? `/milestones?season=${season}` : "/milestones", signal);

/** All boards in one call (the `type` filter is applied client-side so switching is instant). */
export const fetchStreaks = (season: number | null, signal?: AbortSignal) =>
  getJson<StreaksResponse>(season ? `/streaks?season=${season}&limit=10` : "/streaks?limit=10", signal);

export const RECORDS_STALE_MS = 10 * 60_000;
