/**
 * Fantasy (Dream11 points) view types for C1/C2/F3/H2.
 *
 * Raw responses mirror backend/src/p11/analytics/fantasy_schemas.py; `normalize.ts` maps them to
 * these view types (team refs → codes, cv → consistency score, multipliers → C/VC flags), so the
 * components never touch the wire format. Dates arrive as ISO strings.
 */
import type { Role } from "@/lib/tokens";

export type FantasyPlayerRef = {
  id: string;
  /** Scorecard name ("V Kohli"). */
  name: string;
  /** Full name ("Virat Kohli"); falls back to `name`. */
  display_name?: string | null;
  image_url?: string | null;
};

/** Points by Dream11 category (p11.scoring.CATEGORIES). */
export type CategoryMix = { batting: number; bowling: number; fielding: number; lineup: number; bonuses: number };

/** Floor / median / ceiling plus spread, over a set of matches. */
export type Distribution = {
  matches: number;
  total: number;
  mean: number | null;
  median: number | null;
  sd: number | null;
  p10: number | null;
  p90: number | null;
  max: number | null;
  /** 0–100, higher = steadier: 100 × (1 − sd/mean), clamped. */
  consistency: number | null;
  /** Share of matches with 50+ / 100+ points, 0–100. */
  pct_50: number | null;
  pct_100: number | null;
};

export type LeaderRow = Distribution & {
  rank: number | null;
  player: FantasyPlayerRef;
  /** Team code ("RR"). */
  team: string | null;
  role: Role | null;
  credits: number | null;
  /** Mean points per credit (null when the player has no credits). */
  ppc: number | null;
  /** Points in the player's last matches, oldest → newest (empty when the API doesn't send them). */
  recent: number[];
};

export type Leaderboard = {
  season: number | null;
  min_matches: number;
  /** Season whose credits apply (null = none stored for this season). */
  credits_season: number | null;
  credits_available: boolean;
  total_players: number | null;
  rows: LeaderRow[];
};

export type GameLog = { match_id: number; date: string | null; season: number | null; opponent: string | null; points: number };

export type SeasonDistribution = Distribution & { season: number; team: string | null; credits: number | null; credits_season: number | null; ppc: number | null };

export type PlayerFantasy = Distribution & {
  player: FantasyPlayerRef;
  role: Role | null;
  team: string | null;
  credits: number | null;
  credits_season: number | null;
  ppc: number | null;
  /** Total points by category. */
  mix: CategoryMix | null;
  /** Last 10 games, oldest → newest. */
  last10: GameLog[];
  by_season: SeasonDistribution[];
};

export type XiPick = {
  player: FantasyPlayerRef;
  team: string | null;
  role: Role;
  /** Actual base points in the match (or season total for the team of the season). */
  points: number;
  /** Actual points after the C ×2 / VC ×1.5 multiplier. */
  effective: number;
  /** What the picker optimised before the match (naive form XI: last-5 mean); null for hindsight. */
  projected: number | null;
  credits: number | null;
  captain: boolean;
  vice_captain: boolean;
  /** Team of the season only. */
  matches?: number | null;
  mean?: number | null;
};

export type Xi = { picks: XiPick[]; total: number; credits_used: number | null; credits_constrained: boolean };

export type MatchMeta = {
  match_id: number;
  date: string | null;
  season: number | null;
  match_number: number | null;
  stage: string | null;
  home: string | null;
  away: string | null;
  home_name: string | null;
  away_name: string | null;
  venue: string | null;
  result: string | null;
};

export type MatchBestXi = MatchMeta & {
  no_result: boolean;
  best: Xi | null;
  best_with_credits: Xi | null;
  naive: Xi | null;
  /** best.total − naive.total. */
  gap: number | null;
  credits_season: number | null;
  /** Players left out of the credit-capped pool because they have no credits. */
  without_credits: number;
};

export type SeasonXi = { metric: "total" | "mean"; min_matches: number; picks: XiPick[]; sum_total: number; sum_mean: number };

export type TeamOfSeason = { season: number; by_total: SeasonXi | null; by_mean: SeasonXi | null };

export type SeasonMatchXi = MatchMeta & {
  best_total: number;
  naive_total: number | null;
  gap: number | null;
  best_with_credits_total: number | null;
  captain: FantasyPlayerRef | null;
  top_scorer: FantasyPlayerRef | null;
  top_points: number | null;
};

export type SeasonBestXis = {
  season: number;
  credits_season: number | null;
  matches: SeasonMatchXi[];
  no_result_matches: number;
  mean_best: number | null;
  max_best: number | null;
  mean_naive: number | null;
  mean_gap: number | null;
};

export type LeaderSort = "total" | "mean" | "consistency" | "ppc";
export type RoleFilter = Role | "ALL";

/** Marks a response that came from the local fixture because the endpoint isn't live. */
export type Sampled<T> = T & { __sample?: boolean };
