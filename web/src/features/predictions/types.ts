/**
 * Mirrors backend/src/p11/analytics/predictions.py (GET /api/v1/predictions/*). Only honest
 * pre-match predictions: the walk-forward season (retrained every block of matches on earlier
 * matches only) or the frozen-model test season.
 */
import type { Role } from "@/lib/tokens";

import type { ImageCredit } from "@/features/venues/types";

export type TeamSide = { id: number | string | null; name: string; short_code: string };

export type VenueRef = {
  id: number;
  name: string;
  city: string | null;
  image_url?: string | null;
  thumb_url?: string | null;
  image_credit?: ImageCredit | null;
};

export type InningsScore = { innings: number; team_id: number; runs: number; wickets: number; overs: string; target_overs: string | null };

export type MatchHeader = {
  match_id: number;
  date: string | null;
  season: number | null;
  match_number: number | null;
  stage: string | null;
  title: string;
  team1: TeamSide | null;
  team2: TeamSide | null;
  venue: VenueRef | null;
  venue_name: string | null;
  city: string | null;
  winner_id: number | null;
  result_text: string | null;
  scores: InningsScore[];
};

export type CaptainCall = {
  player: { id: string; name: string; image_url: string | null; team: string; role: Role };
  predicted: number | null;
  actual: number | null;
  points: number | null;
  actual_rank: number | null;
  top2: boolean | null;
};

export type SeasonMatch = {
  match: MatchHeader;
  n_players: number;
  model_xi_points: number | null;
  baseline_xi_points: number | null;
  best_xi_points: number | null;
  model_minus_baseline: number | null;
  model_beat_baseline: boolean | null;
  captain: CaptainCall | null;
  baseline_captain_top2: boolean | null;
  mae_model: number | null;
  mae_base: number | null;
  coverage: number | null;
};

export type CallRef = { match_id: number; title: string; margin: number };

export type SeasonStats = {
  matches: number;
  model_total: number | null;
  model_mean: number | null;
  baseline_total: number | null;
  baseline_mean: number | null;
  best_total: number | null;
  best_mean: number | null;
  model_share_of_best: number | null;
  captain_top2_model: number | null;
  captain_top2_baseline: number | null;
  beat_baseline: number;
  beat_baseline_rate: number | null;
  best_call: CallRef | null;
  worst_call: CallRef | null;
  mae_model: number | null;
  mae_base: number | null;
};

export type PredPhase = "walkforward" | "test";

export type SeasonOption = { year: number; phase: PredPhase; frozen: boolean; matches: number };

export type SeasonPredictions = {
  version: string;
  year: number;
  phase: PredPhase;
  frozen: boolean;
  method_note: string;
  credits_note: string;
  wf_block: number | null;
  seasons: SeasonOption[];
  summary: SeasonStats;
  matches: SeasonMatch[];
};

export type XiPlayer = {
  player_id: string;
  name: string;
  image_url: string | null;
  team: string;
  team_name: string;
  role: Role;
  multiplier: number;
  selected_on: number;
  pred_mean: number | null;
  q10: number | null;
  q50: number | null;
  q90: number | null;
  baseline: number | null;
  actual: number | null;
  points: number | null;
  credits: number | null;
};

export type XiKey = "model" | "baseline" | "best";

export type XiCard = {
  key: XiKey;
  label: string;
  picks: XiPlayer[];
  captain: string | null;
  vice_captain: string | null;
  actual_points: number | null;
  selected_on: number;
  credits_total: number | null;
  credits_complete: boolean;
  overlap_with_best: number;
};

export type PlayerRow = {
  player_id: string;
  name: string;
  image_url: string | null;
  team: string;
  team_name: string;
  role: Role;
  pred_mean: number | null;
  q10: number | null;
  q50: number | null;
  q90: number | null;
  baseline: number | null;
  actual: number | null;
  in_model_xi: boolean;
  in_base_xi: boolean;
  in_best_xi: boolean;
  model_mult: number | null;
  base_mult: number | null;
  best_mult: number | null;
  actual_rank: number | null;
  credits: number | null;
};

export type MatchTotals = {
  model: number | null;
  baseline: number | null;
  best: number | null;
  model_minus_baseline: number | null;
  model_share_of_best: number | null;
  captain_top2_model: boolean | null;
  captain_top2_baseline: boolean | null;
  mae_model: number | null;
  mae_base: number | null;
  coverage: number | null;
};

export type MatchPrediction = {
  version: string;
  year: number | null;
  phase: PredPhase;
  frozen: boolean;
  method_note: string;
  credits_note: string;
  credits_season: number | null;
  match: MatchHeader;
  xis: Record<XiKey, XiCard | null>;
  players: PlayerRow[];
  totals: MatchTotals;
};

export type OptimiseResult = {
  match_id: number;
  xi: XiCard;
  projected: number;
  credits_constrained: boolean;
  credits_used: number | null;
  budget: number | null;
  note: string;
};
