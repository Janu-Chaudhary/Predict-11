import type { Role } from "@/lib/tokens";

/** Model vs baseline on one metric, with the paired-bootstrap 95% CI of the difference. */
export type Pair = { model: number | null; baseline: number | null; diff: number | null; ci: [number | null, number | null] };

export type EvalSummary = {
  matches: number | null;
  bestXi: Pair;
  hindsight: number | null;
  captain: Pair;
  mae: Pair;
  spearman: Pair;
  coverage: number | null;
};

export type PhaseKind = "cv" | "test" | "walkforward" | "other";
export type Phase = "test" | "walkforward";

export type PhaseHeadline = EvalSummary & { key: string };

export type RunSummary = {
  version: string;
  createdAt: string | null;
  isLatest: boolean;
  hasTelemetry: boolean;
  hasEvalFrame: boolean;
  hasBooster: boolean;
  inDb: boolean;
  nFeatures: number | null;
  nLearned: number | null;
  trees: Record<string, number>;
  durationS: number | null;
  params: Record<string, unknown>;
  test: PhaseHeadline | null;
  walkforward: PhaseHeadline | null;
};

export type Bin = { lo: number; hi: number; n: number };

export type FeatureInfo = {
  name: string;
  group: string;
  description: string;
  missingRate: number | null;
  mean: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  gain: number | null;
  split: number | null;
  shap: number | null;
};

export type Curve = { train: number[]; valid: number[]; metric: string; bestIter: number | null; iters: number | null };

export type TuningRow = { params: Record<string, unknown>; foldMae: Record<string, number>; meanMae: number | null; seconds: number | null };

export type Evaluation = { key: string; kind: PhaseKind; season: number | null; label: string; summary: EvalSummary };

export type PerMatch = {
  matchId: number;
  date: string | null;
  team1: string | null;
  team2: string | null;
  xiModel: number | null;
  xiBase: number | null;
  xiBest: number | null;
  capHitModel: boolean | null;
  capHitBase: boolean | null;
  maeModel: number | null;
  maeBase: number | null;
  rhoModel: number | null;
  rhoBase: number | null;
  covered: number | null;
};

export type ReliabilityBin = { predLo: number | null; predHi: number | null; predMean: number; actualMean: number; n: number };

export type Calibration = {
  key: string;
  coverage: { belowQ10: number | null; belowQ50: number | null; belowQ90: number | null; inside80: number | null };
  reliability: ReliabilityBin[];
  pinball: { q10: number | null; q50: number | null; q90: number | null };
};

export type ErrStat = { label: string; mae: number | null; bias: number | null; n: number | null };

export type Residuals = { key: string; hist: Bin[]; byRole: ErrStat[]; byExperience: ErrStat[]; byBatsFirst: ErrStat[] };

export type Contribution = { feature: string; value: number | null; shap: number; group?: string | null; description?: string | null };

export type ShapExample = {
  kind: string | null;
  matchId: number;
  playerId: string;
  playerName: string;
  team: string | null;
  pred: number | null;
  actual: number | null;
  base: number | null;
  contribs: Contribution[];
};

export type Shap = { key: string; baseValue: number | null; dependence: Record<string, { x: number | null; shap: number }[]>; examples: ShapExample[] };

export type TimelineBlock = { block: number; firstMatchSeq: number | null; nMatches: number | null; trainRows: number | null; mae: number | null; xiModel: number | null; xiBase: number | null };

export type Protocol = {
  cvSeasons: number[];
  testSeason: number | null;
  wfSeason: number | null;
  wfBlock: number | null;
  quantiles: number[];
  heads: string[];
  halflife: number | null;
  earlyStopping: number | null;
  maxTrees: number | null;
  innerValidation: string | null;
};

export type TargetStats = {
  mean: number | null;
  sd: number | null;
  min: number | null;
  max: number | null;
  p10: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p90: number | null;
  hist: Bin[];
  byRole: { role: string; mean: number | null; sd: number | null; n: number | null }[];
};

export type Telemetry = {
  version: string;
  createdAt: string | null;
  notes: string | null;
  duration: Record<string, number>;
  protocol: Protocol;
  data: { rows: number | null; matches: number | null; players: number | null; rowsBySeason: { year: number; n: number }[]; target: TargetStats | null };
  features: FeatureInfo[];
  correlations: { features: string[]; matrix: number[][] } | null;
  tuning: TuningRow[];
  chosenParams: Record<string, unknown>;
  /** "final" | "cv:2024" → head → curve */
  curves: Record<string, Record<string, Curve>>;
  trees: Record<string, number>;
  nLearned: number | null;
  nLearnedByHead: Record<string, number>;
  evaluations: Evaluation[];
  perMatch: Partial<Record<Phase, { key: string; rows: PerMatch[] }>>;
  calibration: Partial<Record<Phase, Calibration>>;
  residuals: Partial<Record<Phase, Residuals>>;
  shap: Shap | null;
  wfTimeline: TimelineBlock[];
  baselines: Record<string, string>;
  environment: Record<string, string | number>;
};

// ------------------------------------------------------------------ per-match API
export type TeamRef = { id: string | null; name: string; code: string };

export type MatchInfo = {
  matchId: number;
  date: string | null;
  season: number | null;
  matchNumber: number | null;
  stage: string | null;
  team1: TeamRef | null;
  team2: TeamRef | null;
  venue: string | null;
  city: string | null;
};

export type MatchRow = {
  info: MatchInfo;
  phase: Phase;
  nPlayers: number;
  maeModel: number | null;
  maeBase: number | null;
  xiModel: number | null;
  xiBase: number | null;
  xiBest: number | null;
  capHitModel: boolean | null;
  capHitBase: boolean | null;
  covered: number | null;
};

export type XiPick = { playerId: string; name: string; imageUrl: string | null; team: string; role: Role; multiplier: number; value: number; actual: number | null; points: number | null };

export type XiResult = { picks: XiPick[]; captain: string | null; viceCaptain: string | null; actualPoints: number | null; selectedOn: number };

export type MatchPlayer = {
  playerId: string;
  name: string;
  imageUrl: string | null;
  team: string;
  teamName: string;
  role: Role;
  predMean: number | null;
  q10: number | null;
  q50: number | null;
  q90: number | null;
  baseline: number | null;
  actual: number | null;
  inModelXi: boolean;
  inBaseXi: boolean;
  inBestXi: boolean;
  modelMult: number | null;
  baseMult: number | null;
  bestMult: number | null;
};

export type XiKey = "model" | "baseline" | "hindsight";

export type MatchDetail = {
  version: string;
  info: MatchInfo;
  phase: Phase;
  players: MatchPlayer[];
  xi: Record<XiKey, XiResult | null>;
  maeModel: number | null;
  maeBase: number | null;
  coverage: number | null;
};

export type Explanation = {
  version: string;
  matchId: number;
  playerId: string;
  name: string;
  team: string | null;
  role: string | null;
  phase: string;
  baseValue: number;
  prediction: number;
  predOutOfSample: number | null;
  actual: number | null;
  note: string;
  contributions: Contribution[];
};

export type MetricDelta = { phase: Phase; metric: string; a: number | null; b: number | null; delta: number | null; higherIsBetter: boolean };

export type Comparison = {
  a: RunSummary;
  b: RunSummary;
  metrics: MetricDelta[];
  params: { name: string; a: unknown; b: unknown; changed: boolean }[];
  importance: { feature: string; group: string | null; aShare: number | null; bShare: number | null; delta: number | null; aRank: number | null; bRank: number | null }[];
  onlyA: string[];
  onlyB: string[];
};
