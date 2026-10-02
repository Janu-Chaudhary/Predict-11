"use client";

import { GitCompareArrows } from "lucide-react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/shell/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

import { HBars } from "./charts";
import { METRICS, PHASE_LABEL, fmtDateTime, fmtNum, fmtPct, fmtSigned, paramValue, type MetricKey } from "./format";
import { useCompare } from "./queries";
import type { MetricDelta, RunSummary } from "./types";
import { Grid, LabCard, labHref, useLabState } from "./ui";

const METRIC_KEY: Record<string, MetricKey | "coverage"> = { best_xi_points: "bestXi", captain_top2_rate: "captain", mae: "mae", spearman: "spearman", p10_p90_coverage: "coverage" };

function metricFmt(m: MetricDelta) {
  const k = METRIC_KEY[m.metric];
  if (k === "coverage") return { label: "p10–p90 coverage", fmt: (n: number | null) => fmtPct(n, 1), diff: (n: number | null) => fmtSigned(n === null ? null : n * 100, 1, " pp") };
  if (!k) return { label: m.metric, fmt: (n: number | null) => fmtNum(n, 3), diff: (n: number | null) => fmtSigned(n, 3) };
  return { label: METRICS[k].label, fmt: METRICS[k].fmt, diff: METRICS[k].diffFmt };
}

/** Is B an improvement over A on this metric? Coverage: closer to 80% is better. */
export function improved(m: MetricDelta): boolean | null {
  if (m.delta === null || m.a === null || m.b === null || m.delta === 0) return null;
  if (m.metric === "p10_p90_coverage") return Math.abs(m.b - 0.8) < Math.abs(m.a - 0.8);
  return m.higherIsBetter ? m.delta > 0 : m.delta < 0;
}

function RunSelect({ label, value, runs, onChange }: { label: string; value: string | null; runs: RunSummary[]; onChange: (v: string) => void }) {
  return (
    <Select value={value ?? ""} onValueChange={(v) => v && onChange(v)}>
      <SelectTrigger aria-label={label} className="h-9 w-full min-w-0 rounded-[10px] bg-card sm:w-80">
        <span className="text-xs text-muted-foreground">{label}</span>
        <SelectValue placeholder="Pick a run" />
      </SelectTrigger>
      <SelectContent>
        {runs.map((r) => (
          <SelectItem key={r.version} value={r.version}>
            <span className="font-mono text-xs">{r.version}</span>
            <span className="ml-2 text-xs text-muted-foreground">{fmtDateTime(r.createdAt)}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function ComparePanel({ runs }: { runs: RunSummary[] }) {
  const state = useLabState();
  const router = useRouter();
  const withTel = runs.filter((r) => r.hasTelemetry);
  const a = state.a ?? withTel[1]?.version ?? null;
  const b = state.b ?? withTel[0]?.version ?? null;
  const q = useCompare(a, b);
  const go = (patch: { a?: string; b?: string }) => router.replace(labHref(state, { a, b, ...patch }), { scroll: false });

  if (withTel.length < 2)
    return (
      <EmptyState
        icon={GitCompareArrows}
        title="Only one run so far"
        why="Comparing needs at least two training runs with telemetry. Re-train with different settings or features and both will appear here."
        when="After the next training run."
        action={{ href: labHref(state, { tab: "overview" }), label: "Back to the overview" }}
      />
    );

  const c = q.data;
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <RunSelect label="A" value={a} runs={withTel} onChange={(v) => go({ a: v })} />
        <span className="text-sm text-muted-foreground">→</span>
        <RunSelect label="B" value={b} runs={withTel} onChange={(v) => go({ b: v })} />
      </div>
      {a === b && <p className="text-sm text-muted-foreground">Pick two different runs.</p>}
      {q.isPending && a !== b && <Skeleton className="h-80 rounded-xl" />}
      {q.isError && <p className="text-sm text-muted-foreground">{(q.error as Error).message}</p>}
      {c && (
        <>
          <Grid cols={2}>
            <LabCard
              title="Headline metrics: B relative to A"
              caption="Each metric for both runs on the test and walk-forward sets. Green = B is better."
              table={{ columns: ["Set", "Metric", "A", "B", "Δ"], rows: c.metrics.map((m) => [PHASE_LABEL[m.phase], metricFmt(m).label, metricFmt(m).fmt(m.a), metricFmt(m).fmt(m.b), metricFmt(m).diff(m.delta)]) }}
              learn={{
                concept: "Comparing runs on the same held-out sets shows whether a change (new features, other settings) helped. Differences smaller than the confidence intervals on the Overview are likely noise.",
                read: "A is the reference, B the candidate. Coverage counts as better when closer to 80%.",
                good: "B better on best-XI points and MAE on both sets, not just one.",
                ours: `${c.metrics.filter((m) => improved(m) === true).length} of ${c.metrics.filter((m) => m.delta !== null).length} comparable metrics improved from A to B.`,
              }}
            >
              <table className="num w-full text-sm">
                <thead>
                  <tr className="text-overline text-muted-foreground">
                    <th className="py-1 text-left font-medium">Metric</th>
                    <th className="py-1 text-right font-medium">A</th>
                    <th className="py-1 text-right font-medium">B</th>
                    <th className="py-1 text-right font-medium">Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {(["test", "walkforward"] as const).map((ph) => (
                    <PhaseRows key={ph} phase={ph} rows={c.metrics.filter((m) => m.phase === ph)} />
                  ))}
                </tbody>
              </table>
            </LabCard>
            <LabCard title="Parameters" caption="Chosen settings in each run; changed ones are highlighted.">
              <table className="num w-full text-sm">
                <thead>
                  <tr className="text-overline text-muted-foreground">
                    <th className="py-1 text-left font-medium">Parameter</th>
                    <th className="py-1 text-right font-medium">A</th>
                    <th className="py-1 text-right font-medium">B</th>
                  </tr>
                </thead>
                <tbody>
                  {c.params.map((p) => (
                    <tr key={p.name} className={cn("border-t border-border", p.changed && "bg-brand/10")}>
                      <td className="py-1.5 font-mono text-xs">{p.name}</td>
                      <td className="py-1.5 text-right">{paramValue(p.a)}</td>
                      <td className={cn("py-1.5 text-right", p.changed && "font-semibold")}>{paramValue(p.b)}</td>
                    </tr>
                  ))}
                  <tr className="border-t border-border">
                    <td className="py-1.5 text-xs text-muted-foreground">trees (mean head)</td>
                    <td className="py-1.5 text-right">{c.a.trees.mean ?? "–"}</td>
                    <td className="py-1.5 text-right">{c.b.trees.mean ?? "–"}</td>
                  </tr>
                  <tr className="border-t border-border">
                    <td className="py-1.5 text-xs text-muted-foreground">features</td>
                    <td className="py-1.5 text-right">{c.a.nFeatures ?? "–"}</td>
                    <td className="py-1.5 text-right">{c.b.nFeatures ?? "–"}</td>
                  </tr>
                </tbody>
              </table>
              {(c.onlyA.length > 0 || c.onlyB.length > 0) && (
                <p className="mt-3 text-xs text-muted-foreground">
                  {c.onlyB.length > 0 && <>Added in B: <span className="font-mono">{c.onlyB.join(", ")}</span>. </>}
                  {c.onlyA.length > 0 && <>Removed in B: <span className="font-mono">{c.onlyA.join(", ")}</span>.</>}
                </p>
              )}
            </LabCard>
          </Grid>
          <LabCard
            title="Biggest changes in feature importance"
            caption="Change in each feature's share of total gain from A to B (violet = more important in B)."
            table={{ columns: ["Feature", "A share", "B share", "Δ", "A rank", "B rank"], rows: c.importance.map((i) => [i.feature, fmtPct(i.aShare, 2), fmtPct(i.bShare, 2), fmtSigned(i.delta === null ? null : i.delta * 100, 2, " pp"), i.aRank ?? "–", i.bRank ?? "–"]) }}
            learn={{
              concept: "When a run adds a feature or changes settings, importance shifts: new features take credit from correlated old ones.",
              read: "Bars right of centre gained share in B; left lost share.",
              good: "Shifts you can explain by what changed between the runs.",
              ours: c.importance[0] ? `Largest shift: ${c.importance[0].feature} (${fmtSigned((c.importance[0].delta ?? 0) * 100, 2, " pp")}).` : undefined,
            }}
          >
            <HBars
              items={c.importance
                .filter((i) => i.delta !== null)
                .slice(0, 20)
                .map((i) => ({ key: i.feature, label: <span className="font-mono text-xs">{i.feature}</span>, value: (i.delta ?? 0) * 100, sub: `#${i.aRank ?? "–"}→#${i.bRank ?? "–"}` }))}
              fmt={(n) => fmtSigned(n, 2)}
            />
          </LabCard>
        </>
      )}
    </div>
  );
}

function PhaseRows({ phase, rows }: { phase: "test" | "walkforward"; rows: MetricDelta[] }) {
  return (
    <>
      <tr>
        <td colSpan={4} className="text-overline pt-3 pb-1 text-muted-foreground">
          {PHASE_LABEL[phase]}
        </td>
      </tr>
      {rows.map((m) => {
        const f = metricFmt(m);
        const imp = improved(m);
        return (
          <tr key={m.metric} className="border-t border-border">
            <td className="py-1.5 text-[13px]">{f.label}</td>
            <td className="py-1.5 text-right">{f.fmt(m.a)}</td>
            <td className="py-1.5 text-right">{f.fmt(m.b)}</td>
            <td className={cn("py-1.5 text-right font-medium", imp === true ? "text-positive" : imp === false ? "text-negative" : "text-muted-foreground")}>{f.diff(m.delta)}</td>
          </tr>
        );
      })}
    </>
  );
}
