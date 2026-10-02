/**
 * "What our result says": short sentences computed from the run's numbers (never hard-coded),
 * shown in each card's Learn-more panel. Pure functions, unit-tested.
 */
import { fmtNum, fmtPct, fmtSigned, METRICS, verdict, type MetricKey } from "./format";
import type { Bin, Calibration, Curve, ErrStat, FeatureInfo, Pair, TargetStats, TuningRow } from "./types";

export function pairInsight(p: Pair, key: MetricKey, setLabel: string): string {
  const m = METRICS[key];
  if (p.model === null || p.baseline === null) return `No ${m.short} recorded for ${setLabel}.`;
  const v = verdict(p, m.higherIsBetter);
  const [lo, hi] = p.ci;
  const ci = lo !== null && hi !== null ? ` (95% CI ${m.diffFmt(lo)} … ${m.diffFmt(hi)})` : "";
  const head = `${setLabel}: model ${m.fmt(p.model)} vs baseline ${m.fmt(p.baseline)}, a difference of ${m.diffFmt(p.diff)}${ci}.`;
  if (v === "better") return `${head} The interval excludes zero, so the model is reliably better on this metric.`;
  if (v === "worse") return `${head} The interval excludes zero on the wrong side: the baseline is reliably better here.`;
  if (v === "tie") return `${head} The interval includes zero, so this gap could be luck; we can't call a winner.`;
  return head;
}

export function coverageInsight(c: number | null, target = 0.8): string {
  if (c === null) return "Coverage was not recorded for this run.";
  const gap = c - target;
  const s = `The p10–p90 range contained the actual score ${fmtPct(c, 1)} of the time (target ${fmtPct(target)}).`;
  if (Math.abs(gap) <= 0.03) return `${s} That is well calibrated.`;
  return gap < 0
    ? `${s} The ranges are too narrow, i.e. over-confident by ${fmtNum(-gap * 100, 1)} pp.`
    : `${s} The ranges are wider than needed (under-confident by ${fmtNum(gap * 100, 1)} pp), so they could be tightened.`;
}

export function quantileInsight(cal: Calibration): string {
  const { belowQ10, belowQ50, belowQ90 } = cal.coverage;
  const parts: string[] = [];
  const add = (name: string, obs: number | null, exp: number) => {
    if (obs === null) return;
    const d = obs - exp;
    parts.push(`${fmtPct(obs, 1)} of actuals fell below ${name} (expected ${fmtPct(exp)}${Math.abs(d) > 0.03 ? `, off by ${fmtSigned(d * 100, 1, " pp")}` : ", on target"})`);
  };
  add("p10", belowQ10, 0.1);
  add("p50", belowQ50, 0.5);
  add("p90", belowQ90, 0.9);
  if (!parts.length) return "No quantile coverage recorded.";
  return `${parts.join("; ")}.`;
}

export function reliabilityInsight(cal: Calibration): string {
  const bins = cal.reliability;
  if (!bins.length) return "No reliability bins recorded.";
  const n = bins.reduce((s, b) => s + b.n, 0) || 1;
  const bias = bins.reduce((s, b) => s + (b.actualMean - b.predMean) * b.n, 0) / n;
  const worst = bins.reduce((w, b) => (Math.abs(b.actualMean - b.predMean) > Math.abs(w.actualMean - w.predMean) ? b : w));
  const gap = worst.actualMean - worst.predMean;
  return (
    `Across ${bins.length} bins the weighted average gap (actual − predicted) is ${fmtSigned(bias, 1)} pts. ` +
    `The largest gap is in the bin predicted ≈${fmtNum(worst.predMean, 0)} pts, where players actually averaged ${fmtNum(worst.actualMean, 1)} (${fmtSigned(gap, 1)}): ` +
    (gap > 0 ? "the model under-predicts there." : "the model over-predicts there.")
  );
}

export function curveInsight(c: Curve, head: string): string {
  if (!c.valid.length) return "No validation curve recorded.";
  const n = c.valid.length;
  let bestI = 0;
  c.valid.forEach((v, i) => {
    if (v < c.valid[bestI]) bestI = i;
  });
  const best = c.valid[bestI];
  const last = c.valid[n - 1];
  const first = c.valid[0];
  const trainAtBest = c.train[Math.min(bestI, c.train.length - 1)];
  const iter = c.bestIter ?? Math.round(((bestI + 1) / n) * (c.iters ?? n));
  const gap = trainAtBest !== undefined ? best - trainAtBest : null;
  const parts = [
    `The ${head} head's validation ${c.metric} fell from ${fmtNum(first, 2)} to ${fmtNum(best, 2)} (${fmtPct(first ? (first - best) / first : null, 0)} lower) and was best at round ${iter}.`,
  ];
  if (last > best * 1.001) parts.push(`After that it crept back up to ${fmtNum(last, 2)}: more trees were starting to overfit, which is why early stopping cut there.`);
  else parts.push("It was still flat at the end, so more trees would not have helped much.");
  if (gap !== null) parts.push(`At the best round the train/validation gap was ${fmtNum(gap, 2)}${gap > best * 0.15 ? ", a sizeable generalisation gap" : ", a small gap"}.`);
  return parts.join(" ");
}

export function tuningInsight(rows: TuningRow[], chosen: Record<string, unknown>): string {
  const scored = rows.filter((r) => r.meanMae !== null);
  if (!scored.length) return "No tuning results recorded.";
  const sorted = [...scored].sort((a, b) => a.meanMae! - b.meanMae!);
  const best = sorted[0];
  const worst = sorted[sorted.length - 1];
  const spread = worst.meanMae! - best.meanMae!;
  const keys = Object.keys(best.params);
  const desc = keys.map((k) => `${k} = ${String(best.params[k])}`).join(", ");
  const match = keys.every((k) => chosen[k] === undefined || chosen[k] === best.params[k]);
  return (
    `${scored.length} settings were tried. The best mean fold MAE was ${fmtNum(best.meanMae, 3)} (${desc}); the worst ${fmtNum(worst.meanMae, 3)}, a spread of only ${fmtNum(spread, 3)} pts. ` +
    (spread < 0.2 ? "The model is not very sensitive to these knobs in this range. " : "These knobs matter: pick carefully. ") +
    (match ? "That best setting is the one used." : "")
  ).trim();
}

export function importanceInsight(features: FeatureInfo[], by: "gain" | "split" | "shap"): string {
  const vals = features.map((f) => ({ name: f.name, v: f[by] ?? 0 })).sort((a, b) => b.v - a.v);
  const tot = vals.reduce((s, x) => s + x.v, 0);
  if (!tot) return "No importance recorded.";
  const top3 = vals.slice(0, 3);
  const share = top3.reduce((s, x) => s + x.v, 0) / tot;
  const zero = vals.filter((x) => x.v === 0).length;
  return (
    `The top three features (${top3.map((x) => x.name).join(", ")}) account for ${fmtPct(share)} of total ${by === "shap" ? "mean |SHAP|" : by}. ` +
    (zero ? `${zero} feature${zero === 1 ? " is" : "s are"} never used at all.` : "Every feature is used at least once.")
  );
}

export function correlationInsight(features: string[], matrix: number[][]): string {
  let best: [string, string, number] | null = null;
  for (let i = 0; i < features.length; i++)
    for (let j = i + 1; j < features.length; j++) {
      const r = matrix[i]?.[j] ?? 0;
      if (!best || Math.abs(r) > Math.abs(best[2])) best = [features[i], features[j], r];
    }
  if (!best) return "No correlations recorded.";
  let strong = 0;
  for (let i = 0; i < features.length; i++) for (let j = i + 1; j < features.length; j++) if (Math.abs(matrix[i]?.[j] ?? 0) >= 0.8) strong++;
  return `The most correlated pair is ${best[0]} and ${best[1]} (r = ${fmtNum(best[2], 2)}). ${strong} pair${strong === 1 ? "" : "s"} have |r| ≥ 0.8; such features share importance between them.`;
}

export function targetInsight(t: TargetStats): string {
  if (t.mean === null || t.p50 === null) return "No target statistics recorded.";
  const skew = t.mean - t.p50;
  return (
    `The average player-match scores ${fmtNum(t.mean, 1)} pts but the median is only ${fmtNum(t.p50, 1)}: ` +
    (skew > 2 ? "a right-skewed target with many modest scores and a long tail of big hauls. " : "a fairly symmetric target. ") +
    (t.p10 !== null && t.p90 !== null ? `80% of scores lie between ${fmtNum(t.p10, 0)} and ${fmtNum(t.p90, 0)}.` : "")
  );
}

export function histPeak(hist: Bin[]): Bin | null {
  return hist.length ? hist.reduce((m, b) => (b.n > m.n ? b : m)) : null;
}

export function groupErrorInsight(stats: ErrStat[], what: string): string {
  const s = stats.filter((x) => x.mae !== null);
  if (!s.length) return `No residuals by ${what} recorded.`;
  const worst = s.reduce((w, x) => (x.mae! > w.mae! ? x : w));
  const best = s.reduce((w, x) => (x.mae! < w.mae! ? x : w));
  const biased = s.reduce((w, x) => (Math.abs(x.bias ?? 0) > Math.abs(w.bias ?? 0) ? x : w));
  return (
    `Errors are largest for ${worst.label} (MAE ${fmtNum(worst.mae, 1)}) and smallest for ${best.label} (${fmtNum(best.mae, 1)}). ` +
    `The strongest bias is for ${biased.label}: ${fmtSigned(biased.bias, 1)} pts on average (${(biased.bias ?? 0) > 0 ? "under-predicted" : "over-predicted"}).`
  );
}

export function residualHistInsight(hist: Bin[]): string {
  const n = hist.reduce((s, b) => s + b.n, 0);
  if (!n) return "No residual histogram recorded.";
  const pos = hist.filter((b) => b.lo >= 0).reduce((s, b) => s + b.n, 0);
  const tail = hist.filter((b) => b.lo >= 40).reduce((s, b) => s + b.n, 0);
  return `${fmtPct(pos / n)} of rows were under-predicted (actual ≥ predicted). ${fmtPct(tail / n, 1)} were under-predicted by 40+ points: the big hauls no pre-match model can see coming.`;
}

/** Signed share of the (model − baseline) distance to hindsight that the model captures. */
export function captureRatio(model: number | null, base: number | null, best: number | null): number | null {
  if (model === null || best === null || base === null || best === base) return null;
  return (model - base) / (best - base);
}
