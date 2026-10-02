"use client";

import { useMemo, useState } from "react";

import { StatTile } from "@/components/data/stat-tile";

import { BarsChart, C, ForestPlot, HistogramChart, LinesChart, ReliabilityChart } from "./charts";
import { METRICS, PHASE_LABEL, fmtDate, fmtNum, fmtPct, type MetricKey } from "./format";
import { coverageInsight, groupErrorInsight, pairInsight, quantileInsight, reliabilityInsight, residualHistInsight } from "./insights";
import type { ErrStat, Phase, Telemetry } from "./types";
import { Grid, LabCard, SectionTitle, Segmented, Term } from "./ui";

const METRIC_KEYS: MetricKey[] = ["bestXi", "captain", "mae", "spearman"];

function PhaseToggle({ value, onChange, phases }: { value: Phase; onChange: (p: Phase) => void; phases: Phase[] }) {
  if (phases.length < 2) return null;
  return <Segmented size="sm" label="Evaluation set" value={value} onChange={onChange} options={phases.map((p) => ({ key: p, label: PHASE_LABEL[p] }))} />;
}

function errRows(stats: ErrStat[]) {
  return stats.map((s) => ({ group: s.label, mae: s.mae, bias: s.bias, n: s.n }));
}

export function EvaluationTab({ t }: { t: Telemetry }) {
  const [metric, setMetric] = useState<MetricKey>("bestXi");
  const m = METRICS[metric];
  const evalRows = t.evaluations.map((e) => ({ key: e.key, label: e.label, pair: e.summary[metric], emphasis: e.kind !== "cv" }));
  const avail = (["test", "walkforward"] as const).filter((p) => t.perMatch[p] || t.calibration[p] || t.residuals[p]);
  const [phase, setPhase] = useState<Phase>(avail[0] ?? "test");
  const ph = avail.includes(phase) ? phase : avail[0] ?? "test";
  const pm = t.perMatch[ph];
  const cal = t.calibration[ph];
  const res = t.residuals[ph];
  const setLabel = (pm?.key ?? cal?.key ?? res?.key ?? ph).replace("walkforward:", "Walk-forward ").replace("test:", "Test ");

  const perMatchData = useMemo(
    () => (pm?.rows ?? []).map((r, i) => ({ n: i + 1, label: `${fmtDate(r.date)} ${r.team1 ?? ""} v ${r.team2 ?? ""}`.trim(), model: r.xiModel, baseline: r.xiBase, hindsight: r.xiBest })),
    [pm],
  );
  const wins = (pm?.rows ?? []).filter((r) => r.xiModel !== null && r.xiBase !== null && r.xiModel > r.xiBase).length;
  const ties = (pm?.rows ?? []).filter((r) => r.xiModel !== null && r.xiModel === r.xiBase).length;

  return (
    <div className="space-y-6">
      <SectionTitle sub="Every evaluated season: the five CV folds used for tuning, the one-shot test season and the walk-forward season.">Model vs baseline, season by season</SectionTitle>
      <div className="flex flex-wrap items-center gap-2">
        <Segmented label="Metric" value={metric} onChange={setMetric} options={METRIC_KEYS.map((k) => ({ key: k, label: METRICS[k].short }))} />
      </div>
      <Grid cols={2}>
        <LabCard
          title={`${m.label}: difference with 95% CI`}
          caption="Each row: model minus baseline on that season's matches. The bar is the 95% bootstrap interval; a bar clear of the centre line is a real difference."
          table={{ columns: ["Set", "Model", "Baseline", "Δ", "CI low", "CI high"], rows: evalRows.map((r) => [r.label, m.fmt(r.pair.model), m.fmt(r.pair.baseline), m.diffFmt(r.pair.diff), m.diffFmt(r.pair.ci[0]), m.diffFmt(r.pair.ci[1])]) }}
          learn={{
            concept: (
              <>
                A <Term id="bootstrap-ci">paired bootstrap</Term> resamples matches to see how much the average difference would wobble if we had seen a different set of matches. It answers “could
                this gap be luck?”.
              </>
            ),
            formula: "Δ = mean over matches of (model − baseline);  CI = [2.5%, 97.5%] of Δ over 2,000 resamples",
            read: `Green = model reliably better, red = baseline reliably better, grey = interval crosses zero (undecided). ${m.higherIsBetter ? "Right of centre is better for the model." : "For MAE, left of centre (lower error) is better for the model."}`,
            good: "Green on most seasons, and especially on the test and walk-forward rows (the ones never used for any decision).",
            ours: t.evaluations
              .filter((e) => e.kind !== "cv")
              .map((e) => pairInsight(e.summary[metric], metric, e.label))
              .join(" "),
          }}
        >
          <ForestPlot rows={evalRows} fmt={m.diffFmt} higherIsBetter={m.higherIsBetter} />
        </LabCard>
        <LabCard
          title={`${m.label}: model and baseline`}
          caption="The raw values behind the differences, side by side for each evaluation set."
          legend={
            <ul className="flex gap-4 text-xs text-muted-foreground">
              <li className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-[var(--chart-1)]" />model</li>
              <li className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-[var(--chart-2)]" />baseline</li>
            </ul>
          }
          learn={{
            concept: "Absolute levels change between seasons (scoring inflation, more matches), which is why the paired difference on the left is the fair comparison.",
            read: "Two bars per set; the taller one wins for higher-is-better metrics.",
            good: "The model bar consistently on the right side of the baseline bar.",
            ours: `Coverage of the p10–p90 range per set: ${t.evaluations.map((e) => `${e.label} ${fmtPct(e.summary.coverage)}`).join(", ")}.`,
          }}
        >
          <BarsChart
            data={t.evaluations.map((e) => ({ set: e.label.replace("Walk-forward", "WF"), model: e.summary[metric].model, baseline: e.summary[metric].baseline }))}
            xKey="set"
            series={[
              { key: "model", label: "Model", color: C.model },
              { key: "baseline", label: "Baseline", color: C.baseline },
            ]}
            yFmt={(n) => (metric === "captain" ? fmtPct(n) : fmtNum(n, metric === "spearman" ? 2 : 0))}
            height={260}
          />
        </LabCard>
      </Grid>

      <div className="flex flex-wrap items-end justify-between gap-2">
        <SectionTitle sub="Pick the held-out set to inspect: per-match results, calibration and residuals.">Inside {setLabel}</SectionTitle>
        <PhaseToggle value={ph} onChange={setPhase} phases={avail} />
      </div>

      {pm && pm.rows.length > 0 && (
        <LabCard
          title="Best-XI points, match by match"
          caption="Actual points of the XI picked from the model's predictions, from the baseline's, and the perfect hindsight XI. Drag the handles to zoom."
          legend={
            <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <li className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded bg-[var(--chart-1)]" />model XI</li>
              <li className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded bg-[var(--chart-2)]" />baseline XI</li>
              <li className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded border-t-2 border-dashed border-[var(--chart-4)]" />hindsight XI</li>
            </ul>
          }
          table={{ columns: ["#", "Match", "Model", "Baseline", "Hindsight"], rows: perMatchData.map((r) => [r.n, r.label, fmtNum(r.model, 0), fmtNum(r.baseline, 0), fmtNum(r.hindsight, 0)]) }}
          learn={{
            concept: (
              <>
                <Term id="best-xi-points">Best-XI points</Term> is the fantasy-relevant score: the optimiser&apos;s team on predicted values, scored with actual points (C ×2, VC ×1.5). The{" "}
                <Term id="hindsight-xi">hindsight XI</Term> is the ceiling.
              </>
            ),
            read: "Each x position is one match in date order. Hover for the exact numbers. Where the violet line is above the gold one the model's team scored more.",
            good: "Model above baseline more often than not, and the average gap to hindsight shrinking relative to the baseline's gap.",
            ours: `The model's XI outscored the baseline's in ${wins} of ${pm.rows.length} matches${ties ? ` (${ties} ties)` : ""}.`,
          }}
        >
          <LinesChart
            data={perMatchData}
            xKey="n"
            brush
            xLabel={(v) => perMatchData[Number(v) - 1]?.label ?? String(v)}
            series={[
              { key: "hindsight", label: "Hindsight XI", color: C.best, dashed: true, width: 1.5 },
              { key: "baseline", label: "Baseline XI", color: C.baseline },
              { key: "model", label: "Model XI", color: C.model },
            ]}
            yFmt={(n) => fmtNum(n, 0)}
            height={300}
          />
        </LabCard>
      )}

      {cal && (
        <>
          <SectionTitle sub="Are the predicted numbers and ranges honest on average?">Calibration</SectionTitle>
          <Grid cols={3}>
            <LabCard
              title="Reliability diagram (mean head)"
              caption="Rows grouped by predicted points; each dot compares a bin's average prediction with its average actual score. Dot size = rows."
              table={{ columns: ["Pred from", "to", "Pred avg", "Actual avg", "Rows"], rows: cal.reliability.map((b) => [fmtNum(b.predLo, 1), fmtNum(b.predHi, 1), fmtNum(b.predMean, 1), fmtNum(b.actualMean, 1), b.n]) }}
              learn={{
                concept: (
                  <>
                    A <Term id="reliability-diagram">reliability diagram</Term> checks <Term id="calibration">calibration</Term>: when the model says ~40, do those players average ~40?
                  </>
                ),
                read: "Dashed diagonal = perfect. Above it the model under-predicts that bin; below it over-predicts.",
                good: "Dots hugging the diagonal across the whole range, especially in the high bins that drive captain picks.",
                ours: reliabilityInsight(cal),
              }}
            >
              <ReliabilityChart bins={cal.reliability} />
            </LabCard>
            <LabCard
              title="Quantile coverage"
              caption="Share of actual scores below each predicted quantile, against the share a calibrated model would show."
              legend={
                <ul className="flex gap-4 text-xs text-muted-foreground">
                  <li className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-[var(--faint)]" />expected</li>
                  <li className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-[var(--chart-1)]" />observed</li>
                </ul>
              }
              table={{
                columns: ["Check", "Expected", "Observed"],
                rows: [
                  ["below p10", "10%", fmtPct(cal.coverage.belowQ10, 1)],
                  ["below p50", "50%", fmtPct(cal.coverage.belowQ50, 1)],
                  ["below p90", "90%", fmtPct(cal.coverage.belowQ90, 1)],
                  ["inside p10–p90", "80%", fmtPct(cal.coverage.inside80, 1)],
                ],
              }}
              learn={{
                concept: (
                  <>
                    Each <Term id="quantile">quantile head</Term> makes a promise: only 10% of actuals should fall below p10, 50% below p50, 90% below p90, so 80% inside p10–p90 (
                    <Term id="coverage">coverage</Term>).
                  </>
                ),
                read: "Grey bar = the promise, violet = what happened. Equal heights = calibrated.",
                good: "Observed within a few points of expected for every quantile.",
                ours: `${quantileInsight(cal)} ${coverageInsight(cal.coverage.inside80)}`,
              }}
            >
              <BarsChart
                data={[
                  { check: "< p10", expected: 0.1, observed: cal.coverage.belowQ10 },
                  { check: "< p50", expected: 0.5, observed: cal.coverage.belowQ50 },
                  { check: "< p90", expected: 0.9, observed: cal.coverage.belowQ90 },
                  { check: "p10–p90", expected: 0.8, observed: cal.coverage.inside80 },
                ]}
                xKey="check"
                series={[
                  { key: "expected", label: "Expected", color: C.muted },
                  { key: "observed", label: "Observed", color: C.model },
                ]}
                yFmt={(n) => fmtPct(n)}
                height={260}
              />
            </LabCard>
            <LabCard
              title="Pinball loss per quantile"
              caption="The quantile heads' own loss on the held-out rows, in points (lower is better)."
              learn={{
                concept: (
                  <>
                    <Term id="pinball-loss">Pinball loss</Term> scores a quantile prediction asymmetrically: for p90, being too low costs 9× more than being too high.
                  </>
                ),
                formula: "Lτ(y, q) = τ·(y − q) if y ≥ q  else  (1 − τ)·(q − y)",
                read: "Not comparable across quantiles (each has its own scale); compare the same quantile across runs or sets.",
                good: "Lower than the pinball loss of a constant quantile (the training-set quantile), and stable between test and walk-forward.",
                ours: `p10 ${fmtNum(cal.pinball.q10, 2)}, p50 ${fmtNum(cal.pinball.q50, 2)}, p90 ${fmtNum(cal.pinball.q90, 2)} pts. The p50 pinball equals half the median's MAE.`,
              }}
            >
              <div className="grid grid-cols-3 gap-3">
                <StatTile label="p10" value={cal.pinball.q10} format={(n) => fmtNum(n, 2)} />
                <StatTile label="p50" value={cal.pinball.q50} format={(n) => fmtNum(n, 2)} />
                <StatTile label="p90" value={cal.pinball.q90} format={(n) => fmtNum(n, 2)} />
              </div>
            </LabCard>
          </Grid>
        </>
      )}

      {res && (
        <>
          <SectionTitle sub="Residual = actual − predicted (mean head). Positive = the player beat the prediction.">Residuals</SectionTitle>
          <Grid cols={2}>
            <LabCard
              title="Residual distribution"
              caption="How far off the mean prediction was, across all rows of the set."
              table={{ columns: ["From", "to", "Rows"], rows: res.hist.map((b) => [b.lo, b.hi, b.n]) }}
              learn={{
                concept: (
                  <>
                    A <Term id="residual">residual</Term> histogram shows the error shape. Fantasy residuals are right-skewed: a mean prediction can&apos;t foresee a century, so big positive misses form
                    a long tail.
                  </>
                ),
                read: "The dashed line is zero. Mass left of zero = over-prediction; right = under-prediction.",
                good: "Centred near zero (no overall bias), with the tail explained by genuinely unpredictable hauls.",
                ours: residualHistInsight(res.hist),
              }}
            >
              <HistogramChart bins={res.hist} color={C.valid} refX={[{ x: 0, label: "0" }]} />
            </LabCard>
            <ResidualGroup title="By role" stats={res.byRole} what="role" />
            <ResidualGroup title="By experience (previous IPL games)" stats={res.byExperience} what="experience" />
            <ResidualGroup title="By batting first" stats={res.byBatsFirst} what="batting order" />
          </Grid>
        </>
      )}
    </div>
  );
}

function ResidualGroup({ title, stats, what }: { title: string; stats: ErrStat[]; what: string }) {
  if (!stats.length) return null;
  return (
    <LabCard
      title={`Residuals ${title.toLowerCase()}`}
      caption="MAE (size of misses) and bias (average signed miss) for each group."
      legend={
        <ul className="flex gap-4 text-xs text-muted-foreground">
          <li className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-[var(--chart-3)]" />MAE</li>
          <li className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-[var(--chart-5)]" />bias</li>
        </ul>
      }
      table={{ columns: ["Group", "MAE", "Bias", "Rows"], rows: stats.map((s) => [s.label, fmtNum(s.mae, 2), fmtNum(s.bias, 2), s.n ?? "–"]) }}
      learn={{
        concept: "One overall MAE can hide groups the model systematically gets wrong. Splitting residuals by group exposes them.",
        formula: "bias = mean(actual − predicted)   (> 0: under-predicted)",
        read: "Blue = average miss size; red = average signed miss (above zero: the group scores more than predicted).",
        good: "Biases near zero in every group; MAE differences that match how volatile the group is.",
        ours: groupErrorInsight(stats, what),
      }}
    >
      <BarsChart
        data={errRows(stats)}
        xKey="group"
        series={[
          { key: "mae", label: "MAE", color: C.valid },
          { key: "bias", label: "Bias", color: C.neg },
        ]}
        refY={[{ y: 0 }]}
        yFmt={(n) => fmtNum(n, 0)}
        height={220}
      />
    </LabCard>
  );
}
