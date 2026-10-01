/**
 * Mirrors the Pydantic models in backend/src/p11/analytics/players_models.py.
 * Hand-written (no `pnpm gen:api`) while the backend contract settles; dates arrive as ISO strings.
 */

export type PlayerRef = { id: string; name: string };

export type BattingStats = {
  innings: number;
  not_outs: number;
  runs: number;
  balls: number;
  average: number | null;
  strike_rate: number | null;
  fifties: number;
  hundreds: number;
  thirties: number;
  ducks: number;
  fours: number;
  sixes: number;
  dot_pct: number | null;
  highest: string | null;
};

export type BowlingStats = {
  innings: number;
  overs: string;
  balls: number;
  runs: number;
  wickets: number;
  economy: number | null;
  average: number | null;
  strike_rate: number | null;
  best: string | null;
  three_plus: number;
  four_plus: number;
  five_plus: number;
  maidens: number;
  dot_pct: number | null;
};

export type FieldingStats = { catches: number; stumpings: number; run_outs: number };

export type PhaseBatting = {
  phase: string;
  balls: number;
  runs: number;
  outs: number;
  strike_rate: number | null;
  boundary_pct: number | null;
};

export type PhaseBowling = {
  phase: string;
  balls: number;
  runs: number;
  wickets: number;
  economy: number | null;
  dot_pct: number | null;
};

export type SeasonLine = {
  season: number;
  team: string | null;
  matches: number;
  batting: BattingStats;
  bowling: BowlingStats;
  fielding: FieldingStats;
};

export type Split = {
  id: number;
  name: string;
  matches: number;
  batting: BattingStats;
  bowling: BowlingStats;
};

export type FormBat = {
  match_id: number;
  date: string;
  season: number;
  opponent: string | null;
  venue: string | null;
  runs: number;
  balls: number;
  not_out: boolean;
  how_out: string | null;
  score: string;
};

export type FormBowl = {
  match_id: number;
  date: string;
  season: number;
  opponent: string | null;
  venue: string | null;
  overs: string;
  runs: number;
  wickets: number;
  figures: string;
};

export type TeamSpan = { id: number; name: string; first_season: number; last_season: number; matches: number };

export type Filters = { season: number | null; since: string | null };

export type PlayerProfile = {
  id: string;
  name: string;
  unique_name: string;
  aliases: string[];
  filters: Filters;
  matches: number;
  seasons: number[];
  last_team: string | null;
  teams: TeamSpan[];
  debut: string | null;
  last_match: string | null;
  batting: BattingStats;
  bowling: BowlingStats;
  fielding: FieldingStats;
  batting_phases: PhaseBatting[];
  bowling_phases: PhaseBowling[];
  by_season: SeasonLine[];
  venues: Split[];
  vs_teams: Split[];
  /** last 10 innings, newest first */
  form_batting: FormBat[];
  /** last 10 bowling innings, newest first */
  form_bowling: FormBowl[];
};

export type CompareEntry = {
  id: string;
  name: string;
  matches: number;
  last_team: string | null;
  batting: BattingStats;
  bowling: BowlingStats;
  fielding: FieldingStats;
  batting_phases: PhaseBatting[];
  bowling_phases: PhaseBowling[];
};

export type CompareResponse = { filters: Filters; players: CompareEntry[] };

export type SearchHit = {
  id: string;
  name: string;
  /** name or alias that matched the query */
  matched: string;
  /** last IPL team (full name) */
  team: string | null;
  first_season: number | null;
  last_season: number | null;
  seasons: number;
  matches: number;
};

export type SearchResponse = { query: string; results: SearchHit[] };

/** Season / since filter shared by profile and compare. */
export type StatFilter = { season?: number; since?: string };
