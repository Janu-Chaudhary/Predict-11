/**
 * TS mirror of backend/src/p11/analytics/seasons_schemas.py (the /api/v1 seasons contract).
 * Hand-written (not generated) so this feature does not depend on `pnpm gen:api`; keep in sync.
 * Dates arrive as ISO `YYYY-MM-DD` strings.
 */

export type FormResult = "W" | "L" | "N";

export type TeamRef = { id: number; name: string; short_code: string };
export type VenueRef = { id: number; name: string; city: string | null };
export type PlayerRef = { id: string; name: string };

/* ---------- seasons / teams ---------- */

export type SeasonSummary = {
  year: number;
  label: string;
  source_label: string;
  match_count: number;
  league_match_count: number;
  team_count: number;
  start_date: string;
  end_date: string;
  champion: TeamRef | null;
  runner_up: TeamRef | null;
};

export type TeamEra = { name: string; short_code: string; from_season: number; to_season: number };

export type TeamSummary = {
  id: number;
  name: string;
  short_code: string;
  active: boolean;
  seasons: number[];
  titles: number[];
  former_names: TeamEra[];
};

/* ---------- matches ---------- */

export type InningsScore = {
  innings: number;
  team_id: number;
  runs: number;
  wickets: number;
  overs: string;
  target_overs: string | null;
};

export type MatchSummary = {
  id: number;
  season: number;
  date: string;
  match_number: number | null;
  stage: string | null;
  venue: VenueRef | null;
  team1: TeamRef;
  team2: TeamRef;
  toss_winner_id: number | null;
  toss_decision: string | null;
  result: "win" | "tie" | "no_result";
  winner_id: number | null;
  margin_runs: number | null;
  margin_wickets: number | null;
  method: string | null;
  super_over: boolean;
  result_text: string;
  scores: InningsScore[];
};

/* ---------- points table ---------- */

export type PointsRow = {
  position: number;
  team: TeamRef;
  played: number;
  won: number;
  lost: number;
  no_result: number;
  tied: number;
  points: number;
  nrr: number;
  runs_for: number;
  overs_for: string;
  runs_against: number;
  overs_against: string;
  /** Last 5 league results, oldest first. */
  form: FormResult[];
  qualified: boolean;
};

export type PointsTable = {
  season: number;
  league_matches: number;
  after_match: number | null;
  rows: PointsRow[];
  tiebreak: string;
};

/* ---------- scenarios ---------- */

export type ScenarioFixture = {
  match_id: number;
  match_number: number | null;
  date: string;
  team1_id: number;
  team2_id: number;
  actual_winner_id: number | null;
  picked_winner_id: number | null;
};

export type ScenarioTeam = {
  team: TeamRef;
  played: number;
  points: number;
  wins: number;
  remaining: number;
  max_points: number;
  /** Top 4 on points (and wins) alone, no NRR needed. */
  p_top4: number;
  /** Top 4 possible once NRR breaks level teams. */
  p_top4_incl_ties: number;
  p_top4_tie_dependent: number;
  p_top2: number;
  p_top2_incl_ties: number;
  p_top2_tie_dependent: number;
  clinched_top4: boolean;
  eliminated: boolean;
  clinched_top2: boolean;
  out_of_top2: boolean;
};

export type ScenarioPick = { match_id: number; winner_id: number };
export type ScenarioRequest = { after_match: number | null; picks: ScenarioPick[] };

export type Scenarios = {
  season: number;
  after_match: number;
  league_matches: number;
  remaining_matches: number;
  method: "exhaustive" | "monte_carlo";
  outcomes_evaluated: number;
  flags_exact: boolean;
  assumption: string;
  teams: ScenarioTeam[];
  remaining: ScenarioFixture[];
};

/* ---------- story ---------- */

export type RaceSeries = { player: PlayerRef; team: TeamRef | null; total: number; cumulative: number[] };
export type CapRace = { dates: string[]; leaders: RaceSeries[] };

export type BattingLeader = {
  player: PlayerRef;
  team: TeamRef | null;
  innings: number;
  runs: number;
  balls: number;
  strike_rate: number;
  fours: number;
  sixes: number;
};

export type BowlingLeader = {
  player: PlayerRef;
  team: TeamRef | null;
  innings: number;
  overs: string;
  runs: number;
  wickets: number;
  economy: number;
};

export type SeasonStory = {
  season: number;
  orange_cap: CapRace;
  purple_cap: CapRace;
  most_sixes: BattingLeader[];
  best_strike_rate: BattingLeader[];
  best_economy: BowlingLeader[];
  min_balls_for_strike_rate: number;
  min_overs_for_economy: number;
};

/* ---------- head to head ---------- */

export type ResultLine = {
  match_id: number;
  season: number;
  date: string;
  venue: VenueRef | null;
  winner_id: number | null;
  result_text: string;
};

export type TeamTotalRecord = {
  match_id: number;
  season: number;
  date: string;
  team: TeamRef;
  opponent: TeamRef;
  venue: VenueRef | null;
  runs: number;
  wickets: number;
  overs: string;
};

export type VenueSplit = { venue: VenueRef; played: number; team_a_won: number; team_b_won: number; no_result: number };

export type HeadToHead = {
  team_a: TeamRef;
  team_b: TeamRef;
  season: number | null;
  venue_id: number | null;
  played: number;
  team_a_won: number;
  team_b_won: number;
  no_result: number;
  tied: number;
  last5: ResultLine[];
  team_a_highest: TeamTotalRecord | null;
  team_b_highest: TeamTotalRecord | null;
  team_a_lowest: TeamTotalRecord | null;
  team_b_lowest: TeamTotalRecord | null;
  by_venue: VenueSplit[];
};

/* ---------- records ---------- */

export type MarginRecord = {
  match_id: number;
  season: number;
  date: string;
  winner: TeamRef;
  loser: TeamRef;
  venue: VenueRef | null;
  margin: number;
  balls_remaining: number | null;
};

export type BattingInningsRecord = {
  match_id: number;
  season: number;
  date: string;
  player: PlayerRef;
  team: TeamRef;
  opponent: TeamRef;
  venue: VenueRef | null;
  runs: number;
  balls: number;
  not_out: boolean;
  fours: number;
  sixes: number;
  strike_rate: number;
};

export type BowlingFiguresRecord = {
  match_id: number;
  season: number;
  date: string;
  player: PlayerRef;
  team: TeamRef;
  opponent: TeamRef;
  venue: VenueRef | null;
  wickets: number;
  runs: number;
  overs: string;
};

export type PartnershipRecord = {
  match_id: number;
  season: number;
  date: string;
  team: TeamRef;
  opponent: TeamRef;
  venue: VenueRef | null;
  wicket: number;
  batter1: PlayerRef;
  batter2: PlayerRef;
  runs: number;
  balls: number;
  batter1_runs: number;
  batter2_runs: number;
};

export type FastestMilestone = {
  match_id: number;
  season: number;
  date: string;
  player: PlayerRef;
  team: TeamRef;
  opponent: TeamRef;
  venue: VenueRef | null;
  balls: number;
  final_runs: number;
};

export type Records = {
  scope: "all" | "season";
  season: number | null;
  venue_id: number | null;
  most_runs: BattingLeader[];
  most_wickets: BowlingLeader[];
  highest_totals: TeamTotalRecord[];
  lowest_totals: TeamTotalRecord[];
  biggest_wins_by_runs: MarginRecord[];
  biggest_wins_by_wickets: MarginRecord[];
  highest_individual_scores: BattingInningsRecord[];
  best_bowling_figures: BowlingFiguresRecord[];
  highest_partnerships: PartnershipRecord[];
  fastest_fifties: FastestMilestone[];
  fastest_hundreds: FastestMilestone[];
};

/* ---------- venues (owned by the venues agent; only the fields the filters need) ---------- */

export type VenueOption = { id: number; name: string; city: string | null; matches: number };
export type VenueList = { venues: VenueOption[] };
