/**
 * SAMPLE FIXTURE: invented numbers in the telemetry.json wire shape, for unit tests only.
 * Never rendered by the app as real data (the Lab only shows runs the API returns).
 */
export const SAMPLE_TELEMETRY_WIRE = {
  version: "fixture-run",
  notes: "SYNTHETIC SAMPLE fixture for tests",
  created_at: "2026-10-02T12:00:00+00:00",
  duration_s: { build: 40, tune: 800, test: 60, walkforward: 500, total: 1400 },
  protocol: { cv_seasons: [2023, 2024], test_season: 2025, wf_season: 2026, wf_block: 10, quantiles: [0.1, 0.5, 0.9], heads: ["mean", "q10", "q50", "q90"], recency_halflife_seasons: 3 },
  data: {
    rows: 1000,
    matches: 45,
    players: 120,
    rows_by_season: { "2024": 400, "2023": 300, "2025": 200, "2026": 100 },
    target: { mean: 40, sd: 35, min: -4, max: 200, p10: 4, p25: 12, p50: 31, p75: 59, p90: 89, hist: [{ lo: 0, hi: 10, n: 50 }, { lo: 10, hi: 20, n: 30 }, { lo: 20, hi: "bad", n: 1 }], by_role: { BOWL: { mean: 35, sd: 30, n: 300 }, WK: { mean: 42, sd: 38, n: 100 } } },
  },
  features: [
    { name: "ewm_5", group: "Fantasy form", description: "EWM of past points", missing_rate: 0.05, mean: 30, std: 12, min: 0, max: 120, importance_gain: 600, importance_split: 40, shap_mean_abs: 6.1 },
    { name: "mean_5", group: "Fantasy form", description: "Last-5 mean", missing_rate: 0.05, mean: 31, std: 14, min: 0, max: 130, importance_gain: 300, importance_split: 30, shap_mean_abs: 3.2 },
    { name: "bats_first", group: "Conditions", description: "Bats first", missing_rate: 0, mean: 0.5, std: 0.5, min: 0, max: 1, importance_gain: 100, importance_split: 10, shap_mean_abs: 0.5 },
    { group: "no name: dropped" },
  ],
  correlations: { features: ["ewm_5", "mean_5"], matrix: [[1, 0.92], [0.92, 1]] },
  tuning: [
    { params: { num_leaves: 15 }, fold_mae: { "2023": 20.1, "2024": 21.0 }, mean_mae: 20.55, seconds: 50 },
    { params: { num_leaves: 31 }, fold_mae: { "2023": 20.4, "2024": 21.2 }, mean_mae: 20.8, seconds: 70 },
  ],
  chosen_params: { num_leaves: 15, learning_rate: 0.03 },
  curves: { final: { mean: { train: [10, 8, 7, 6], valid: [11, 9.5, 9.4, 9.6], metric: "l2", best_iter: 300, iters: 400 } } },
  trees: { mean: 300, q10: 200 },
  n_learned_values: 9000,
  evaluations: {
    "walkforward:2026": { matches: 10, best_xi_points: { model: 780, baseline: 760, diff: 20, ci95: [-5, 45] }, hindsight_best_xi_points: 1200, captain_top2_rate: { model: 0.3, baseline: 0.2, diff: 0.1, ci95: [0.02, 0.18] }, mae: { model: 33, baseline: 36, diff: -3, ci95: [-4, -2] }, spearman: { model: 0.2, baseline: 0.18, diff: 0.02, ci95: [-0.01, 0.05] }, p10_p90_coverage: 0.74 },
    "cv:2024": { matches: 70, best_xi_points: { model: 700, baseline: 690, diff: 10, ci95: [1, 19] } },
    "test:2025": { matches: 20, best_xi_points: { model: 770, baseline: 740, diff: 30, ci95: [2, 55] }, hindsight_best_xi_points: 1160, mae: { model: 33.5, baseline: 35.8, diff: -2.3, ci95: [-3.1, -1.5] }, p10_p90_coverage: 0.81 },
  },
  per_match: { "test:2025": [{ match_id: 1, date: "2025-03-22", team1: "KKR", team2: "RCB", xi_model: 800, xi_base: 780, xi_best: 1100, cap_hit_model: true }, { nope: 1 }] },
  calibration: {
    "test:2025": {
      coverage: { below_q10: 0.12, below_q50: 0.52, below_q90: 0.88, inside_80: 0.76 },
      reliability: [{ pred_lo: 0, pred_hi: 20, pred_mean: 12, actual_mean: 14, n: 100 }, { pred_lo: 20, pred_hi: 60, pred_mean: 40, actual_mean: 31, n: 50 }],
      pinball: { q10: 3.1, q50: 13.2, q90: 8.4 },
    },
  },
  residuals: { "test:2025": { hist: [{ lo: -20, hi: 0, n: 60 }, { lo: 0, hi: 40, n: 30 }, { lo: 40, hi: 80, n: 10 }], by_role: { BOWL: { mae: 30, bias: 2, n: 40 }, WK: { mae: 35, bias: -6, n: 10 } }, by_experience: [{ bucket: "debut", mae: 25, bias: 4, n: 5 }], by_bats_first: { "bats first": { mae: 32, bias: 1, n: 50 } } } },
  shap: { "test:2025": { base_value: 38, dependence: { ewm_5: [{ x: 10, shap: -5 }, { x: null, shap: 0 }, { x: 50, shap: 6 }] }, examples: [{ kind: "over", match_id: 1, player_id: "p1", player_name: "A Player", pred: 60, actual: 4, base: 38, contribs: [{ feature: "ewm_5", value: 70, shap: 15 }, { feature: "bats_first", value: 1, shap: 2 }] }] } },
  walkforward_timeline: [{ block: 1, first_match_seq: 1, n_matches: 10, train_rows: 900, mae: 34, xi_model: 790, xi_base: 770 }],
  baselines: { last5: "Mean of the last 5 games" },
  environment: { lightgbm: "4.7.0", cpu_count: 8, weird: { nested: true } },
};
