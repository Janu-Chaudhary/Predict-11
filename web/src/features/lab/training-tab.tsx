"use client";

import { useMemo, useState } from "react";

import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { cn } from "@/lib/utils";

import { BarsChart, BarsWithLine, C, LinesChart, curveRows } from "./charts";
import { abbrev, fmtCompact, fmtInt, fmtNum, paramValue } from "./format";
import { curveInsight, tuningInsight } from "./insights";
import type { Telemetry, TuningRow } from "./types";
import { Grid, KeyValues, LabCard, ProseCard, SectionTitle, Segmented, Term } from "./ui";

const HEAD_INFO: Record<string, { loss: string; what: string }> = {
  mean: { loss: "squared error (L2)", what: "the expected points" },
  q10: { loss: "pinball, τ = 0.1", what: "the floor (10th percentile)" },
  q50: { loss: "pinball, τ = 0.5", what: "the median" },
  q90: { loss: "pinball, τ = 0.9", what: "the ceiling (90th percentile)" },
};

export const PARAM_INFO: Record<string, { what: string; up: string; term: string }> = {
  num_leaves: { what: "Maximum leaves per tree: how many groups of rows one tree can separate.", up: "More = more complex interactions, higher overfitting risk.", term: "num-leaves" },
  min_child_samples: { what: "Minimum rows in a leaf; a leaf is an average of at least this many rows.", up: "More = smoother, more conservative trees.", term: "min-child-samples" },
  learning_rate: { what: "Shrinkage: the fraction of each new tree added to the model.", up: "Higher = fewer trees needed but noisier fit; lower = more trees, usually better generalisation.", term: "learning-rate" },
  feature_fraction: { what: "Share of features each tree may use (random subset per tree).", up: "Lower = more diverse trees, less reliance on any single feature.", term: "feature-fraction" },
  bagging_fraction: { what: "Share of rows sampled for each iteration.", up: "Lower = more randomness (regularisation), faster training.", term: "bagging" },
  bagging_freq: { what: "Resample the rows every k iterations (0 disables bagging).", up: "1 = a fresh row sample every tree.", term: "bagging" },
  lambda_l2: { what: "L2 penalty on leaf values, shrinking them toward zero.", up: "More = smaller, more cautious leaf values.", term: "regularisation" },
  lambda_l1: { what: "L1 penalty on leaf values (can zero them out).", up: "More = sparser leaves.", term: "regularisation" },
};

function settingKey(p: Record<string, unknown>) {
  return Object.entries(p)
    .map(([k, v]) => `${abbrev(k)} ${paramValue(v)}`)
    .join(", ");
}

function isChosen(row: TuningRow, chosen: Record<string, unknown>) {
  return Object.entries(row.params).every(([k, v]) => chosen[k] === undefined || chosen[k] === v);
}

const SERIES_COLORS = ["var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

export function TrainingTab({ t }: { t: Telemetry }) {
  const sets = Object.keys(t.curves).sort((a, b) => (a === "final" ? -1 : b === "final" ? 1 : a.localeCompare(b)));
  const [set, setSet] = useState(sets[0] ?? "final");
  const heads = Object.keys(t.curves[set] ?? {});
  const [head, setHead] = useState("mean");
  const h = heads.includes(head) ? head : heads[0];
  const curve = h ? t.curves[set]?.[h] : undefined;
  const rows = useMemo(() => (curve ? curveRows(curve) : []), [curve]);

  const folds = useMemo(() => [...new Set(t.tuning.flatMap((r) => Object.keys(r.foldMae)))].sort(), [t.tuning]);
  const paramKeys = useMemo(() => [...new Set(t.tuning.flatMap((r) => Object.keys(r.params)))], [t.tuning]);
  const tuningSeries = useMemo(() => {
    let other = 0;
    return t.tuning.map((r, i) => {
      const chosen = isChosen(r, t.chosenParams);
      return { key: `s${i}`, label: settingKey(r.params) + (chosen ? " (chosen)" : ""), color: chosen ? C.model : t.tuning.length <= 5 ? SERIES_COLORS[other++ % 4] : "var(--faint)", width: chosen ? 3 : 1.5, opacity: chosen ? 1 : 0.8 };
    });
  }, [t.tuning, t.chosenParams]);
  const tuningData = folds.map((f) => ({ fold: f, ...Object.fromEntries(t.tuning.map((r, i) => [`s${i}`, r.foldMae[f] ?? null])) }));

  const tuningCols: StatColumn<TuningRow>[] = [
    ...paramKeys.map((k) => ({ key: `p:${k}`, header: abbrev(k), label: k, sortable: true, value: (r: TuningRow) => r.params[k] as number, cell: (r: TuningRow) => paramValue(r.params[k]) })),
    ...folds.map((f) => ({ key: `f:${f}`, header: `MAE ${f}`, sortable: true, hideBelow: "md" as const, value: (r: TuningRow) => r.foldMae[f], cell: (r: TuningRow) => fmtNum(r.foldMae[f], 3) })),
    { key: "mean", header: "Mean MAE", sortable: true, value: (r) => r.meanMae, cell: (r) => <span className="font-semibold">{fmtNum(r.meanMae, 3)}</span> },
    { key: "sec", header: "Seconds", sortable: true, hideBelow: "sm", value: (r) => r.seconds, cell: (r) => fmtNum(r.seconds, 0) },
  ];

  const halflife = t.protocol.halflife;
  const newest = (t.protocol.testSeason ?? 2025) - 1;
  const weights = halflife ? t.data.rowsBySeason.filter((s) => s.year <= newest).map((s) => ({ season: String(s.year), weight: Math.round(Math.pow(0.5, (newest - s.year) / halflife) * 1000) / 1000 })) : [];

  const nTrees = Object.values(t.trees).reduce((s, n) => s + n, 0);
  const avgLeaves = nTrees && t.nLearned ? (t.nLearned / nTrees + 1) / 2 : null;
  const F = t.features.length || 84;
  const mlp = F * 64 + 64 + 64 * 64 + 64 + 64 + 1;

  return (
    <div className="space-y-6">
      <SectionTitle sub="How the error on training data and on held-out data evolves as trees are added.">Learning curves</SectionTitle>
      {curve ? (
        <LabCard
          title={`Learning curve · ${h} head · ${set === "final" ? "test model" : set.replace("cv:", "CV fold ")}`}
          caption={`${curve.metric} loss per boosting round on the training rows (violet) and the inner-validation rows (blue). Drag the handles below the chart to zoom.`}
          actions={
            <>
              {sets.length > 1 && <Segmented size="sm" label="Model fit" value={set} onChange={setSet} options={sets.map((s) => ({ key: s, label: s === "final" ? "Final" : s.replace("cv:", "CV ") }))} />}
              <Segmented size="sm" label="Head" value={h ?? "mean"} onChange={setHead} options={heads.map((k) => ({ key: k, label: k }))} />
            </>
          }
          legend={
            <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <li className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded bg-[var(--chart-1)]" />train</li>
              <li className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded bg-[var(--chart-3)]" />validation</li>
              {curve.bestIter !== null && <li className="inline-flex items-center gap-1.5"><span className="h-3 w-0 border-l border-dashed border-foreground/60" />best round ({curve.bestIter})</li>}
            </ul>
          }
          table={{ columns: ["Round", "Train", "Validation"], rows: rows.map((r) => [r.iter, fmtNum(r.train, 4), fmtNum(r.valid, 4)]) }}
          learn={{
            concept: (
              <>
                <Term id="gradient-boosting">Boosting</Term> adds one small tree per round, each fixing the remaining error. Training loss almost always keeps falling. Validation loss falls, flattens,
                then rises once trees start fitting noise: <Term id="overfitting">overfitting</Term>. <Term id="early-stopping">Early stopping</Term> watches the validation curve and keeps the
                best round; the final model is then refitted on all training data with that many trees.
              </>
            ),
            formula: h === "mean" ? "L2 = mean((y − ŷ)²)" : `pinball_τ = mean(max(τ·(y − q), (τ − 1)·(y − q))),  τ = ${h?.replace("q", "0.").replace("0.50", "0.5")}`,
            read: "x = number of trees so far, y = loss (lower is better). The gap between the lines is the generalisation gap; the dashed line is where early stopping chose to stop.",
            good: "Validation flattens well before the round cap, the gap stays modest, and the best round is not the very last one (otherwise the cap, not the data, decided).",
            ours: curveInsight(curve, h ?? "mean"),
          }}
        >
          <LinesChart
            data={rows}
            xKey="iter"
            brush
            series={[
              { key: "train", label: "Train", color: C.model },
              { key: "valid", label: "Validation", color: C.valid },
            ]}
            refX={curve.bestIter !== null ? [{ x: rows.reduce((b, r) => (Math.abs(r.iter - curve.bestIter!) < Math.abs(b - curve.bestIter!) ? r.iter : b), rows[0]?.iter ?? 0), label: "best" }] : undefined}
            yFmt={(n) => fmtNum(n, n < 10 ? 2 : 0)}
            height={300}
          />
        </LabCard>
      ) : (
        <p className="text-sm text-muted-foreground">No learning curves were recorded for this run.</p>
      )}

      <SectionTitle sub="A small grid of settings, each scored by rolling-origin cross-validation; the lowest mean fold MAE wins.">Hyper-parameter tuning</SectionTitle>
      {t.tuning.length > 0 ? (
        <Grid cols={2}>
          <LabCard
            title="Fold MAE per setting"
            caption="Each line is one setting; each point its MAE on one CV season. The chosen setting is the thick violet line."
            legend={
              <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                {tuningSeries.map((s) => (
                  <li key={s.key} className="inline-flex items-center gap-1.5">
                    <span className="h-0.5 w-4 rounded" style={{ background: s.color, height: s.width }} />
                    {s.label}
                  </li>
                ))}
              </ul>
            }
            learn={{
              concept: (
                <>
                  <Term id="hyperparameter">Hyper-parameters</Term> are chosen, not learned. Each setting is trained and scored on every <Term id="rolling-origin">rolling-origin</Term> fold; averaging
                  over folds avoids picking a setting that just got lucky on one season.
                </>
              ),
              read: "Lines that sit lower are better. Lines that cross mean the ranking depends on the season, so the average matters.",
              good: "A setting that is best (or near best) on most folds, not just on average.",
              ours: tuningInsight(t.tuning, t.chosenParams),
            }}
          >
            <LinesChart data={tuningData} xKey="fold" series={tuningSeries} yFmt={(n) => fmtNum(n, 1)} height={260} />
          </LabCard>
          <div className="min-w-0 space-y-2">
            <StatTable
              columns={tuningCols}
              rows={t.tuning}
              rowKey={(_, i) => String(i)}
              caption="Hyper-parameter grid with MAE per CV fold"
              initialSort={{ key: "mean", dir: "asc" }}
              rowClassName={(r) => (isChosen(r, t.chosenParams) ? "bg-brand/10" : undefined)}
              dense
            />
            <p className="text-xs text-muted-foreground">Highlighted row = the chosen setting. MAE is the mean head&apos;s mean absolute error (points) on each validation season.</p>
          </div>
        </Grid>
      ) : (
        <p className="text-sm text-muted-foreground">No tuning results recorded.</p>
      )}

      <SectionTitle sub="Every setting the final model was trained with, and what it does.">Chosen parameters</SectionTitle>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Object.entries(t.chosenParams).map(([k, v]) => {
          const info = PARAM_INFO[k];
          const tuned = paramKeys.includes(k);
          return (
            <section key={k} className="rounded-xl border border-border bg-card p-4 shadow-e1">
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="font-mono text-sm font-medium">{info ? <Term id={info.term}>{k}</Term> : k}</h3>
                <span className="font-condensed num text-2xl font-bold">{paramValue(v)}</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{tuned ? "tuned on the CV grid" : "fixed"}</p>
              {info && (
                <>
                  <p className="mt-2 text-sm">{info.what}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{info.up}</p>
                </>
              )}
            </section>
          );
        })}
      </div>

      <SectionTitle sub="What the trained model physically consists of.">Trees and parameters</SectionTitle>
      <Grid cols={2}>
        <LabCard
          title="Per head"
          caption="Trees chosen by early stopping and learned values (split thresholds + leaf values) for each of the four heads."
          table={{ columns: ["Head", "Trees", "Learned values"], rows: Object.keys(t.trees).map((k) => [k, t.trees[k], t.nLearnedByHead[k] ?? "–"]) }}
        >
          <ul className="divide-y divide-border">
            {Object.keys(t.trees).map((k) => (
              <li key={k} className="grid grid-cols-[4rem_1fr_auto] items-center gap-3 py-2">
                <span className="font-mono text-sm font-medium">{k}</span>
                <span className="text-xs text-muted-foreground">
                  predicts {HEAD_INFO[k]?.what ?? k}; loss {HEAD_INFO[k]?.loss ?? "?"}
                </span>
                <span className="num text-right text-sm">
                  <span className="font-semibold">{fmtInt(t.trees[k])}</span> trees
                  {t.nLearnedByHead[k] !== undefined && <span className="block text-xs text-muted-foreground">{fmtCompact(t.nLearnedByHead[k])} values</span>}
                </span>
              </li>
            ))}
          </ul>
        </LabCard>
        <ProseCard title="What is a “parameter” for a tree model?">
          <p>
            A neural network&apos;s <Term id="parameters">parameters</Term> are its weights, all adjusted together by gradient descent. A boosted tree model&apos;s are the{" "}
            <strong>split thresholds</strong> (one per internal node, e.g. “ewm_5 &lt; 31.2”) and <strong>leaf values</strong> (the points a leaf adds). A tree with L leaves has L − 1 splits,
            so 2L − 1 learned values. Trees are built one at a time and never revised.
          </p>
          <KeyValues
            items={[
              { k: "Trees in all heads", v: fmtInt(nTrees) },
              { k: "Average leaves per tree", v: fmtNum(avgLeaves, 1) },
              { k: "Learned values (all heads)", v: fmtInt(t.nLearned) },
              { k: `For scale: MLP ${F}→64→64→1`, v: fmtInt(mlp) },
            ]}
          />
          <p className="text-muted-foreground">
            The numbers aren&apos;t directly comparable: a tree&apos;s threshold is a discrete choice, a weight is continuous. What matters for overfitting is the{" "}
            <Term id="regularisation">regularisation</Term> (leaves, min rows per leaf, learning rate, early stopping), not the raw count.
          </p>
        </ProseCard>
      </Grid>

      <Grid cols={2}>
        {weights.length > 0 && (
          <LabCard
            title="Recency weighting"
            caption={`How much one row from each season counts when training the ${t.protocol.testSeason ?? "test"} model (weight halves every ${halflife} seasons).`}
            table={{ columns: ["Season", "Weight"], rows: weights.map((w) => [w.season, w.weight]) }}
            learn={{
              concept: (
                <>
                  <Term id="recency-weighting">Recency weighting</Term> makes the loss care more about recent seasons, because the game changes (scoring rates, impact player). Old data still helps
                  with rare situations, so it is down-weighted rather than dropped.
                </>
              ),
              formula: `weight = 0.5 ^ ((${newest} − season) / ${halflife})`,
              read: "Bar height = the multiplier on that season's rows in the loss.",
              good: "A half-life long enough to keep data volume, short enough to track the modern game.",
              ours: `A ${weights[0]?.season} row counts ${fmtNum(weights[0]?.weight, 3)}× as much as a ${newest} row.`,
            }}
          >
            <BarsChart data={weights} xKey="season" series={[{ key: "weight", label: "Weight", color: C.model }]} yFmt={(n) => fmtNum(n, 2)} height={220} />
          </LabCard>
        )}
        {t.wfTimeline.length > 0 && (
          <LabCard
            title={`Walk-forward ${t.protocol.wfSeason ?? ""}: block by block`}
            caption={`The season replayed in blocks of ${t.protocol.wfBlock ?? "?"} matches: retrain on everything before the block, then predict it. Bars = MAE, lines = best-XI points.`}
            table={{
              columns: ["Block", "Matches", "Train rows", "MAE", "XI model", "XI baseline"],
              rows: t.wfTimeline.map((b) => [b.block, b.nMatches ?? "–", b.trainRows ?? "–", fmtNum(b.mae, 2), fmtNum(b.xiModel, 1), fmtNum(b.xiBase, 1)]),
            }}
            legend={
              <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <li className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-[var(--chart-3)]" />MAE (left axis)</li>
                <li className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded bg-[var(--chart-1)]" />model XI pts</li>
                <li className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded bg-[var(--chart-2)]" />baseline XI pts</li>
              </ul>
            }
            learn={{
              concept: (
                <>
                  <Term id="walk-forward">Walk-forward</Term> mimics production: the model only ever sees matches already played. Each block adds about {t.protocol.wfBlock ?? 10} matches of new training
                  data.
                </>
              ),
              read: "Watch whether the model line stays above the baseline line block after block, and whether MAE drifts as the season goes on.",
              good: "Model above baseline in most blocks; no upward MAE drift (which would signal the model going stale).",
              ours: (() => {
                const wins = t.wfTimeline.filter((b) => b.xiModel !== null && b.xiBase !== null && b.xiModel > b.xiBase).length;
                return `The model's XI beat the baseline's in ${wins} of ${t.wfTimeline.length} blocks.`;
              })(),
            }}
          >
            <BarsWithLine
              data={t.wfTimeline.map((b) => ({ block: `B${b.block}`, mae: b.mae, xi_model: b.xiModel, xi_base: b.xiBase }))}
              xKey="block"
              bar={{ key: "mae", label: "MAE", color: C.valid }}
              line={[
                { key: "xi_model", label: "Model XI", color: C.model },
                { key: "xi_base", label: "Baseline XI", color: C.baseline },
              ]}
            />
          </LabCard>
        )}
      </Grid>
      <p className={cn("text-xs text-muted-foreground", !t.protocol.innerValidation && "hidden")}>
        Inner validation for early stopping: {t.protocol.innerValidation}. Patience {t.protocol.earlyStopping ?? "?"} rounds, cap {fmtInt(t.protocol.maxTrees)} trees.
      </p>
    </div>
  );
}
