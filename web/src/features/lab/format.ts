import type { EvalSummary, Pair, Phase } from "./types";

export const dash = "–";

export function fmtNum(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return dash;
  return n.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export const fmtInt = (n: number | null | undefined) => fmtNum(n, 0);

export function fmtPct(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return dash;
  return `${(n * 100).toFixed(digits)}%`;
}

export function fmtSigned(n: number | null | undefined, digits = 1, suffix = ""): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return dash;
  const s = n.toFixed(digits);
  return `${n > 0 ? "+" : n < 0 ? "−" : "±"}${s.replace("-", "")}${suffix}`;
}

/** Compact counts: 1234 → "1.2k", 1_234_567 → "1.23M". */
export function fmtCompact(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return dash;
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (Math.abs(n) >= 1e4) return `${(n / 1e3).toFixed(1)}k`;
  return fmtInt(n);
}

export function fmtDuration(s: number | null | undefined): string {
  if (s === null || s === undefined || !Number.isFinite(s)) return dash;
  if (s < 90) return `${Math.round(s)} s`;
  if (s < 3600) return `${Math.round(s / 60)} min`;
  const h = Math.floor(s / 3600);
  return `${h} h ${Math.round((s - h * 3600) / 60)} min`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return dash;
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return dash;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** Feature values: integers stay integers, small magnitudes keep more digits. */
export function fmtValue(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "missing";
  if (Number.isInteger(n)) return String(n);
  const a = Math.abs(n);
  return a >= 100 ? n.toFixed(0) : a >= 10 ? n.toFixed(1) : a >= 1 ? n.toFixed(2) : n.toFixed(3);
}

export type MetricKey = "bestXi" | "captain" | "mae" | "spearman";

export const METRICS: Record<MetricKey, { label: string; short: string; higherIsBetter: boolean; fmt: (n: number | null) => string; diffFmt: (n: number | null) => string; term: string; unit?: string }> = {
  bestXi: { label: "Best-XI points per match", short: "Best-XI pts", higherIsBetter: true, fmt: (n) => fmtNum(n, 1), diffFmt: (n) => fmtSigned(n, 1), term: "best-xi-points", unit: "pts" },
  captain: { label: "Captain in actual top 2", short: "Captain hit", higherIsBetter: true, fmt: (n) => fmtPct(n, 1), diffFmt: (n) => fmtSigned(n === null ? null : n * 100, 1, " pp"), term: "captain-hit-rate" },
  mae: { label: "MAE per player (points)", short: "MAE", higherIsBetter: false, fmt: (n) => fmtNum(n, 2), diffFmt: (n) => fmtSigned(n, 2), term: "mae", unit: "pts" },
  spearman: { label: "Within-match Spearman ρ", short: "Spearman ρ", higherIsBetter: true, fmt: (n) => fmtNum(n, 3), diffFmt: (n) => fmtSigned(n, 3), term: "spearman" },
};

export const pairOf = (s: EvalSummary, k: MetricKey): Pair => s[k];

/** Is the model better than the baseline, and is the CI clear of zero? */
export function verdict(p: Pair, higherIsBetter: boolean): "better" | "worse" | "tie" | "unknown" {
  if (p.diff === null) return "unknown";
  const [lo, hi] = p.ci;
  const good = higherIsBetter ? p.diff > 0 : p.diff < 0;
  if (lo !== null && hi !== null && lo <= 0 && hi >= 0) return "tie";
  return good ? "better" : "worse";
}

export const PHASE_LABEL: Record<Phase, string> = { test: "Test", walkforward: "Walk-forward" };

export function paramValue(v: unknown): string {
  if (v === null || v === undefined) return dash;
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(Number(v.toPrecision(4)));
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}

export function paramsLabel(p: Record<string, unknown>): string {
  return Object.entries(p)
    .map(([k, v]) => `${abbrev(k)} ${paramValue(v)}`)
    .join(" · ");
}

const ABBR: Record<string, string> = {
  num_leaves: "leaves",
  min_child_samples: "min child",
  learning_rate: "lr",
  feature_fraction: "feat frac",
  bagging_fraction: "bag frac",
  bagging_freq: "bag freq",
  lambda_l2: "λ2",
  lambda_l1: "λ1",
};
export const abbrev = (k: string) => ABBR[k] ?? k;
