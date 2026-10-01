/** Mirrors the matchup models in backend/src/p11/analytics/players_models.py. */
import type { PlayerRef } from "../players/types";

export type EncounterSeason = { season: number; balls: number; runs: number; dismissals: number; strike_rate: number | null };

export type Encounter = {
  match_id: number;
  date: string;
  season: number;
  venue: string | null;
  balls: number;
  runs: number;
  out: boolean;
  how_out: string | null;
  /** "balls-runs-out", e.g. "9-14-1" */
  summary: string;
};

export type PairStats = {
  balls: number;
  runs: number;
  dismissals: number;
  how_out: Record<string, number>;
  strike_rate: number | null;
  average: number | null;
  dot_pct: number | null;
  boundary_pct: number | null;
  fours: number;
  sixes: number;
  matches: number;
  innings: number;
  /** low <12 balls, medium 12-29, high >=30 */
  confidence: string;
  by_season: EncounterSeason[];
  last_encounters: Encounter[];
};

export type MatchupRow = {
  player: PlayerRef;
  balls: number;
  runs: number;
  dismissals: number;
  strike_rate: number | null;
  dot_pct: number | null;
  boundary_pct: number | null;
  matches: number;
  confidence: string;
};

export type H2HResponse = {
  batter: PlayerRef | null;
  bowler: PlayerRef | null;
  since: string | null;
  min_balls: number;
  pair: PairStats | null;
  top_bowlers_vs_batter: MatchupRow[];
  top_batters_vs_bowler: MatchupRow[];
  notes: string[];
};
