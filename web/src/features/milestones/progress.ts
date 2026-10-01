import type { Milestone } from "./types";

/**
 * Milestone ladders, mirroring the backend's `MILESTONE_RULES` (players_records.py): the step
 * between round numbers, which grows once a career passes `bigFrom`.
 */
const STEPS: Record<string, { small: number; big: number; bigFrom: number }> = {
  runs: { small: 500, big: 1000, bigFrom: 1000 },
  wickets: { small: 50, big: 50, bigFrom: 0 },
  sixes: { small: 50, big: 100, bigFrom: 100 },
  matches: { small: 50, big: 100, bigFrom: 100 },
  catches: { small: 50, big: 50, bigFrom: 0 },
};

export const STAT_LABEL: Record<string, { title: string; unit: string; singular: string }> = {
  runs: { title: "Runs", unit: "runs", singular: "run" },
  wickets: { title: "Wickets", unit: "wickets", singular: "wicket" },
  sixes: { title: "Sixes", unit: "sixes", singular: "six" },
  catches: { title: "Catches", unit: "catches", singular: "catch" },
  matches: { title: "Matches", unit: "matches", singular: "match" },
};

export const STAT_ORDER = ["runs", "wickets", "sixes", "catches", "matches"];

export type MilestoneProgress = {
  /** The previous round number (start of the bar). */
  from: number;
  to: number;
  current: number;
  /** 0–1 share of the way from `from` to `to`, clamped. */
  ratio: number;
  /** Whole-number percentage for display. */
  pct: number;
};

/** The step that applies at a given career value (falls back to the gap to the target). */
export function stepFor(stat: string, current: number, target: number): number {
  const rule = STEPS[stat];
  if (!rule) return target; // unknown stat: measure from zero
  return current < rule.bigFrom ? rule.small : rule.big;
}

/**
 * Progress from the previous milestone to the next one, e.g. 2,955 runs toward 3,000 →
 * from 2,000, ratio 0.955. Bars from 0 would sit at ~99% for every card and say nothing.
 */
export function milestoneProgress(m: Pick<Milestone, "stat" | "current" | "target">): MilestoneProgress {
  const to = m.target;
  const from = Math.max(0, to - stepFor(m.stat, m.current, m.target));
  const span = to - from;
  const raw = span > 0 ? (m.current - from) / span : 1;
  const ratio = Math.min(1, Math.max(0, raw));
  // Never show 100% for a milestone that hasn't been reached yet.
  const pct = m.current < to ? Math.min(99, Math.floor(ratio * 100)) : 100;
  return { from, to, current: m.current, ratio, pct };
}

/** Group by stat in a fixed order (unknown stats appended), closest first within a group. */
export function groupMilestones(list: Milestone[]): { stat: string; items: Milestone[] }[] {
  const groups = new Map<string, Milestone[]>();
  for (const m of list) groups.set(m.stat, [...(groups.get(m.stat) ?? []), m]);
  const order = [...STAT_ORDER.filter((s) => groups.has(s)), ...[...groups.keys()].filter((s) => !STAT_ORDER.includes(s))];
  return order.map((stat) => ({
    stat,
    items: [...groups.get(stat)!].sort((a, b) => a.needed - b.needed || b.target - a.target || a.player.name.localeCompare(b.player.name)),
  }));
}

export function neededText(m: Pick<Milestone, "stat" | "needed">): string {
  const l = STAT_LABEL[m.stat];
  const unit = l ? (m.needed === 1 ? l.singular : l.unit) : m.stat;
  return `${m.needed.toLocaleString("en-IN")} ${unit} to go`;
}
