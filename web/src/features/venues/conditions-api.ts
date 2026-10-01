import { getJson } from "./api";

/**
 * Venue extras from /venues/{id}/toss-trend, /pace-spin and /dew. Mirrors TossTrend, PaceSpin and
 * DewReport in backend/src/p11/analytics/conditions_models.py.
 */
export type TossSeason = {
  season: number;
  matches: number;
  toss_field_pct: number | null;
  toss_winner_win_pct: number | null;
  chase_win_pct: number | null;
  decided: number;
};

export type TossTrend = { venue_id: number; venue: string; seasons: TossSeason[]; recent: TossSeason; all_time: TossSeason; notes: string[] };

export type BowlGroupLine = {
  /** pace | spin | unknown, or a bowling type in by_type. */
  group: string;
  balls: number;
  overs: string;
  runs: number;
  wickets: number;
  economy: number | null;
  strike_rate: number | null;
  average: number | null;
  overs_share_pct: number | null;
  wickets_share_pct: number | null;
};

export type PaceSpinWindow = { window: string; matches: number; groups: BowlGroupLine[]; by_type: BowlGroupLine[]; unknown_ball_pct: number | null };
export type PaceSpin = { venue_id: number; venue: string; recent: PaceSpinWindow; all_time: PaceSpinWindow; notes: string[] };

export type DewBucket = { matches: number; chase_wins: number; chase_win_pct: number | null };
export type DewSeason = {
  season: number;
  evening_matches: number;
  with_weather: number;
  avg_spread: number | null;
  avg_humidity: number | null;
  high_dew_matches: number;
  high_dew: DewBucket;
  low_dew: DewBucket;
};
export type DewReport = { venue_id: number | null; venue: string | null; high_dew_spread_c: number; seasons: DewSeason[]; total: DewSeason; recent: DewSeason; notes: string[] };

export const conditionKeys = {
  toss: (id: number) => ["venues", "toss-trend", id] as const,
  paceSpin: (id: number) => ["venues", "pace-spin", id] as const,
  dew: (id: number) => ["venues", "dew", id] as const,
};

export const fetchTossTrend = (id: number, signal?: AbortSignal) => getJson<TossTrend>(`/venues/${id}/toss-trend`, signal);
export const fetchPaceSpin = (id: number, signal?: AbortSignal) => getJson<PaceSpin>(`/venues/${id}/pace-spin`, signal);
export const fetchDew = (id: number, signal?: AbortSignal) => getJson<DewReport>(`/venues/${id}/dew`, signal);
