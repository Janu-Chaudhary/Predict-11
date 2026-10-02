"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError, getJson } from "./api";
import type { PlayerRef } from "./types";

/**
 * D2 type-level matchups. Mirrors backend/src/p11/analytics/conditions_models.py
 * (BatterVsTypes, BowlerVsHands).
 */
export type Coverage = { balls: number; balls_known: number; unknown_pct: number | null; opponents: number; opponents_known: number };

export type TypeSplit = {
  /** Normalised bowling type ("leg-spin"), or "pace" / "spin" in by_group. */
  bowling_type: string;
  group: string;
  balls: number;
  runs: number;
  dismissals: number;
  strike_rate: number | null;
  average: number | null;
  dot_pct: number | null;
  boundary_pct: number | null;
  fours: number;
  sixes: number;
  bowlers: number;
  confidence: string;
};

export type BatterVsTypes = { batter: PlayerRef; batting_hand: string | null; season?: number | null; since: string | null; by_type: TypeSplit[]; by_group: TypeSplit[]; coverage: Coverage; notes: string[] };

export type HandSplit = {
  hand: string;
  label: string;
  balls: number;
  runs_conceded: number;
  wickets: number;
  economy: number | null;
  /** Balls per wicket. */
  strike_rate: number | null;
  average: number | null;
  dot_pct: number | null;
  boundary_pct: number | null;
  batters: number;
  confidence: string;
};

export type BowlerVsHands = { bowler: PlayerRef; bowling_type: string | null; group: string | null; season?: number | null; since: string | null; by_hand: HandSplit[]; coverage: Coverage; notes: string[] };

export const fetchBatterVsTypes = (id: string, since?: string, signal?: AbortSignal, season?: number) =>
  getJson<BatterVsTypes>(`/matchups/batter/${encodeURIComponent(id)}/vs-bowling-types`, { since, season }, signal);

export const fetchBowlerVsHands = (id: string, since?: string, signal?: AbortSignal, season?: number) =>
  getJson<BowlerVsHands>(`/matchups/bowler/${encodeURIComponent(id)}/vs-batting-hand`, { since, season }, signal);

const retry = (n: number, err: unknown) => !(err instanceof ApiError && err.status !== null && err.status < 500) && n < 1;

export function useBatterVsTypes(id: string | undefined, since?: string, enabled = true, season?: number) {
  return useQuery({
    queryKey: ["matchups", "batter-types", id ?? null, since ?? null, season ?? null] as const,
    queryFn: ({ signal }) => fetchBatterVsTypes(id!, since, signal, season),
    enabled: Boolean(id) && enabled,
    placeholderData: keepPreviousData,
    staleTime: 10 * 60_000,
    retry,
  });
}

export function useBowlerVsHands(id: string | undefined, since?: string, enabled = true, season?: number) {
  return useQuery({
    queryKey: ["matchups", "bowler-hands", id ?? null, since ?? null, season ?? null] as const,
    queryFn: ({ signal }) => fetchBowlerVsHands(id!, since, signal, season),
    enabled: Boolean(id) && enabled,
    placeholderData: keepPreviousData,
    staleTime: 10 * 60_000,
    retry,
  });
}

/** "right-arm fast" → "Right-arm fast". */
export const typeLabel = (t: string) => (t ? t[0].toUpperCase() + t.slice(1) : t);

/** "Unknown type 4.2% of balls" note, or null when coverage is complete. */
export function unknownNote(c: Coverage | null | undefined, what: "bowling type" | "batting hand"): string | null {
  if (!c || c.unknown_pct === null || c.unknown_pct <= 0) return null;
  const pct = c.unknown_pct < 0.1 ? "<0.1" : c.unknown_pct.toFixed(1);
  return `Unknown ${what} for ${pct}% of balls (${(c.balls - c.balls_known).toLocaleString("en-IN")} of ${c.balls.toLocaleString("en-IN")}); those balls are left out of the splits.`;
}
