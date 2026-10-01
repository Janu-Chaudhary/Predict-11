/** Formatting + small helpers shared by the player and H2H features. */

/** Full franchise names from the API (incl. renames and defunct sides) → badge code for TeamBadge. */
const TEAM_NAME_TO_CODE: Record<string, string> = {
  "chennai super kings": "CSK",
  "mumbai indians": "MI",
  "royal challengers bengaluru": "RCB",
  "royal challengers bangalore": "RCB",
  "kolkata knight riders": "KKR",
  "delhi capitals": "DC",
  "delhi daredevils": "DC",
  "punjab kings": "PBKS",
  "kings xi punjab": "PBKS",
  "rajasthan royals": "RR",
  "sunrisers hyderabad": "SRH",
  "gujarat titans": "GT",
  "lucknow super giants": "LSG",
  "deccan chargers": "DCG",
  "kochi tuskers kerala": "KTK",
  "pune warriors": "PWI",
  "pune warriors india": "PWI",
  "rising pune supergiant": "RPS",
  "rising pune supergiants": "RPS",
  "gujarat lions": "GL",
};

export function teamCode(name: string | null | undefined): string | null {
  if (!name) return null;
  const code = TEAM_NAME_TO_CODE[name.trim().toLowerCase()];
  if (code) return code;
  // Already a code (e.g. "CSK") or unknown: initials as a neutral fallback.
  if (/^[A-Z]{2,4}$/.test(name)) return name;
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 4);
}

const DASH = "–";

/** Number with fixed decimals; null/undefined/NaN → en dash. */
export function fmt(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return DASH;
  return v.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export const fmtPct = (v: number | null | undefined, digits = 1) => (v === null || v === undefined ? DASH : `${fmt(v, digits)}%`);

export function pct(part: number, whole: number): number | null {
  return whole > 0 ? (part / whole) * 100 : null;
}

export function strikeRate(runs: number, balls: number): number | null {
  return balls > 0 ? (runs / balls) * 100 : null;
}

export function fmtDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }): string {
  if (!iso) return DASH;
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { ...opts, timeZone: "UTC" });
}

/** "2008–2026" or "2024" from a season list. */
export function seasonSpan(seasons: number[]): string {
  if (seasons.length === 0) return DASH;
  const lo = Math.min(...seasons);
  const hi = Math.max(...seasons);
  return lo === hi ? String(lo) : `${lo}–${hi}`;
}

export const PHASE_LABEL: Record<string, string> = { powerplay: "Powerplay (1–6)", middle: "Middle (7–15)", death: "Death (16–20)" };
export const PHASE_SHORT: Record<string, string> = { powerplay: "PP", middle: "Middle", death: "Death" };

/** Parse a comma-separated id list, de-duplicated, capped. */
export function parseIds(raw: string | string[] | undefined, max = 3): string[] {
  const s = Array.isArray(raw) ? raw.join(",") : (raw ?? "");
  return [...new Set(s.split(",").map((x) => x.trim()).filter(Boolean))].slice(0, max);
}

export function firstParam(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

/** "2024" or "2024-04-01" → valid `since`; anything else → undefined. */
export function parseSince(v: string | undefined): string | undefined {
  return v && /^\d{4}(-\d{2}-\d{2})?$/.test(v) ? v : undefined;
}

export function parseSeason(v: string | undefined): number | undefined {
  const n = Number(v);
  return v && Number.isInteger(n) && n >= 2008 && n <= 2100 ? n : undefined;
}

/** Full name for display ("Virat Kohli"); falls back to the scorecard name until the API sends it. */
export function displayName(p: { name: string; display_name?: string | null }): string {
  return p.display_name?.trim() || p.name;
}

/** Headshot URL or null (initials fallback in PlayerAvatar). */
export function photoOf(p: { image_url?: string | null }): string | null {
  return p.image_url?.trim() || null;
}
