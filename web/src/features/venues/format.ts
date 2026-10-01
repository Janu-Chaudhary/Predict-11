/** Number formatting shared by the venue and records views. Missing values render as an en dash. */

const DASH = "–";

export const isNum = (v: number | null | undefined): v is number => typeof v === "number" && Number.isFinite(v);

/** Whole runs (par scores are averages; a lone decimal adds false precision). */
export const fmtRuns = (v: number | null | undefined) => (isNum(v) ? Math.round(v).toLocaleString("en-IN") : DASH);

export const fmtPct = (v: number | null | undefined) => (isNum(v) ? `${Math.round(v)}%` : DASH);

/** Run rates / economy: one decimal. */
export const fmtRate = (v: number | null | undefined, digits = 1) => (isNum(v) ? v.toFixed(digits) : DASH);

export const fmtInt = (v: number | null | undefined) => (isNum(v) ? v.toLocaleString("en-IN") : DASH);

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-05-24" → "24 May 2026" (no timezone shifting: the API sends plain dates). */
export function fmtDate(iso: string | null | undefined, withYear = true): string {
  if (!iso) return DASH;
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return withYear ? `${d} ${MONTHS[m - 1]} ${y}` : `${d} ${MONTHS[m - 1]}`;
}

/** Shorten long official ground names for tight spaces ("Bharat Ratna … Ekana Cricket Stadium" → "Ekana Cricket Stadium"). */
export function shortVenueName(name: string): string {
  const ekana = name.match(/Ekana.*$/);
  if (ekana) return ekana[0];
  return name.replace(/^Dr\.?\s+/, "").replace(/\s*,\s*[^,]+$/, "");
}

export const PHASE_LABEL: Record<string, string> = {
  powerplay: "Powerplay",
  middle: "Middle",
  death: "Death",
};

export const PHASE_OVERS: Record<string, string> = {
  powerplay: "overs 1–6",
  middle: "overs 7–15",
  death: "overs 16–20",
};
