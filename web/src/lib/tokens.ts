/**
 * Design tokens that live in TS rather than CSS: franchise colours, role colours,
 * the projection tier ramp and the two-team chart colour clash rule.
 * See docs/DESIGN-DIRECTION.md §2.2–2.3.
 *
 * Team colours are accents only: badge, 3 px stripe, chart series, team-page top border.
 * Never card/page fills, text colour, buttons or table-row backgrounds.
 */

import { deltaE } from "./color";

export const TEAM_CODES = ["CSK", "MI", "RCB", "KKR", "DC", "PBKS", "RR", "SRH", "GT", "LSG"] as const;
export type TeamCode = (typeof TEAM_CODES)[number];

/** Defunct franchises that appear in historical data. Rendered in neutral colours. */
export const HISTORICAL_TEAM_CODES = ["DCG", "KTK", "PWI", "RPS", "GL"] as const;
export type HistoricalTeamCode = (typeof HISTORICAL_TEAM_CODES)[number];
export type AnyTeamCode = TeamCode | HistoricalTeamCode;

export type ThemeName = "dark" | "light";

export type TeamTheme = {
  name: string;
  short: string;
  /** Primary brand colour (badge background). */
  primary: string;
  /** Secondary brand colour (badge underline). */
  secondary: string;
  /** Text colour that is legible on `primary`. */
  onPrimary: string;
  /** Chart series colour on the dark base (≥ 3:1 vs surface-1). */
  chartDark: string;
  /** Chart series colour on the light base. */
  chartLight: string;
  /** Fallback series colour when two teams clash (dark / light). */
  chartAltDark: string;
  chartAltLight: string;
  /** True for defunct franchises: neutral palette. */
  historical?: boolean;
  /** Local crest under /public/teams (current franchises only). */
  logo?: string;
};

const TEAM_BASE: Record<TeamCode, Omit<TeamTheme, "logo">> = {
  CSK: { name: "Chennai Super Kings", short: "CSK", primary: "#F9CD05", secondary: "#0081E9", onPrimary: "#1A1A1A", chartDark: "#F9CD05", chartLight: "#B8920A", chartAltDark: "#4FA3F7", chartAltLight: "#0067BA" },
  MI: { name: "Mumbai Indians", short: "MI", primary: "#004BA0", secondary: "#D1AB3E", onPrimary: "#FFFFFF", chartDark: "#4C8EF0", chartLight: "#004BA0", chartAltDark: "#D1AB3E", chartAltLight: "#9C7A1A" },
  RCB: { name: "Royal Challengers Bengaluru", short: "RCB", primary: "#C8102E", secondary: "#1A1A1A", onPrimary: "#FFFFFF", chartDark: "#EF4B5F", chartLight: "#C8102E", chartAltDark: "#D4AF37", chartAltLight: "#8C6D1F" },
  KKR: { name: "Kolkata Knight Riders", short: "KKR", primary: "#3A225D", secondary: "#B3A123", onPrimary: "#FFFFFF", chartDark: "#A98BE0", chartLight: "#3A225D", chartAltDark: "#D9C64A", chartAltLight: "#857512" },
  DC: { name: "Delhi Capitals", short: "DC", primary: "#17449B", secondary: "#EF1B23", onPrimary: "#FFFFFF", chartDark: "#6B95F2", chartLight: "#17449B", chartAltDark: "#F2545B", chartAltLight: "#C8141C" },
  PBKS: { name: "Punjab Kings", short: "PBKS", primary: "#D71920", secondary: "#A7A9AC", onPrimary: "#FFFFFF", chartDark: "#FF7A6B", chartLight: "#D71920", chartAltDark: "#C4C6C9", chartAltLight: "#5F6165" },
  RR: { name: "Rajasthan Royals", short: "RR", primary: "#EA1A85", secondary: "#254AA5", onPrimary: "#FFFFFF", chartDark: "#F25CA8", chartLight: "#C2156E", chartAltDark: "#7F9BE6", chartAltLight: "#254AA5" },
  SRH: { name: "Sunrisers Hyderabad", short: "SRH", primary: "#F26522", secondary: "#1A1A1A", onPrimary: "#1A1A1A", chartDark: "#F7883F", chartLight: "#D4520F", chartAltDark: "#C9CDDA", chartAltLight: "#3A3F52" },
  GT: { name: "Gujarat Titans", short: "GT", primary: "#1B2133", secondary: "#B8975A", onPrimary: "#FFFFFF", chartDark: "#C9A86A", chartLight: "#1B2133", chartAltDark: "#8EA2CC", chartAltLight: "#8A6A2C" },
  LSG: { name: "Lucknow Super Giants", short: "LSG", primary: "#0057E2", secondary: "#F28B00", onPrimary: "#FFFFFF", chartDark: "#3FA0FF", chartLight: "#0057E2", chartAltDark: "#FFA640", chartAltLight: "#B86400" },
};

export const TEAMS: Record<TeamCode, TeamTheme> = Object.fromEntries(
  TEAM_CODES.map((c) => [c, { ...TEAM_BASE[c], logo: `/teams/${c.toLowerCase()}.webp` }]),
) as Record<TeamCode, TeamTheme>;

const neutral = (name: string, short: string): TeamTheme => ({
  name,
  short,
  primary: "#3A3F55",
  secondary: "#8A90A8",
  onPrimary: "#F2F3F8",
  chartDark: "#A3A9C2",
  chartLight: "#4A506A",
  chartAltDark: "#D8DBE6",
  chartAltLight: "#2A2F42",
  historical: true,
});

export const HISTORICAL_TEAMS: Record<HistoricalTeamCode, TeamTheme> = {
  DCG: neutral("Deccan Chargers", "DCG"),
  KTK: neutral("Kochi Tuskers Kerala", "KTK"),
  PWI: neutral("Pune Warriors India", "PWI"),
  RPS: neutral("Rising Pune Supergiant", "RPS"),
  GL: neutral("Gujarat Lions", "GL"),
};

/** Team aliases seen in source data (old names / codes) → canonical code. */
const TEAM_ALIASES: Record<string, AnyTeamCode> = {
  KXIP: "PBKS",
  DD: "DC",
  DEC: "DCG",
  DCH: "DCG",
  KOC: "KTK",
  PW: "PWI",
  RPSG: "RPS",
};

export function isTeamCode(code: string): code is TeamCode {
  return (TEAM_CODES as readonly string[]).includes(code);
}

/** Resolve any team code (current, historical, alias, unknown) to a theme. Never throws. */
export function getTeam(code: string): TeamTheme {
  const up = code.toUpperCase();
  const canon = TEAM_ALIASES[up] ?? up;
  if (isTeamCode(canon)) return TEAMS[canon];
  if ((HISTORICAL_TEAM_CODES as readonly string[]).includes(canon)) return HISTORICAL_TEAMS[canon as HistoricalTeamCode];
  return neutral(code, up.slice(0, 4));
}

export function teamChartColour(code: string, theme: ThemeName): string {
  const t = getTeam(code);
  return theme === "dark" ? t.chartDark : t.chartLight;
}

/** ΔE (OKLab) below which two series are considered a clash (§2.3). */
export const CLASH_THRESHOLD = 0.12;

/** Neutral fallback: foreground at 70% (CSS value, theme-aware). */
export const NEUTRAL_SERIES = "color-mix(in oklch, var(--foreground) 70%, transparent)";
const NEUTRAL_SERIES_HEX: Record<ThemeName, string> = { dark: "#B9BCC9", light: "#5A5E70" };

export type SeriesColour = {
  team: string;
  color: string;
  /** Dashed line / hatched shape cue. Always set on the away team when a clash was resolved. */
  dashed: boolean;
  source: "chart" | "alt" | "neutral";
};

/**
 * Two-team colour assignment (worm, momentum, H2H). Home keeps its chart colour.
 * If the away colour is within ΔE < 0.12 it switches to its alt colour; if that still
 * clashes it becomes neutral foreground at 70%. The away series gets a dash whenever it moved.
 */
export function pickMatchColours(home: string, away: string, theme: ThemeName): { home: SeriesColour; away: SeriesColour } {
  const h = getTeam(home);
  const a = getTeam(away);
  const homeColour = theme === "dark" ? h.chartDark : h.chartLight;
  const awayColour = theme === "dark" ? a.chartDark : a.chartLight;
  const awayAlt = theme === "dark" ? a.chartAltDark : a.chartAltLight;

  const homeSeries: SeriesColour = { team: home, color: homeColour, dashed: false, source: "chart" };
  if (deltaE(homeColour, awayColour) >= CLASH_THRESHOLD) {
    return { home: homeSeries, away: { team: away, color: awayColour, dashed: false, source: "chart" } };
  }
  if (deltaE(homeColour, awayAlt) >= CLASH_THRESHOLD) {
    return { home: homeSeries, away: { team: away, color: awayAlt, dashed: true, source: "alt" } };
  }
  return {
    home: homeSeries,
    away: { team: away, color: NEUTRAL_SERIES_HEX[theme], dashed: true, source: "neutral" },
  };
}

/* ---------- Roles ---------- */

export const ROLES = ["WK", "BAT", "AR", "BOWL"] as const;
export type Role = (typeof ROLES)[number];

export type RoleTheme = {
  label: string;
  /** Tailwind classes for the role chip (light + dark). */
  chip: string;
  /** Raw colour for non-Tailwind uses (charts, SVG). */
  hex: string;
};

/** The four role hues are reserved for roles (§2.6). */
export const ROLE_THEME: Record<Role, RoleTheme> = {
  WK: {
    label: "Wicket-keeper",
    chip: "bg-amber-500/12 text-amber-800 ring-amber-600/25 dark:bg-amber-400/12 dark:text-amber-200 dark:ring-amber-400/25",
    hex: "#D97706",
  },
  BAT: {
    label: "Batter",
    chip: "bg-sky-500/12 text-sky-800 ring-sky-600/25 dark:bg-sky-400/12 dark:text-sky-200 dark:ring-sky-400/25",
    hex: "#0284C7",
  },
  AR: {
    label: "All-rounder",
    chip: "bg-violet-500/12 text-violet-800 ring-violet-600/25 dark:bg-violet-400/12 dark:text-violet-200 dark:ring-violet-400/25",
    hex: "#7C3AED",
  },
  BOWL: {
    label: "Bowler",
    chip: "bg-emerald-500/12 text-emerald-800 ring-emerald-600/25 dark:bg-emerald-400/12 dark:text-emerald-200 dark:ring-emerald-400/25",
    hex: "#059669",
  },
};

/* ---------- Projection tier ramp ---------- */

export type Tier = 0 | 1 | 2 | 3 | 4;

/** `<20` · `20–39` · `40–59` · `60–79` · `80+` fantasy points. */
export function tierFor(points: number): Tier {
  if (!(points >= 20)) return 0;
  if (points < 40) return 1;
  if (points < 60) return 2;
  if (points < 80) return 3;
  return 4;
}

/** Background class + legible text class per tier. */
export const TIER_CLASS: Record<Tier, { bg: string; text: string }> = {
  0: { bg: "bg-tier-0", text: "text-foreground" },
  1: { bg: "bg-tier-1", text: "text-foreground" },
  2: { bg: "bg-tier-2", text: "text-brand-foreground" },
  3: { bg: "bg-tier-3", text: "text-primary-foreground" },
  4: { bg: "bg-tier-4", text: "text-primary-foreground" },
};

/**
 * Badge-level clash rule: in a two-team context, if the away badge's primary colour is
 * within ΔE < 0.12 of the home badge, the away badge gets its secondary colour as a ring.
 */
export function badgesClash(home: string, away: string): boolean {
  return deltaE(getTeam(home).primary, getTeam(away).primary) < CLASH_THRESHOLD;
}
