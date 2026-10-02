"use client";

import { ArrowDown, ArrowRight, Database, ListChecks, Shirt, Sigma, TreePine } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { fmtCompact, fmtInt } from "./format";
import type { Protocol, Telemetry } from "./types";
import { labHref, useLabState, type LabTab } from "./ui";

// ------------------------------------------------------------------ pipeline
type Step = { tab: LabTab; icon: typeof Database; title: string; body: ReactNode; stat?: string };

export function PipelineDiagram({ t }: { t: Telemetry | null }) {
  const state = useLabState();
  const heads = t?.protocol.heads.length ? t.protocol.heads : ["mean", "q10", "q50", "q90"];
  const groups = t ? new Set(t.features.map((f) => f.group)).size : null;
  const steps: Step[] = [
    {
      tab: "data",
      icon: Database,
      title: "Data",
      body: "Every IPL player-match since 2008 with its Dream11 points (the target).",
      stat: t?.data.rows ? `${fmtCompact(t.data.rows)} rows · ${fmtInt(t.data.matches)} matches` : undefined,
    },
    {
      tab: "features",
      icon: ListChecks,
      title: "Features",
      body: "Point-in-time numbers known at the toss: form, craft, matchups, venue, conditions.",
      stat: t?.features.length ? `${t.features.length} features · ${groups} groups` : undefined,
    },
    {
      tab: "training",
      icon: TreePine,
      title: `${heads.length} model heads`,
      body: (
        <span className="mt-1 flex flex-wrap gap-1">
          {heads.map((h) => (
            <span key={h} className="rounded-md bg-surface-3 px-1.5 py-0.5 font-mono text-[11px]">
              {h}
            </span>
          ))}
        </span>
      ),
      stat: t?.trees ? `${fmtInt(Object.values(t.trees).reduce((s, n) => s + n, 0))} trees` : undefined,
    },
    {
      tab: "predictions",
      icon: Shirt,
      title: "Optimiser",
      body: "Exact solver picks the best Dream11 XI + captain / vice-captain on the predictions.",
      stat: "11 players · C ×2 · VC ×1.5",
    },
    {
      tab: "evaluation",
      icon: Sigma,
      title: "Evaluation",
      body: "Scored with actual points, against the last-5-form baseline, with bootstrap CIs.",
      stat: t ? `${t.evaluations.length} evaluation sets` : undefined,
    },
  ];
  return (
    <ol className="flex flex-col items-stretch gap-1 lg:flex-row" aria-label="Model pipeline">
      {steps.map((s, i) => (
        <li key={s.title} className="flex flex-col items-center gap-1 lg:min-w-0 lg:flex-1 lg:flex-row lg:items-stretch">
          <Link
            href={labHref(state, { tab: s.tab, match: null, player: null })}
            scroll={false}
            className="group block w-full min-w-0 rounded-xl border lg:h-full border-border bg-surface-2/60 p-3 outline-none hover:border-brand/50 hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className="flex items-center gap-2">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-brand/15 text-brand">
                <s.icon aria-hidden className="size-4" />
              </span>
              <span className="text-overline text-muted-foreground">Step {i + 1}</span>
            </div>
            <div className="mt-2 text-sm font-semibold">{s.title}</div>
            <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{s.body}</div>
            {s.stat && <div className="num mt-2 text-xs font-medium text-foreground">{s.stat}</div>}
          </Link>
          {i < steps.length - 1 && (
            <>
              <ArrowDown aria-hidden className="size-4 shrink-0 text-faint lg:hidden" />
              <ArrowRight aria-hidden className="hidden size-4 shrink-0 self-center text-faint lg:block" />
            </>
          )}
        </li>
      ))}
    </ol>
  );
}

// ------------------------------------------------------------------ season split strip
export type SeasonRole = "train" | "inner" | "validate" | "test" | "walkforward" | "unused";

export const ROLE_STYLE: Record<SeasonRole, { label: string; cls: string }> = {
  train: { label: "Train", cls: "bg-brand/45" },
  inner: { label: "Inner validation (early stopping)", cls: "bg-[repeating-linear-gradient(135deg,var(--chart-1)_0_3px,transparent_3px_6px)] bg-brand/15" },
  validate: { label: "Validate (CV fold)", cls: "bg-[var(--chart-2)]" },
  test: { label: "Test (scored once)", cls: "bg-[var(--chart-4)]" },
  walkforward: { label: "Walk-forward", cls: "bg-[var(--chart-3)]" },
  unused: { label: "Not used", cls: "bg-surface-3/60" },
};

/** Role of `season` when the scored season is `target` (rolling origin with inner validation). */
export function roleFor(season: number, target: number, kind: "validate" | "test" | "walkforward"): SeasonRole {
  if (season === target) return kind;
  if (season > target) return "unused";
  if (season === target - 1) return "inner";
  return "train";
}

export function seasonsOf(p: Protocol, years: number[]): number[] {
  const first = Math.min(2008, ...years);
  const last = Math.max(p.wfSeason ?? 2026, p.testSeason ?? 2025, ...years);
  return Array.from({ length: last - first + 1 }, (_, i) => first + i);
}

export function SplitStrip({ protocol, years }: { protocol: Protocol; years: number[] }) {
  const seasons = seasonsOf(protocol, years);
  const rows: { label: string; target: number; kind: "validate" | "test" | "walkforward" }[] = [
    ...protocol.cvSeasons.map((y) => ({ label: `CV fold ${y}`, target: y, kind: "validate" as const })),
    ...(protocol.testSeason ? [{ label: `Test ${protocol.testSeason}`, target: protocol.testSeason, kind: "test" as const }] : []),
    ...(protocol.wfSeason ? [{ label: `Walk-forward ${protocol.wfSeason}`, target: protocol.wfSeason, kind: "walkforward" as const }] : []),
  ];
  const cols = `minmax(6.5rem,8rem) repeat(${seasons.length}, minmax(0,1fr))`;
  return (
    <div>
      <div className="overflow-x-auto">
        <div className="min-w-[640px]">
          <div className="grid gap-[3px]" style={{ gridTemplateColumns: cols }}>
            <span />
            {seasons.map((y) => (
              <span key={y} className="num text-center text-[10px] text-faint">
                {String(y).slice(2)}
              </span>
            ))}
          </div>
          {rows.map((r) => (
            <div key={r.label} className="mt-[3px] grid items-center gap-[3px]" style={{ gridTemplateColumns: cols }}>
              <span className="truncate pr-2 text-xs font-medium">{r.label}</span>
              {seasons.map((y) => {
                const role = roleFor(y, r.target, r.kind);
                return <span key={y} title={`${y}: ${ROLE_STYLE[role].label}`} className={cn("h-5 rounded-[3px]", ROLE_STYLE[role].cls)} />;
              })}
            </div>
          ))}
        </div>
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {(["train", "inner", "validate", "test", "walkforward", "unused"] as const).map((k) => (
          <li key={k} className="inline-flex items-center gap-1.5">
            <span className={cn("h-3 w-5 rounded-[3px]", ROLE_STYLE[k].cls)} />
            {ROLE_STYLE[k].label}
          </li>
        ))}
      </ul>
    </div>
  );
}
