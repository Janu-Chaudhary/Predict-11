"use client";

import { BookOpen, ChevronDown } from "lucide-react";
import Link from "next/link";
import { createContext, useContext, type ReactNode } from "react";

import { ChartFrame, type TableView } from "@/components/charts/chart-frame";
import { cn } from "@/lib/utils";

import { METRICS, verdict, type MetricKey } from "./format";
import { GLOSSARY_BY_ID } from "./glossary";
import type { Pair } from "./types";
import { labHref, type LabState } from "./ui-state";

// ------------------------------------------------------------------ URL state
export { LAB_TABS, labHref, type LabState, type LabTab } from "./ui-state";

const LabContext = createContext<LabState | null>(null);
export const LabProvider = LabContext.Provider;
export function useLabState(): LabState {
  const s = useContext(LabContext);
  if (!s) throw new Error("useLabState outside <LabProvider>");
  return s;
}

/** Inline link to a glossary entry (dotted underline, keeps the selected run). */
export function Term({ id, children }: { id: string; children?: ReactNode }) {
  const state = useContext(LabContext);
  const entry = GLOSSARY_BY_ID[id];
  const base = state ? labHref(state, { tab: "glossary", match: null, player: null }) : "/lab?tab=glossary";
  return (
    <Link
      href={`${base}#term-${id}`}
      title={entry?.short}
      className="underline decoration-brand/60 decoration-dotted underline-offset-[3px] hover:text-brand hover:decoration-solid"
    >
      {children ?? entry?.term ?? id}
    </Link>
  );
}

// ------------------------------------------------------------------ teaching card
export type Learn = {
  /** The concept in plain words. */
  concept: ReactNode;
  formula?: string;
  read: ReactNode;
  good: ReactNode;
  /** Computed from this run's numbers. */
  ours?: ReactNode;
};

export function LearnMore({ learn, className }: { learn: Learn; className?: string }) {
  return (
    <details className={cn("group mt-3 rounded-lg border border-border bg-surface-2/50 open:bg-surface-2/70", className)}>
      <summary className="flex h-9 cursor-pointer list-none items-center gap-1.5 rounded-lg px-3 text-xs font-medium text-muted-foreground outline-none select-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
        <BookOpen aria-hidden className="size-3.5" />
        Learn more
        <ChevronDown aria-hidden className="ml-auto size-4 transition-transform group-open:rotate-180" />
      </summary>
      <div className="grid gap-3 px-3 pt-1 pb-3 text-sm leading-relaxed md:grid-cols-2">
        <LearnBlock title="The idea">{learn.concept}</LearnBlock>
        <LearnBlock title="How to read it">{learn.read}</LearnBlock>
        {learn.formula && (
          <LearnBlock title="Formula" className="md:col-span-2">
            <code className="block overflow-x-auto rounded-md bg-card px-3 py-2 font-mono text-[13px] whitespace-pre text-foreground">{learn.formula}</code>
          </LearnBlock>
        )}
        <LearnBlock title="What good looks like">{learn.good}</LearnBlock>
        {learn.ours && (
          <LearnBlock title="What our run says" className="rounded-md border-l-2 border-brand bg-card px-3 py-2">
            {learn.ours}
          </LearnBlock>
        )}
      </div>
    </details>
  );
}

function LearnBlock({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("min-w-0", className)}>
      <h4 className="text-overline mb-1 text-muted-foreground">{title}</h4>
      <div className="text-foreground/90">{children}</div>
    </div>
  );
}

/**
 * Every Lab chart/table sits in the app's ChartFrame (same card, title, Chart⇄Table toggle), with a
 * one-line "what am I looking at" caption above and an expandable Learn-more panel below.
 */
export function LabCard({
  title,
  caption,
  learn,
  table,
  legend,
  actions,
  children,
  className,
}: {
  title: ReactNode;
  caption: string;
  learn?: Learn;
  table?: TableView;
  legend?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <ChartFrame title={title} summary={caption} table={table} legend={legend} actions={actions} className={cn("flex flex-col", className)}>
      <p className="mb-3 text-sm text-muted-foreground">{caption}</p>
      {children}
      {learn && <LearnMore learn={learn} />}
    </ChartFrame>
  );
}

/** Plain prose card (same frame, no chart). */
export function ProseCard({ title, children, className }: { title: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("w-full min-w-0 rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4", className)}>
      <h3 className="text-overline mb-2 text-muted-foreground">{title}</h3>
      <div className="space-y-2 text-sm leading-relaxed text-foreground/90">{children}</div>
    </section>
  );
}

// ------------------------------------------------------------------ controls
/** Segmented control (single choice): same look as the fantasy pages. */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
  className,
  size = "md",
}: {
  label: string;
  options: { key: T; label: ReactNode; title?: string }[];
  value: T;
  onChange: (v: T) => void;
  className?: string;
  size?: "sm" | "md";
}) {
  return (
    <div role="group" aria-label={label} className={cn("no-scrollbar inline-flex max-w-full overflow-x-auto rounded-[10px] bg-surface-2 p-0.5", className)}>
      {options.map((o) => (
        <button
          key={o.key}
          type="button"
          title={o.title}
          aria-pressed={value === o.key}
          onClick={() => onChange(o.key)}
          className={cn(
            "inline-flex shrink-0 items-center rounded-lg font-medium whitespace-nowrap text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
            size === "sm" ? "h-7 px-2 text-xs" : "h-9 px-3 text-sm",
            value === o.key && "bg-card text-foreground shadow-e1",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Toggle chips (multi or single select). */
export function Chip({ active, onClick, children, title }: { active: boolean; onClick: () => void; children: ReactNode; title?: string }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      title={title}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 shrink-0 items-center gap-1 rounded-full border px-3 text-xs font-medium whitespace-nowrap outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active ? "border-brand/50 bg-brand/12 text-foreground" : "border-border text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

// ------------------------------------------------------------------ metric tile
const VERDICT_TEXT = { better: "Model better", worse: "Baseline better", tie: "Too close to call", unknown: "" } as const;

/**
 * StatTile look (same card, overline, condensed number) for a model-vs-baseline metric: the
 * model's value, the baseline's, the difference and a mini CI bar around zero.
 */
export function MetricTile({ metric, pair, className }: { metric: MetricKey; pair: Pair; className?: string }) {
  const m = METRICS[metric];
  const v = verdict(pair, m.higherIsBetter);
  return (
    <div className={cn("min-w-0 rounded-xl border border-border bg-card p-4 shadow-e1 lg:p-5", className)}>
      <div className="text-overline truncate text-muted-foreground">
        <Term id={m.term}>{m.label}</Term>
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="font-condensed num text-[2rem] leading-9 font-bold lg:text-[2.5rem] lg:leading-[2.75rem]">{m.fmt(pair.model)}</span>
        <span className="num text-xs text-muted-foreground">vs {m.fmt(pair.baseline)} baseline</span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs">
        <span className={cn("num font-medium", v === "better" ? "text-positive" : v === "worse" ? "text-negative" : "text-muted-foreground")}>
          <span aria-hidden>{v === "better" ? "▲ " : v === "worse" ? "▼ " : "• "}</span>
          {m.diffFmt(pair.diff)}
        </span>
        <span className="text-muted-foreground">{VERDICT_TEXT[v]}</span>
      </div>
      <CiBar pair={pair} higherIsBetter={m.higherIsBetter} fmt={m.diffFmt} className="mt-3" />
    </div>
  );
}

/** Difference ± 95% CI on a symmetric axis around zero (the "no difference" line). */
export function CiBar({ pair, higherIsBetter, fmt, className }: { pair: Pair; higherIsBetter: boolean; fmt: (n: number | null) => string; className?: string }) {
  const [lo, hi] = pair.ci;
  if (pair.diff === null || lo === null || hi === null) return null;
  const span = Math.max(Math.abs(lo), Math.abs(hi), Math.abs(pair.diff)) * 1.15 || 1;
  const x = (n: number) => 50 + (n / span) * 50;
  const v = verdict(pair, higherIsBetter);
  const color = v === "better" ? "bg-positive" : v === "worse" ? "bg-negative" : "bg-muted-foreground";
  return (
    <div className={className}>
      <div
        role="img"
        aria-label={`Difference ${fmt(pair.diff)}, 95% interval ${fmt(lo)} to ${fmt(hi)}`}
        className="relative h-4"
      >
        <div className="absolute inset-x-0 top-1/2 h-px bg-border" />
        <div className="absolute top-0 bottom-0 left-1/2 w-px bg-foreground/40" />
        <div className={cn("absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full opacity-40", color)} style={{ left: `${x(lo)}%`, width: `${Math.max(0.5, x(hi) - x(lo))}%` }} />
        <div className={cn("absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card", color)} style={{ left: `${x(pair.diff)}%` }} />
      </div>
      <div className="num mt-0.5 flex justify-between text-[11px] text-faint">
        <span>{fmt(lo)}</span>
        <span>95% CI · 0 = no difference</span>
        <span>{fmt(hi)}</span>
      </div>
    </div>
  );
}

/** Small "key: value" definition list used in side panels. */
export function KeyValues({ items, className }: { items: { k: ReactNode; v: ReactNode }[]; className?: string }) {
  return (
    <dl className={cn("grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm", className)}>
      {items.map((it, i) => (
        <div key={i} className="contents">
          <dt className="text-muted-foreground">{it.k}</dt>
          <dd className="num text-right font-medium">{it.v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Responsive grid shortcut: 1 column on phones, 2 on md, `cols` on xl. */
export function Grid({ cols = 2, children, className }: { cols?: 2 | 3 | 4; children: ReactNode; className?: string }) {
  const xl = cols === 4 ? "xl:grid-cols-4" : cols === 3 ? "xl:grid-cols-3" : "xl:grid-cols-2";
  return <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-2", xl, className)}>{children}</div>;
}

export function SectionTitle({ children, id, sub }: { children: ReactNode; id?: string; sub?: ReactNode }) {
  return (
    <div className="mt-8 mb-3 first:mt-0">
      <h2 id={id} className="text-title text-foreground">
        {children}
      </h2>
      {sub && <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{sub}</p>}
    </div>
  );
}
