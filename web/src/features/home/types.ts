/**
 * Types for /api/v1/home/* (mirrors backend/src/p11/analytics/home_schemas.py).
 * Hand-written so the home feature does not depend on regenerating the shared schema.ts.
 */

export type Phase = "pre_match" | "post_match" | "off_season";
export type HeroKind = "A" | "B" | "C";
export type BallKind = "dot" | "run" | "four" | "six" | "wicket";
export type Role = "WK" | "BAT" | "AR" | "BOWL";

export type HomeTeam = { id: number; name: string; short_code: string };
export type HomeVenue = { id: number; name: string; city: string | null };
export type HomeScore = { innings: number; team_id: number; runs: number; wickets: number; overs: string };

export type HomeMatch = {
  id: number;
  date: string;
  season: number;
  title: string;
  stage: string | null;
  match_number: number | null;
  venue: HomeVenue | null;
  team1: HomeTeam;
  team2: HomeTeam;
  winner_id: number | null;
  result: string;
  scores: HomeScore[];
};

export type NextFixture = {
  id: number | null;
  start: string;
  title: string;
  venue: HomeVenue | null;
  team1: HomeTeam;
  team2: HomeTeam;
  status: "provisional" | "xi_confirmed";
};

export type SeasonCard = {
  year: number;
  champion: HomeTeam | null;
  runner_up: HomeTeam | null;
  final_match_id: number | null;
  next_season: string;
};

export type HomeState = {
  phase: Phase;
  now: string;
  hero: HeroKind;
  hero_match_id: number | null;
  hero_reason: string;
  next_fixture: NextFixture | null;
  last_match: HomeMatch | null;
  season: SeasonCard | null;
};

export type WormBall = { x: number; runs: number; wickets: number; kind: BallKind; label: string };
export type WormInnings = {
  innings: number;
  team: HomeTeam;
  runs: number;
  wickets: number;
  overs: string;
  balls: WormBall[];
};
export type Worm = { match: HomeMatch; innings: WormInnings[]; ball_count: number; y_max: number };

export type Shot = {
  over: number;
  ball: number;
  label: string;
  runs: number;
  direction: number;
  distance_pct: number;
  zone: number;
  zone_name: string;
  bowler: string;
};
export type Wagon = {
  match_id: number;
  batter: string;
  team: HomeTeam | null;
  runs: number;
  balls: number | null;
  not_out: boolean | null;
  left_handed: boolean;
  shots: Shot[];
  source: string;
};

export type XIPlayer = {
  id: string;
  name: string;
  short_name: string;
  team: string;
  role: Role;
  points: number;
  picked: boolean;
  captain: "C" | "VC" | null;
};
export type XI = { match_id: number; kind: "actual"; teams: string[]; players: XIPlayer[]; total: number };

export type PlayerStatLine = { id: string; name: string; team: string | null; value: number };
export type HomeTiles = {
  table: { season: number; leader: HomeTeam; leader_points: number; played: number; champion: HomeTeam | null } | null;
  players: { season: number; top_runs: PlayerStatLine | null; top_wickets: PlayerStatLine | null } | null;
  h2h: { team_a: HomeTeam; team_b: HomeTeam; matches: number; a_wins: number; b_wins: number } | null;
  venues: { season: number; venues_used: number; top_par_venue: HomeVenue | null; top_par: number | null } | null;
  records: { team: HomeTeam; opponent: HomeTeam; runs: number; wickets: number; year: number; match_id: number } | null;
  /** Season's top Dream11 scorer (older APIs omit the key). */
  fantasy?: { season: number; top: PlayerStatLine; matches: number; mean: number } | null;
};

/** What the hero area finally renders, after data availability is checked. */
export type ResolvedHero =
  | { kind: "A"; wagon: Wagon; match: HomeMatch | null; note: string }
  | { kind: "B"; xi: XI; match: HomeMatch | null; note: string }
  | { kind: "C"; worm: Worm; note: string }
  | { kind: "none"; note: string };

export type HomeData = {
  state: HomeState | null;
  hero: ResolvedHero;
  tiles: HomeTiles | null;
  /** Set when the API could not be reached at all. */
  error: string | null;
};
