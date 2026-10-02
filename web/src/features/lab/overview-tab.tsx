"use client";

import Link from "next/link";

import { StatTile } from "@/components/data/stat-tile";

import { BarsChart, C } from "./charts";
import { PipelineDiagram } from "./diagrams";
import { fmtCompact, fmtDateTime, fmtDuration, fmtInt, fmtNum, fmtPct, type MetricKey } from "./format";
import { captureRatio, coverageInsight, pairInsight } from "./insights";
import type { EvalSummary, RunSummary, Telemetry } from "./types";
import { Grid, KeyValues, LabCard, MetricTile, ProseCard, SectionTitle, Term, labHref, useLabState } from "./ui";

/** Static explanation (works before any run exists: no numbers). */
export function OverviewIntro({ t }: { t: Telemetry | null }) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <ProseCard title="What the model predicts, and when">
        <p>
          For every player in an IPL match it predicts their <strong>Dream11 fantasy points</strong>. The prediction is made at the <strong>toss</strong>: both playing XIs, the
          venue, who bats first and the weather are known; nothing that happens in the match is.
        </p>
        <p>
          It outputs four numbers per player: an expected value (the <Term id="gradient-boosting">mean head</Term>) and a range, the <Term id="quantile">p10, p50 and p90</Term>{" "}
          quantiles (floor, median, ceiling). An <Term id="best-xi-points">optimiser</Term> then picks the best legal XI and captain from those predictions.
        </p>
        <p>
          The honest question is not “is it accurate?” but “is it better than a simple rule?”. Every result compares against the <Term id="baseline">last-5-games baseline</Term>,
          with a <Term id="bootstrap-ci">confidence interval</Term> so luck is not mistaken for skill.
        </p>
      </ProseCard>
      <LabCard
        title="The pipeline"
        caption="Five stages from raw scorecards to an evaluated fantasy XI. Click a stage to open its tab."
        learn={{
          concept: "A supervised-learning pipeline: features (inputs) and a target (Dream11 points) for every past player-match, a model fitted to map one to the other, and an evaluation on matches the model never saw.",
          read: "Left to right (top to bottom on a phone). Each box shows the size of that stage for the selected run.",
          good: "Every stage is time-aware: features only use the past, and evaluation only scores seasons after the training window.",
          ours: t ? `${fmtCompact(t.data.rows)} rows, ${t.features.length} features, ${t.protocol.heads.length || 4} heads, ${t.evaluations.length} evaluation sets.` : undefined,
        }}
      >
        <PipelineDiagram t={t} />
      </LabCard>
    </div>
  );
}

const KPI_METRICS: MetricKey[] = ["bestXi", "captain", "mae", "spearman"];

function PhaseKpis({ title, s, setLabel }: { title: string; s: EvalSummary; setLabel: string }) {
  const capture = captureRatio(s.bestXi.model, s.bestXi.baseline, s.hindsight);
  return (
    <section>
      <h3 className="text-overline mb-2 text-muted-foreground">
        {title} <span className="num normal-case">· {fmtInt(s.matches)} matches</span>
      </h3>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-6">
        {KPI_METRICS.map((k) => (
          <MetricTile key={k} metric={k} pair={s[k]} className="xl:col-span-1" />
        ))}
        <StatTile label="p10–p90 coverage" value={s.coverage} format={(n) => fmtPct(n, 1)} hint="target 80%" />
        <StatTile
          label="Hindsight best XI"
          value={s.hindsight}
          format={(n) => fmtNum(n, 0)}
          unit="pts"
          hint={capture !== null ? `model closes ${fmtPct(capture)} of the gap to it` : "the perfect team, picked after the match"}
        />
      </div>
      <details className="mt-2 text-xs text-muted-foreground">
        <summary className="cursor-pointer select-none hover:text-foreground">What these numbers say for {setLabel}</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {KPI_METRICS.map((k) => (
            <li key={k}>{pairInsight(s[k], k, setLabel)}</li>
          ))}
          <li>{coverageInsight(s.coverage)}</li>
        </ul>
      </details>
    </section>
  );
}

export function OverviewTab({ t, run, runs }: { t: Telemetry; run: RunSummary; runs: RunSummary[] }) {
  const state = useLabState();
  const test = t.evaluations.find((e) => e.kind === "test");
  const wf = t.evaluations.find((e) => e.kind === "walkforward");
  const trees = Object.values(t.trees).reduce((s, n) => s + n, 0);
  const durations = Object.entries(t.duration)
    .filter(([k]) => k !== "total")
    .map(([k, v]) => ({ stage: k, minutes: Math.round((v / 60) * 10) / 10 }));
  const other = runs.find((r) => r.version !== run.version);
  return (
    <div className="space-y-6">
      <OverviewIntro t={t} />

      <SectionTitle sub="Each tile: the model's value, the baseline's, the difference and its 95% interval (the dot and bar). Hover a term for its meaning, click for the glossary.">
        Headline results
      </SectionTitle>
      {test ? <PhaseKpis title={`${test.label}: held-out season, scored once`} s={test.summary} setLabel={test.label} /> : <p className="text-sm text-muted-foreground">No test evaluation in this run.</p>}
      {wf && <PhaseKpis title={`${wf.label}: retrained every ${t.protocol.wfBlock ?? "few"} matches, like live use`} s={wf.summary} setLabel={wf.label} />}

      <SectionTitle sub="How big the model is and what it cost to train.">Model size and cost</SectionTitle>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <StatTile label="Learned parameters" value={t.nLearned} format={fmtCompact} hint={<Link className="underline decoration-dotted" href={labHref(state, { tab: "training" })}>what counts as one?</Link>} />
        <StatTile label="Trees (all heads)" value={trees || null} format={fmtInt} hint={Object.entries(t.trees).map(([h, n]) => `${h} ${n}`).join(" · ")} />
        <StatTile label="Features" value={t.features.length || null} hint={`${new Set(t.features.map((f) => f.group)).size} groups`} />
        <StatTile label="Training rows" value={t.data.rows} format={fmtCompact} hint={`${fmtInt(t.data.matches)} matches · ${fmtInt(t.data.players)} players`} />
        <StatTile label="Total run time" value={fmtDuration(t.duration.total ?? null)} hint="features → tuning → test → walk-forward" />
        <StatTile label="Created" value={fmtDateTime(t.createdAt).split(",")[0]} hint={<span className="font-mono">{t.version}</span>} />
      </div>

      <Grid cols={2}>
        {durations.length > 0 && (
          <LabCard
            title="Where the training time went"
            caption="Minutes spent in each stage of the run."
            table={{ columns: ["Stage", "Minutes"], rows: durations.map((d) => [d.stage, d.minutes]) }}
            learn={{
              concept: "Tuning is usually the expensive part: each hyper-parameter setting is fitted once per cross-validation fold, and every fit trains four heads with early stopping.",
              read: "Longer bars = more compute. Walk-forward retrains the model before every block of matches, so it scales with the season length.",
              good: "Most time in tuning/walk-forward, little in feature building, is typical.",
              ours: `The run took ${fmtDuration(t.duration.total ?? null)} in total; the biggest stage was ${durations.reduce((m, d) => (d.minutes > m.minutes ? d : m), durations[0]).stage}.`,
            }}
          >
            <BarsChart data={durations} xKey="stage" series={[{ key: "minutes", label: "Minutes", color: C.model }]} height={200} yFmt={(n) => fmtNum(n, 0)} />
          </LabCard>
        )}
        <LabCard title="Run details" caption="Identity of this run and the environment it ran in.">
          <KeyValues
            items={[
              { k: "Version", v: <span className="font-mono text-xs">{t.version}</span> },
              { k: "Created", v: fmtDateTime(t.createdAt) },
              { k: "Latest run", v: run.isLatest ? "yes" : "no" },
              { k: "Baseline", v: <span className="text-xs font-normal">{t.baselines.last5 ?? "last-5-games mean"}</span> },
              ...Object.entries(t.environment).map(([k, v]) => ({ k, v: String(v) })),
              { k: "Artifacts", v: [run.hasTelemetry && "telemetry", run.hasBooster && "boosters", run.hasEvalFrame && "eval frame", run.inDb && "DB"].filter(Boolean).join(" · ") },
            ]}
          />
          {other && (
            <Link href={labHref(state, { tab: "compare", a: other.version, b: run.version })} className="mt-4 inline-flex h-9 items-center text-sm font-medium text-brand underline-offset-4 hover:underline">
              Compare with {other.version} →
            </Link>
          )}
        </LabCard>
      </Grid>
    </div>
  );
}
