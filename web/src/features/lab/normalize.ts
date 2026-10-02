/**
 * Permissive readers: unknown JSON → typed Lab data. Every field is optional on the wire (the
 * training code and the Lab evolve independently), so a missing key becomes null / [] / {} and
 * a view decides what to show. Never throws on shape; only on non-object input to `telemetry`.
 */
import { ROLES, type Role } from "@/lib/tokens";

import type {
  Bin,
  Calibration,
  Comparison,
  Contribution,
  Curve,
  ErrStat,
  EvalSummary,
  Evaluation,
  Explanation,
  FeatureInfo,
  MatchDetail,
  MatchInfo,
  MatchPlayer,
  MatchRow,
  MetricDelta,
  Pair,
  PerMatch,
  Phase,
  PhaseHeadline,
  PhaseKind,
  Residuals,
  RunSummary,
  Shap,
  ShapExample,
  TargetStats,
  Telemetry,
  TeamRef,
  XiKey,
  XiPick,
  XiResult,
} from "./types";

type O = Record<string, unknown>;

export const obj = (v: unknown): O => (v && typeof v === "object" && !Array.isArray(v) ? (v as O) : {});
export const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
export function num(v: unknown): number | null {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) return Number(v);
  return null;
}
export const str = (v: unknown): string | null => (typeof v === "string" && v !== "" ? v : typeof v === "number" ? String(v) : null);
const bool = (v: unknown): boolean | null => (typeof v === "boolean" ? v : v === 1 ? true : v === 0 ? false : null);
const role = (v: unknown): Role => (ROLES as readonly string[]).includes(String(v)) ? (v as Role) : "BAT";
const numMap = (v: unknown): Record<string, number> =>
  Object.fromEntries(Object.entries(obj(v)).flatMap(([k, x]) => (num(x) === null ? [] : [[k, num(x)!]])));

export function pair(v: unknown): Pair {
  const o = obj(v);
  const ci = arr(o.ci95 ?? o.ci);
  return { model: num(o.model), baseline: num(o.baseline), diff: num(o.diff), ci: [num(ci[0]), num(ci[1])] };
}

export function evalSummary(v: unknown): EvalSummary {
  const o = obj(v);
  return {
    matches: num(o.matches),
    bestXi: pair(o.best_xi_points),
    hindsight: num(o.hindsight_best_xi_points),
    captain: pair(o.captain_top2_rate),
    mae: pair(o.mae),
    spearman: pair(o.spearman),
    coverage: num(o.p10_p90_coverage),
  };
}

/** "test:2025" → { kind: "test", season: 2025, label: "Test 2025" }. */
export function phaseOf(key: string): { kind: PhaseKind; season: number | null; label: string } {
  const [k, y] = key.split(":");
  const season = num(y);
  const kind: PhaseKind = k === "cv" || k === "test" || k === "walkforward" ? k : "other";
  const name = kind === "cv" ? "CV" : kind === "test" ? "Test" : kind === "walkforward" ? "Walk-forward" : k;
  return { kind, season, label: season ? `${name} ${season}` : name };
}

/** First key of a phase in a telemetry block keyed like "test:2025". */
export function keyFor(block: unknown, phase: string): string | null {
  return Object.keys(obj(block)).find((k) => k === phase || k.startsWith(`${phase}:`)) ?? null;
}

function headline(v: unknown): PhaseHeadline | null {
  if (!v || typeof v !== "object") return null;
  return { key: str(obj(v).key) ?? "", ...evalSummary(v) };
}

export function runSummary(v: unknown): RunSummary {
  const o = obj(v);
  return {
    version: str(o.version) ?? "unknown",
    createdAt: str(o.created_at),
    isLatest: o.is_latest === true,
    hasTelemetry: o.has_telemetry === true,
    hasEvalFrame: o.has_eval_frame === true,
    hasBooster: o.has_booster === true,
    inDb: o.in_db === true,
    nFeatures: num(o.n_features),
    nLearned: num(o.n_learned_values),
    trees: numMap(o.trees),
    durationS: num(o.duration_s),
    params: obj(o.chosen_params),
    test: headline(o.test),
    walkforward: headline(o.walkforward),
  };
}

export const runs = (v: unknown): RunSummary[] => arr(v).map(runSummary);

const bins = (v: unknown): Bin[] =>
  arr(v).flatMap((b) => {
    const o = obj(b);
    const lo = num(o.lo);
    const hi = num(o.hi);
    const n = num(o.n);
    return lo === null || hi === null || n === null ? [] : [{ lo, hi, n }];
  });

function feature(v: unknown): FeatureInfo | null {
  const o = obj(v);
  const name = str(o.name);
  if (!name) return null;
  return {
    name,
    group: str(o.group) ?? "Other",
    description: str(o.description) ?? "",
    missingRate: num(o.missing_rate),
    mean: num(o.mean),
    std: num(o.std),
    min: num(o.min),
    max: num(o.max),
    gain: num(o.importance_gain),
    split: num(o.importance_split),
    shap: num(o.shap_mean_abs),
  };
}

function curve(v: unknown): Curve | null {
  const o = obj(v);
  const train = arr(o.train).map(num).filter((x): x is number => x !== null);
  const valid = arr(o.valid).map(num).filter((x): x is number => x !== null);
  if (!train.length && !valid.length) return null;
  return { train, valid, metric: str(o.metric) ?? "loss", bestIter: num(o.best_iter), iters: num(o.iters) };
}

function perMatch(v: unknown): PerMatch | null {
  const o = obj(v);
  const matchId = num(o.match_id);
  if (matchId === null) return null;
  return {
    matchId,
    date: str(o.date),
    team1: str(o.team1),
    team2: str(o.team2),
    xiModel: num(o.xi_model),
    xiBase: num(o.xi_base),
    xiBest: num(o.xi_best),
    capHitModel: bool(o.cap_hit_model),
    capHitBase: bool(o.cap_hit_base),
    maeModel: num(o.mae_model),
    maeBase: num(o.mae_base),
    rhoModel: num(o.rho_model),
    rhoBase: num(o.rho_base),
    covered: num(o.covered),
  };
}

function calibration(key: string, v: unknown): Calibration {
  const o = obj(v);
  const c = obj(o.coverage);
  const p = obj(o.pinball);
  return {
    key,
    coverage: { belowQ10: num(c.below_q10), belowQ50: num(c.below_q50), belowQ90: num(c.below_q90), inside80: num(c.inside_80) },
    reliability: arr(o.reliability).flatMap((b) => {
      const r = obj(b);
      const predMean = num(r.pred_mean);
      const actualMean = num(r.actual_mean);
      return predMean === null || actualMean === null ? [] : [{ predLo: num(r.pred_lo), predHi: num(r.pred_hi), predMean, actualMean, n: num(r.n) ?? 0 }];
    }),
    pinball: { q10: num(p.q10), q50: num(p.q50), q90: num(p.q90) },
  };
}

const errStat = (label: string, v: unknown): ErrStat => {
  const o = obj(v);
  return { label, mae: num(o.mae), bias: num(o.bias), n: num(o.n) };
};

const ROLE_ORDER = ["WK", "BAT", "AR", "BOWL"];

function residuals(key: string, v: unknown): Residuals {
  const o = obj(v);
  const byRole = Object.entries(obj(o.by_role))
    .map(([k, x]) => errStat(k, x))
    .sort((a, b) => ROLE_ORDER.indexOf(a.label) - ROLE_ORDER.indexOf(b.label));
  return {
    key,
    hist: bins(o.hist),
    byRole,
    byExperience: arr(o.by_experience).map((x) => errStat(str(obj(x).bucket) ?? "?", x)),
    byBatsFirst: Object.entries(obj(o.by_bats_first)).map(([k, x]) => errStat(k, x)),
  };
}

export function contribution(v: unknown): Contribution | null {
  const o = obj(v);
  const feature = str(o.feature);
  const shap = num(o.shap);
  if (!feature || shap === null) return null;
  return { feature, value: num(o.value), shap, group: str(o.group), description: str(o.description) };
}

function shapExample(v: unknown): ShapExample | null {
  const o = obj(v);
  const matchId = num(o.match_id);
  const playerId = str(o.player_id);
  if (matchId === null || !playerId) return null;
  return {
    kind: str(o.kind),
    matchId,
    playerId,
    playerName: str(o.player_name) ?? playerId,
    team: str(o.team),
    pred: num(o.pred),
    actual: num(o.actual),
    base: num(o.base),
    contribs: arr(o.contribs).map(contribution).filter((c): c is Contribution => c !== null),
  };
}

function shap(v: unknown): Shap | null {
  const block = obj(v);
  const key = keyFor(block, "test") ?? Object.keys(block)[0];
  if (!key) return null;
  const o = obj(block[key]);
  const dependence = Object.fromEntries(
    Object.entries(obj(o.dependence)).map(([f, pts]) => [
      f,
      arr(pts).flatMap((p) => {
        const s = num(obj(p).shap);
        return s === null ? [] : [{ x: num(obj(p).x), shap: s }];
      }),
    ]),
  );
  return { key, baseValue: num(o.base_value), dependence, examples: arr(o.examples).map(shapExample).filter((e): e is ShapExample => e !== null) };
}

function byPhase<T>(block: unknown, read: (key: string, v: unknown) => T): Partial<Record<Phase, T>> {
  const out: Partial<Record<Phase, T>> = {};
  for (const ph of ["test", "walkforward"] as const) {
    const k = keyFor(block, ph);
    if (k) out[ph] = read(k, obj(block)[k]);
  }
  return out;
}

function targetStats(v: unknown): TargetStats | null {
  const o = obj(v);
  if (!Object.keys(o).length) return null;
  return {
    mean: num(o.mean),
    sd: num(o.sd),
    min: num(o.min),
    max: num(o.max),
    p10: num(o.p10),
    p25: num(o.p25),
    p50: num(o.p50),
    p75: num(o.p75),
    p90: num(o.p90),
    hist: bins(o.hist),
    byRole: Object.entries(obj(o.by_role))
      .map(([r, x]) => ({ role: r, mean: num(obj(x).mean), sd: num(obj(x).sd), n: num(obj(x).n) }))
      .sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role)),
  };
}

const KIND_ORDER: Record<PhaseKind, number> = { cv: 0, test: 1, walkforward: 2, other: 3 };

export function telemetry(v: unknown): Telemetry {
  const o = obj(v);
  const p = obj(o.protocol);
  const d = obj(o.data);
  const corr = obj(o.correlations);
  const corrFeatures = arr(corr.features).map(str).filter((s): s is string => s !== null);
  const matrix = arr(corr.matrix).map((row) => arr(row).map((x) => num(x) ?? 0));
  const evaluations: Evaluation[] = Object.entries(obj(o.evaluations))
    .map(([key, s]) => ({ key, ...phaseOf(key), summary: evalSummary(s) }))
    .sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind] || (a.season ?? 0) - (b.season ?? 0));
  const curves: Telemetry["curves"] = {};
  for (const [set, heads] of Object.entries(obj(o.curves))) {
    const hs: Record<string, Curve> = {};
    for (const [h, c] of Object.entries(obj(heads))) {
      const cv = curve(c);
      if (cv) hs[h] = cv;
    }
    if (Object.keys(hs).length) curves[set] = hs;
  }
  return {
    version: str(o.version) ?? "unknown",
    createdAt: str(o.created_at),
    notes: str(o.notes),
    duration: numMap(o.duration_s),
    protocol: {
      cvSeasons: arr(p.cv_seasons).map(num).filter((x): x is number => x !== null),
      testSeason: num(p.test_season),
      wfSeason: num(p.wf_season),
      wfBlock: num(p.wf_block),
      quantiles: arr(p.quantiles).map(num).filter((x): x is number => x !== null),
      heads: arr(p.heads).map(str).filter((x): x is string => x !== null),
      halflife: num(p.recency_halflife_seasons),
      earlyStopping: num(p.early_stopping_rounds),
      maxTrees: num(p.max_trees),
      innerValidation: str(p.inner_validation),
    },
    data: {
      rows: num(d.rows),
      matches: num(d.matches),
      players: num(d.players),
      rowsBySeason: Object.entries(obj(d.rows_by_season))
        .flatMap(([y, n]) => (num(y) !== null && num(n) !== null ? [{ year: num(y)!, n: num(n)! }] : []))
        .sort((a, b) => a.year - b.year),
      target: targetStats(d.target),
    },
    features: arr(o.features).map(feature).filter((f): f is FeatureInfo => f !== null),
    correlations: corrFeatures.length && matrix.length === corrFeatures.length ? { features: corrFeatures, matrix } : null,
    tuning: arr(o.tuning).map((t) => {
      const r = obj(t);
      return { params: obj(r.params), foldMae: numMap(r.fold_mae), meanMae: num(r.mean_mae), seconds: num(r.seconds) };
    }),
    chosenParams: obj(o.chosen_params),
    curves,
    trees: numMap(o.trees),
    nLearned: num(o.n_learned_values),
    nLearnedByHead: numMap(o.n_learned_by_head),
    evaluations,
    perMatch: byPhase(o.per_match, (key, rows) => ({ key, rows: arr(rows).map(perMatch).filter((r): r is PerMatch => r !== null) })),
    calibration: byPhase(o.calibration, calibration),
    residuals: byPhase(o.residuals, residuals),
    shap: shap(o.shap),
    wfTimeline: arr(o.walkforward_timeline).map((b, i) => {
      const r = obj(b);
      return {
        block: num(r.block) ?? i + 1,
        firstMatchSeq: num(r.first_match_seq),
        nMatches: num(r.n_matches),
        trainRows: num(r.train_rows),
        mae: num(r.mae),
        xiModel: num(r.xi_model),
        xiBase: num(r.xi_base),
      };
    }),
    baselines: Object.fromEntries(Object.entries(obj(o.baselines)).flatMap(([k, x]) => (str(x) ? [[k, str(x)!]] : []))),
    environment: Object.fromEntries(Object.entries(obj(o.environment)).flatMap(([k, x]): [string, string | number][] => (num(x) !== null ? [[k, num(x)!]] : str(x) ? [[k, str(x)!]] : []))),
  };
}

// ------------------------------------------------------------------ per-match API
function teamRef(v: unknown): TeamRef | null {
  const o = obj(v);
  const name = str(o.name);
  if (!name) return null;
  return { id: str(o.id), name, code: str(o.code) ?? name.slice(0, 4).toUpperCase() };
}

export function matchInfo(v: unknown): MatchInfo {
  const o = obj(v);
  return {
    matchId: num(o.match_id) ?? 0,
    date: str(o.date),
    season: num(o.season),
    matchNumber: num(o.match_number),
    stage: str(o.stage),
    team1: teamRef(o.team1),
    team2: teamRef(o.team2),
    venue: str(o.venue),
    city: str(o.city),
  };
}

const phase = (v: unknown): Phase => (v === "walkforward" ? "walkforward" : "test");

export const matchRows = (v: unknown): MatchRow[] =>
  arr(v).map((m) => {
    const o = obj(m);
    return {
      info: matchInfo(o.info),
      phase: phase(o.phase),
      nPlayers: num(o.n_players) ?? 0,
      maeModel: num(o.mae_model),
      maeBase: num(o.mae_base),
      xiModel: num(o.xi_model),
      xiBase: num(o.xi_base),
      xiBest: num(o.xi_best),
      capHitModel: bool(o.cap_hit_model),
      capHitBase: bool(o.cap_hit_base),
      covered: num(o.covered),
    };
  });

function xiPick(v: unknown): XiPick {
  const o = obj(v);
  return {
    playerId: str(o.player_id) ?? "",
    name: str(o.name) ?? str(o.player_id) ?? "?",
    imageUrl: str(o.image_url),
    team: str(o.team) ?? "",
    role: role(o.role),
    multiplier: num(o.multiplier) ?? 1,
    value: num(o.value) ?? 0,
    actual: num(o.actual),
    points: num(o.points),
  };
}

function xiResult(v: unknown): XiResult | null {
  if (!v || typeof v !== "object") return null;
  const o = obj(v);
  return { picks: arr(o.picks).map(xiPick), captain: str(o.captain), viceCaptain: str(o.vice_captain), actualPoints: num(o.actual_points), selectedOn: num(o.selected_on) ?? 0 };
}

function matchPlayer(v: unknown): MatchPlayer {
  const o = obj(v);
  return {
    playerId: str(o.player_id) ?? "",
    name: str(o.name) ?? str(o.player_id) ?? "?",
    imageUrl: str(o.image_url),
    team: str(o.team) ?? "",
    teamName: str(o.team_name) ?? str(o.team) ?? "",
    role: role(o.role),
    predMean: num(o.pred_mean),
    q10: num(o.q10),
    q50: num(o.q50),
    q90: num(o.q90),
    baseline: num(o.baseline),
    actual: num(o.actual),
    inModelXi: o.in_model_xi === true,
    inBaseXi: o.in_base_xi === true,
    inBestXi: o.in_best_xi === true,
    modelMult: num(o.model_mult),
    baseMult: num(o.base_mult),
    bestMult: num(o.best_mult),
  };
}

export function matchDetail(v: unknown): MatchDetail {
  const o = obj(v);
  const xi = obj(o.xi);
  const keys: XiKey[] = ["model", "baseline", "hindsight"];
  return {
    version: str(o.version) ?? "",
    info: matchInfo(o.info),
    phase: phase(o.phase),
    players: arr(o.players).map(matchPlayer),
    xi: Object.fromEntries(keys.map((k) => [k, xiResult(xi[k])])) as Record<XiKey, XiResult | null>,
    maeModel: num(o.mae_model),
    maeBase: num(o.mae_base),
    coverage: num(o.coverage),
  };
}

export function explanation(v: unknown): Explanation {
  const o = obj(v);
  return {
    version: str(o.version) ?? "",
    matchId: num(o.match_id) ?? 0,
    playerId: str(o.player_id) ?? "",
    name: str(o.name) ?? str(o.player_id) ?? "?",
    team: str(o.team),
    role: str(o.role),
    phase: str(o.phase) ?? "",
    baseValue: num(o.base_value) ?? 0,
    prediction: num(o.prediction) ?? 0,
    predOutOfSample: num(o.pred_out_of_sample),
    actual: num(o.actual),
    note: str(o.note) ?? "",
    contributions: arr(o.contributions).map(contribution).filter((c): c is Contribution => c !== null),
  };
}

export function comparison(v: unknown): Comparison {
  const o = obj(v);
  return {
    a: runSummary(o.a),
    b: runSummary(o.b),
    metrics: arr(o.metrics).map((m): MetricDelta => {
      const r = obj(m);
      return { phase: phase(r.phase), metric: str(r.metric) ?? "", a: num(r.a), b: num(r.b), delta: num(r.delta), higherIsBetter: r.higher_is_better !== false };
    }),
    params: arr(o.params).map((p) => {
      const r = obj(p);
      return { name: str(r.name) ?? "", a: r.a ?? null, b: r.b ?? null, changed: r.changed === true };
    }),
    importance: arr(o.importance).map((i) => {
      const r = obj(i);
      return { feature: str(r.feature) ?? "", group: str(r.group), aShare: num(r.a_gain_share), bShare: num(r.b_gain_share), delta: num(r.delta), aRank: num(r.a_rank), bRank: num(r.b_rank) };
    }),
    onlyA: arr(o.features_only_a).map(str).filter((s): s is string => s !== null),
    onlyB: arr(o.features_only_b).map(str).filter((s): s is string => s !== null),
  };
}
