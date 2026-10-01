/**
 * Local types for the venue endpoints (GET /api/v1/venues, /venues/{id}).
 * Mirrors `backend/src/p11/analytics/venues.py` (VenueList, VenueCard). Written by hand so this
 * feature does not depend on `pnpm gen:api`; swap for the generated types once they land.
 */

export type PlayerRef = { id: string; name: string };

export type VenueSummary = {
  id: number;
  name: string;
  city: string | null;
  matches: number;
  matches_recent: number;
  first_season: number | null;
  last_season: number | null;
  par_recent: number | null;
  par_all_time: number | null;
  chase_win_pct_recent: number | null;
};

export type VenueList = {
  /** First season of the "recent" window (2023 = impact-player era). */
  recent_from: number;
  venues: VenueSummary[];
};

export type ParStats = {
  matches: number;
  avg_first_innings: number | null;
  median_first_innings: number | null;
  avg_second_innings: number | null;
  chase_win_pct: number | null;
  bat_first_win_pct: number | null;
};

export type TossStats = {
  matches: number;
  chose_field: number;
  chose_bat: number;
  field_pct: number | null;
  toss_winner_win_pct: number | null;
  toss_winner_win_pct_when_field: number | null;
  toss_winner_win_pct_when_bat: number | null;
};

export type PhaseRate = {
  phase: string;
  run_rate: number | null;
  wickets_per_innings: number | null;
};

export type TeamTotal = {
  match_id: number;
  date: string;
  season: number;
  team: string | null;
  opponent: string | null;
  innings: number;
  runs: number;
  wickets: number;
  overs: string;
  /** e.g. "287/3 (20)" */
  score: string;
};

export type VenueLeader = {
  player: PlayerRef;
  innings: number;
  value: number;
  /** Batting SR (run-scorers) or economy (wicket-takers). */
  rate: number | null;
};

export type SeasonTrend = {
  season: number;
  matches: number;
  avg_first_innings: number | null;
  /**
   * Per-season toss split. Not in the backend contract yet (2026-10-02); the card renders the
   * toss-trend chart when these arrive and falls back to the 2023+ vs all-time split otherwise.
   */
  chose_field?: number | null;
  chose_bat?: number | null;
  field_pct?: number | null;
};

export type VenueCard = {
  id: number;
  name: string;
  city: string | null;
  matches: number;
  first_match: string | null;
  last_match: string | null;
  /** Recency-weighted average 1st-innings total. */
  par_weighted: number | null;
  recent: ParStats;
  all_time: ParStats;
  toss_recent: TossStats;
  toss_all_time: TossStats;
  phases_recent: PhaseRate[];
  phases_all_time: PhaseRate[];
  by_season: SeasonTrend[];
  highest_totals: TeamTotal[];
  lowest_totals: TeamTotal[];
  top_run_scorers: VenueLeader[];
  top_wicket_takers: VenueLeader[];
  notes: string[];
};
