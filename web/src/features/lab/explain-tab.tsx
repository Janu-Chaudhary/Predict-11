"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { PlayerAvatar } from "@/components/player/player-avatar";
import { RoleChip } from "@/components/player/role-chip";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

import { DependenceChart, HBars, Waterfall } from "./charts";
import { fmtNum, fmtValue } from "./format";
import { importanceInsight } from "./insights";
import { MatchPicker, matchLabel } from "./match-picker";
import { useExplain, useMatch } from "./queries";
import type { Contribution, ShapExample, Telemetry } from "./types";
import { Grid, LabCard, SectionTitle, Segmented, Term, labHref, useLabState } from "./ui";

const KIND_LABEL: Record<string, string> = { over: "Over-predicted", under: "Under-predicted", accurate: "Accurate" };

/** Telemetry examples carry only the top contributions: fold the remainder into one row. */
export function withRemainder(ex: ShapExample): Contribution[] {
  const sum = ex.contribs.reduce((s, c) => s + c.shap, 0);
  if (ex.pred === null || ex.base === null) return ex.contribs;
  const rest = ex.pred - ex.base - sum;
  return Math.abs(rest) > 0.05 ? [...ex.contribs, { feature: "all other features", value: null, shap: rest }] : ex.contribs;
}

export function dependenceInsight(points: { x: number | null; shap: number }[], feature: string): string {
  const pts = points.filter((p) => p.x !== null) as { x: number; shap: number }[];
  if (pts.length < 5) return "Too few points to describe the shape.";
  const sorted = [...pts].sort((a, b) => a.x - b.x);
  const third = Math.max(1, Math.floor(sorted.length / 3));
  const low = sorted.slice(0, third).reduce((s, p) => s + p.shap, 0) / third;
  const high = sorted.slice(-third).reduce((s, p) => s + p.shap, 0) / third;
  const dir = high - low;
  return `Rows in the lowest third of ${feature} get ${fmtNum(low, 1)} pts on average from it; the highest third ${fmtNum(high, 1)} pts. ${
    Math.abs(dir) < 0.5 ? "A weak effect overall." : dir > 0 ? "Higher values push predictions up." : "Higher values push predictions down."
  }`;
}

export function ExplainTab({ t, version }: { t: Telemetry; version: string }) {
  const shap = t.shap;
  const hasShap = t.features.some((f) => f.shap !== null);
  const depFeatures = Object.keys(shap?.dependence ?? {});
  const [dep, setDep] = useState(depFeatures[0] ?? "");
  const depF = depFeatures.includes(dep) ? dep : depFeatures[0];
  const examples = shap?.examples ?? [];
  const [exI, setExI] = useState("0");
  const ex = examples[Number(exI)] ?? examples[0];

  const global = useMemo(
    () =>
      [...t.features]
        .sort((a, b) => ((hasShap ? b.shap : b.gain) ?? 0) - ((hasShap ? a.shap : a.gain) ?? 0))
        .slice(0, 20)
        .map((f) => ({ key: f.name, label: <span className="font-mono text-xs">{f.name}</span>, value: (hasShap ? f.shap : f.gain) ?? 0, title: f.description })),
    [t.features, hasShap],
  );

  return (
    <div className="space-y-6">
      <SectionTitle sub="Which inputs move the predictions, globally and for one player in one match.">Explainability with SHAP</SectionTitle>
      <Grid cols={2}>
        <LabCard
          title={hasShap ? "Global importance: mean |SHAP| (points)" : "Global importance (gain)"}
          caption="Average absolute push each feature gives a prediction, across the test rows. Click a bar to see its dependence plot."
          table={{ columns: ["Feature", hasShap ? "Mean |SHAP|" : "Gain"], rows: global.map((g) => [g.key, fmtNum(g.value, 3)]) }}
          learn={{
            concept: (
              <>
                <Term id="shap">SHAP</Term> splits each prediction into additive pieces, one per feature: prediction = <Term id="base-value">base value</Term> + Σ contributions. Averaging the absolute
                pieces over many rows gives a global importance measured in points, unlike gain.
              </>
            ),
            formula: "importanceⱼ = mean over rows of |φⱼ|",
            read: "Longer bar = the feature moves predictions more, in either direction. Direction is in the dependence plot.",
            good: "Top features that make cricket sense; no single feature dwarfing everything (that can hint at leakage).",
            ours: importanceInsight(t.features, hasShap ? "shap" : "gain"),
          }}
        >
          <HBars items={global} fmt={(n) => fmtNum(n, hasShap ? 2 : 0)} onSelect={(k) => depFeatures.includes(k) && setDep(k)} selected={depF} />
        </LabCard>

        {depF && shap ? (
          <LabCard
            title="Dependence plot"
            caption="One dot per test row: the feature's value (x) against how much it moved that prediction (y)."
            actions={
              <Select value={depF} onValueChange={(v) => v && setDep(v)}>
                <SelectTrigger aria-label="Feature" className="h-7 min-w-40 rounded-lg bg-card text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {depFeatures.map((f) => (
                    <SelectItem key={f} value={f} className="font-mono text-xs">
                      {f}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            }
            learn={{
              concept: (
                <>
                  A <Term id="dependence-plot">dependence plot</Term> reveals the shape of a feature&apos;s effect, which importance bars hide: linear, saturating, threshold-like, or
                  interaction-driven.
                </>
              ),
              read: "Violet dots pushed the prediction up, red down. Vertical spread at the same x = interactions with other features. Rows where the feature is missing are not shown.",
              good: "Smooth, monotone shapes for form-type features (more recent points → higher prediction).",
              ours: dependenceInsight(shap.dependence[depF] ?? [], depF),
            }}
          >
            <DependenceChart points={shap.dependence[depF] ?? []} feature={depF} />
          </LabCard>
        ) : (
          <p className="text-sm text-muted-foreground">No dependence data recorded for this run.</p>
        )}
      </Grid>

      {ex && (
        <LabCard
          title="Worked examples"
          caption="Three test rows chosen by the training run: the biggest over-prediction, the biggest under-prediction and the most accurate."
          actions={
            <Segmented
              size="sm"
              label="Example"
              value={String(examples.indexOf(ex))}
              onChange={setExI}
              options={examples.map((e, i) => ({ key: String(i), label: KIND_LABEL[e.kind ?? ""] ?? `Example ${i + 1}` }))}
            />
          }
          learn={{
            concept: "A waterfall starts at the base value (the average prediction) and adds each feature's SHAP value until it reaches this row's prediction.",
            read: "Violet bars push up, red bars push down; the biggest pushes are at the top. Compare the final prediction with the actual score.",
            good: "For accurate rows the story makes sense; for big misses, look for what the model could not know (e.g. an unexpected batting promotion).",
            ours: `${ex.playerName}${ex.team ? ` (${ex.team})` : ""}: predicted ${fmtNum(ex.pred, 1)}, actually scored ${fmtNum(ex.actual, 0)}. Biggest push: ${ex.contribs[0]?.feature ?? "?"} = ${fmtValue(ex.contribs[0]?.value)} (${fmtNum(ex.contribs[0]?.shap, 1)} pts).`,
          }}
        >
          <div className="mb-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
            <span>
              <span className="text-muted-foreground">Player </span>
              <span className="font-medium">{ex.playerName}</span>
            </span>
            <span className="num">
              <span className="text-muted-foreground">Predicted </span>
              {fmtNum(ex.pred, 1)}
            </span>
            <span className="num">
              <span className="text-muted-foreground">Actual </span>
              <span className="font-semibold">{fmtNum(ex.actual, 0)}</span>
            </span>
          </div>
          <Waterfall base={ex.base ?? shap?.baseValue ?? 0} contribs={withRemainder(ex)} top={15} />
        </LabCard>
      )}

      <SectionTitle sub="Pick any evaluated match, then a player, to see why the model predicted what it did.">Explain a prediction</SectionTitle>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[20rem_minmax(0,1fr)] xl:grid-cols-[22rem_16rem_minmax(0,1fr)]">
        <MatchPicker version={version} />
        <PlayerPicker version={version} />
        <ExplainPanel version={version} />
      </div>
    </div>
  );
}

function PlayerPicker({ version }: { version: string }) {
  const state = useLabState();
  const router = useRouter();
  const matchQ = useMatch(version, state.match);
  const d = matchQ.data;
  return (
    <section className="min-w-0 rounded-xl border border-border bg-card p-3 shadow-e1 lg:col-span-1" aria-label="Pick a player">
      <h3 className="text-overline mb-2 text-muted-foreground">Player {d ? <span className="normal-case">· {matchLabel(d.info)}</span> : null}</h3>
      {state.match === null && <p className="text-sm text-muted-foreground">Pick a match first.</p>}
      {state.match !== null && matchQ.isPending && <Skeleton className="h-64 rounded-lg" />}
      {matchQ.isError && <p className="text-sm text-muted-foreground">{(matchQ.error as Error).message}</p>}
      {d && (
        <ul className="max-h-64 overflow-y-auto overscroll-contain lg:max-h-[34rem]">
          {d.players.map((p) => (
            <li key={p.playerId}>
              <button
                type="button"
                onClick={() => router.replace(labHref(state, { player: p.playerId }), { scroll: false })}
                aria-pressed={state.player === p.playerId}
                className={cn(
                  "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring",
                  state.player === p.playerId && "bg-brand/12 ring-1 ring-brand/40",
                )}
              >
                <PlayerAvatar name={p.name} src={p.imageUrl} team={p.team} size="xs" />
                <span className="min-w-0 flex-1 truncate text-sm">{p.name}</span>
                <span className="num text-xs text-muted-foreground">{fmtNum(p.predMean, 0)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ExplainPanel({ version }: { version: string }) {
  const state = useLabState();
  const q = useExplain(version, state.match, state.player);
  const e = q.data;
  return (
    <section className="min-w-0 rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4 lg:col-span-2 xl:col-span-1" aria-label="Explanation">
      <h3 className="text-overline mb-2 text-muted-foreground">Why this prediction</h3>
      {!state.player && <p className="text-sm text-muted-foreground">Pick a match and a player to see the SHAP waterfall for that prediction.</p>}
      {state.player && q.isPending && <Skeleton className="h-80 rounded-lg" />}
      {q.isError && <p className="text-sm text-muted-foreground">Couldn&apos;t explain this prediction: {(q.error as Error).message}</p>}
      {e && (
        <div className={cn(q.isPlaceholderData && "opacity-60")}>
          <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-2">
            <span className="text-base font-semibold">{e.name}</span>
            {e.role && ["WK", "BAT", "AR", "BOWL"].includes(e.role) && <RoleChip role={e.role as "WK"} />}
            <span className="num text-sm">
              <span className="text-muted-foreground">Base </span>
              {fmtNum(e.baseValue, 1)}
            </span>
            <span className="num text-sm">
              <span className="text-muted-foreground">Prediction </span>
              <span className="font-semibold">{fmtNum(e.prediction, 1)}</span>
            </span>
            {e.predOutOfSample !== null && (
              <span className="num text-sm" title="The out-of-sample prediction stored for this evaluation">
                <span className="text-muted-foreground">Out-of-sample </span>
                {fmtNum(e.predOutOfSample, 1)}
              </span>
            )}
            <span className="num text-sm">
              <span className="text-muted-foreground">Actual </span>
              <span className="font-semibold">{fmtNum(e.actual, 0)}</span>
            </span>
          </div>
          <Waterfall base={e.baseValue} contribs={e.contributions} top={14} />
          <details className="mt-3 text-xs text-muted-foreground">
            <summary className="cursor-pointer select-none hover:text-foreground">All {e.contributions.length} features</summary>
            <div className="mt-2 max-h-72 overflow-auto rounded-lg border border-border">
              <table className="num w-full text-xs">
                <thead>
                  <tr className="bg-surface-2">
                    <th className="text-overline px-2 py-1.5 text-left">Feature</th>
                    <th className="text-overline px-2 py-1.5 text-right">Value</th>
                    <th className="text-overline px-2 py-1.5 text-right">SHAP</th>
                  </tr>
                </thead>
                <tbody>
                  {e.contributions.map((c) => (
                    <tr key={c.feature} className="border-t border-border" title={c.description ?? undefined}>
                      <td className="px-2 py-1 font-mono text-foreground">{c.feature}</td>
                      <td className="px-2 py-1 text-right">{fmtValue(c.value)}</td>
                      <td className={cn("px-2 py-1 text-right font-medium", c.shap < 0 ? "text-negative" : "text-foreground")}>{fmtNum(c.shap, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <p className="mt-3 text-xs text-muted-foreground">{e.note}</p>
        </div>
      )}
    </section>
  );
}
