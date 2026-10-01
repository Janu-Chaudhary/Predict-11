/** Pure helpers for the fantasy screens: sorting, filters, URL state and number formatting. */
import { ROLES, type Role } from "@/lib/tokens";

import { fmt } from "../players/format";
import type { CategoryMix, Distribution, LeaderRow, LeaderSort, RoleFilter, XiPick } from "./types";

export const SORTS: { key: LeaderSort; label: string; short: string; hint: string }[] = [
  { key: "total", label: "Total points", short: "Total", hint: "Season total" },
  { key: "mean", label: "Mean per match", short: "Mean", hint: "Average points per match" },
  { key: "consistency", label: "Consistency", short: "Steady", hint: "100 × (1 − SD ÷ mean): higher is steadier" },
  { key: "ppc", label: "Points per credit", short: "Pts/cr", hint: "Mean points per Dream11 credit" },
];

export const ROLE_FILTERS: RoleFilter[] = ["ALL", ...ROLES];
export const MIN_MATCHES = [1, 3, 5, 8, 10] as const;
export const DEFAULT_MIN_MATCHES = 5;

const SORT_VALUE: Record<LeaderSort, (r: LeaderRow) => number | null> = {
  total: (r) => r.total,
  mean: (r) => r.mean,
  consistency: (r) => r.consistency,
  ppc: (r) => r.ppc,
};

/**
 * Highest first; rows without the metric (e.g. no credits) sink to the bottom. Ties break on
 * total points, then name, so the order is stable between renders.
 */
export function sortLeaderboard(rows: LeaderRow[], sort: LeaderSort): LeaderRow[] {
  const get = SORT_VALUE[sort];
  return [...rows].sort((a, b) => {
    const va = get(a);
    const vb = get(b);
    if (va === null && vb === null) return b.total - a.total || a.player.name.localeCompare(b.player.name);
    if (va === null) return 1;
    if (vb === null) return -1;
    return vb - va || b.total - a.total || a.player.name.localeCompare(b.player.name);
  });
}

/** Client-side guard so the role chip and min-matches control also work on a cached/sample payload. */
export function filterLeaderboard(rows: LeaderRow[], role: RoleFilter, minMatches: number): LeaderRow[] {
  return rows.filter((r) => (role === "ALL" || r.role === role) && r.matches >= minMatches);
}

export function sortValueLabel(r: LeaderRow, sort: LeaderSort): string {
  switch (sort) {
    case "total":
      return fmt(r.total);
    case "mean":
      return fmt(r.mean, 1);
    case "consistency":
      return fmt(r.consistency, 0);
    case "ppc":
      return fmt(r.ppc, 2);
  }
}

/* ---------- URL state ---------- */

export function parseSort(v: string | undefined): LeaderSort {
  return SORTS.some((s) => s.key === v) ? (v as LeaderSort) : "total";
}

export function parseRole(v: string | undefined): RoleFilter {
  const up = v?.toUpperCase();
  return up && (ROLES as readonly string[]).includes(up) ? (up as Role) : "ALL";
}

export function parseMinMatches(v: string | undefined): number {
  const n = Number(v);
  return v && Number.isInteger(n) && n >= 1 && n <= 30 ? n : DEFAULT_MIN_MATCHES;
}

export type LeaderState = { season: number; sort: LeaderSort; role: RoleFilter; min: number };

export function leaderHref(s: LeaderState, current: number): string {
  const sp = new URLSearchParams();
  if (s.season !== current) sp.set("season", String(s.season));
  if (s.sort !== "total") sp.set("sort", s.sort);
  if (s.role !== "ALL") sp.set("role", s.role);
  if (s.min !== DEFAULT_MIN_MATCHES) sp.set("min", String(s.min));
  return `/fantasy${sp.size ? `?${sp}` : ""}`;
}

/* ---------- Distribution formatting ---------- */

/** Points: whole numbers stay whole, otherwise one decimal. */
export function fmtPts(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "–";
  return Number.isInteger(v) ? fmt(v) : fmt(v, 1);
}

/** "12–107–203" floor–median–ceiling, or null when the range is incomplete. */
export function rangeText(d: Pick<Distribution, "p10" | "median" | "p90">): string | null {
  if (d.p10 === null || d.median === null || d.p90 === null) return null;
  return `${fmtPts(d.p10)}–${fmtPts(d.median)}–${fmtPts(d.p90)}`;
}

/** Spoken summary for range bars and rows. */
export function describeDistribution(d: Distribution): string {
  const parts = [`${d.matches} matches`, `mean ${fmtPts(d.mean)}`];
  const r = rangeText(d);
  if (r) parts.push(`floor ${fmtPts(d.p10)}, median ${fmtPts(d.median)}, ceiling ${fmtPts(d.p90)}`);
  if (d.consistency !== null) parts.push(`consistency ${fmt(d.consistency, 0)} of 100`);
  return parts.join(", ");
}

/** A shared track for a list of range bars: 0 → the largest p90 rounded up to 20. */
export function rangeScale(rows: Pick<Distribution, "p90">[], minMax = 120): number {
  const top = Math.max(minMax, ...rows.map((r) => r.p90 ?? 0));
  return Math.ceil(top / 20) * 20;
}

/** Consistency label in words so the number isn't the only cue. */
export function consistencyWord(c: number | null): string {
  if (c === null) return "–";
  if (c >= 50) return "Steady";
  if (c >= 25) return "Mixed";
  return "Volatile";
}

export const CATEGORY_META: { key: keyof CategoryMix; label: string; cls: string }[] = [
  { key: "batting", label: "Batting", cls: "bg-brand" },
  { key: "bowling", label: "Bowling", cls: "bg-primary" },
  { key: "fielding", label: "Fielding", cls: "bg-info" },
  { key: "bonuses", label: "Bonuses", cls: "bg-positive" },
  { key: "lineup", label: "Lineup", cls: "bg-faint" },
];

/** Category shares in %, negatives (ducks) clipped to 0, summing to 100 (or [] when empty). */
export function categoryShares(mix: CategoryMix | null): { key: keyof CategoryMix; label: string; cls: string; value: number; pct: number }[] {
  if (!mix) return [];
  const pos = CATEGORY_META.map((c) => ({ ...c, value: mix[c.key], clipped: Math.max(0, mix[c.key]) }));
  const sum = pos.reduce((s, c) => s + c.clipped, 0);
  if (sum <= 0) return [];
  return pos.filter((c) => c.clipped > 0).map(({ clipped, ...c }) => ({ ...c, pct: (clipped / sum) * 100 }));
}

/* ---------- XI helpers ---------- */

export const xiTotal = (xi: XiPick[]) => xi.reduce((s, p) => s + p.effective, 0);

export function multiplierLabel(p: XiPick): string | null {
  return p.captain ? "×2" : p.vice_captain ? "×1.5" : null;
}

/** Role order for lists (WK, BAT, AR, BOWL), then points. */
export function sortXi(xi: XiPick[]): XiPick[] {
  return [...xi].sort((a, b) => ROLES.indexOf(a.role) - ROLES.indexOf(b.role) || b.points - a.points);
}

export function signed(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "–";
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${fmt(Math.abs(v), digits)}`;
}
