"use client";

import { AlertTriangle, FlaskConical } from "lucide-react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { SampleDataNote } from "@/components/shell/sample-data-note";
import { TabLinks } from "@/components/shell/tab-links";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

import { ComparePanel } from "./compare-tab";
import { DataTab } from "./data-tab";
import { EvaluationTab } from "./evaluation-tab";
import { ExplainTab } from "./explain-tab";
import { FeaturesTab } from "./features-tab";
import { fmtDateTime } from "./format";
import { GlossaryTab } from "./glossary-tab";
import { OverviewTab, OverviewIntro } from "./overview-tab";
import { PredictionsTab } from "./predictions-tab";
import { useRuns, useTelemetry } from "./queries";
import { TrainingTab } from "./training-tab";
import type { RunSummary } from "./types";
import { LabProvider, labHref, type LabState, type LabTab } from "./ui";

const TAB_LABELS: Record<LabTab, string> = {
  overview: "Overview",
  data: "Data",
  features: "Features",
  training: "Training",
  evaluation: "Evaluation",
  explain: "Explainability",
  predictions: "Predictions",
  compare: "Compare runs",
  glossary: "Glossary",
};

/** Which run to show: the URL's if it exists, else the latest, else the newest. */
export function pickRun(runs: RunSummary[], wanted: string | null): RunSummary | null {
  return runs.find((r) => r.version === wanted) ?? runs.find((r) => r.isLatest) ?? runs[0] ?? null;
}

export function LabView({ state }: { state: LabState }) {
  const runsQ = useRuns();
  const runs = runsQ.data ?? [];
  const run = pickRun(runs, state.run);
  const telQ = useTelemetry(run?.hasTelemetry ? run.version : null);
  const ctx: LabState = { ...state, run: state.run && run?.version === state.run ? state.run : null };
  const t = telQ.data ?? null;

  const body = () => {
    if (state.tab === "glossary") return <GlossaryTab />;
    if (runsQ.isPending) return <TabSkeleton />;
    if (runsQ.isError)
      return (
        <EmptyState
          icon={AlertTriangle}
          title="The model API is unreachable"
          why={`Couldn't load the list of training runs (${(runsQ.error as Error).message}).`}
          when="Retry once the API is running."
          action={{ href: "/lab?tab=glossary", label: "Read the glossary meanwhile" }}
        />
      );
    if (!run)
      return state.tab === "overview" ? (
        <div className="space-y-6">
          <NoRun />
          <OverviewIntro t={null} />
        </div>
      ) : (
        <NoRun />
      );
    if (state.tab === "compare") return <ComparePanel runs={runs} />;
    if (!run.hasTelemetry)
      return (
        <EmptyState
          icon={FlaskConical}
          title={`Run ${run.version} has no telemetry yet`}
          why="The training run is registered but its telemetry.json (the numbers behind every chart here) hasn't been written. It may still be training or evaluating."
          when="As soon as the run finishes writing models/<version>/telemetry.json."
          action={{ href: labHref(ctx, { tab: "glossary" }), label: "Read the glossary meanwhile" }}
        />
      );
    if (telQ.isPending) return <TabSkeleton />;
    if (telQ.isError || !t)
      return <EmptyState icon={AlertTriangle} title="Couldn't load this run's telemetry" why={(telQ.error as Error | null)?.message ?? "Unknown error"} when="Retry in a moment." />;
    switch (state.tab) {
      case "data":
        return <DataTab t={t} />;
      case "features":
        return <FeaturesTab t={t} />;
      case "training":
        return <TrainingTab t={t} />;
      case "evaluation":
        return <EvaluationTab t={t} />;
      case "explain":
        return <ExplainTab t={t} version={run.version} />;
      case "predictions":
        return <PredictionsTab t={t} version={run.version} />;
      default:
        return <OverviewTab t={t} run={run} runs={runs} />;
    }
  };

  return (
    <LabProvider value={ctx}>
      <PageHeader
        overline="Under the hood"
        title="Model Lab"
        subtitle="How the fantasy-points model was built, trained and tested, and how good it really is. Every chart explains itself: open “Learn more”."
        actions={runs.length > 0 ? <RunPicker runs={runs} current={run?.version ?? null} state={ctx} /> : undefined}
      />
      {t?.notes && /synthetic|sample/i.test(t.notes) && <SampleDataNote className="mb-4">{t.notes}</SampleDataNote>}
      <TabLinks
        label="Model Lab sections"
        active={state.tab}
        tabs={(Object.keys(TAB_LABELS) as LabTab[]).map((k) => ({ key: k, label: TAB_LABELS[k], disabled: !run && k !== "glossary" && k !== "overview" }))}
        hrefFor={(k) => labHref(ctx, { tab: k as LabTab, match: state.tab === "predictions" || state.tab === "explain" ? state.match : null, player: null })}
      />
      {body()}
    </LabProvider>
  );
}

function NoRun() {
  return (
    <EmptyState
      icon={FlaskConical}
      title="No training run yet: the model is training"
      why="Nothing here is filled in until a real training run has written its artifacts. The Lab never shows placeholder numbers as results."
      when="When the first run lands in models/<version>/ (telemetry.json, boosters, evaluation frame), this page fills in automatically."
      action={{ href: "/lab?tab=glossary", label: "Learn the concepts first: open the glossary" }}
      bullets={[
        "Overview: headline accuracy vs a last-5-games baseline, with confidence intervals",
        "Data and features: what the model sees, and how leakage is prevented",
        "Training: learning curves, tuning, early stopping",
        "Evaluation: per-season results, calibration, residuals",
        "Explainability: SHAP for any prediction; Predictions: every match, every player",
      ]}
    />
  );
}

function RunPicker({ runs, current, state }: { runs: RunSummary[]; current: string | null; state: LabState }) {
  const router = useRouter();
  return (
    <Select
      value={current ?? ""}
      onValueChange={(v) => {
        if (!v) return;
        router.push(labHref(state, { run: v, match: null, player: null }), { scroll: false });
      }}
    >
      <SelectTrigger aria-label="Training run" className="h-9 max-w-[min(80vw,22rem)] min-w-48 rounded-[10px] bg-card">
        <span className="text-xs text-muted-foreground">Run</span>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {runs.map((r) => (
          <SelectItem key={r.version} value={r.version}>
            <span className="font-mono text-xs">{r.version}</span>
            <span className="ml-2 text-xs text-muted-foreground">
              {r.isLatest ? "latest · " : ""}
              {fmtDateTime(r.createdAt)}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function TabSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading the run" className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-32 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
    </div>
  );
}
