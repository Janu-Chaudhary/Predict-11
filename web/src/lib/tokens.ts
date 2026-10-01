/**
 * Design tokens: IPL franchise colours and fantasy role colours.
 * Team colours are approximations of each franchise's primary/secondary brand colours,
 * used sparingly (badges, accents) — never as large background fills.
 */

export const TEAM_CODES = ["CSK", "MI", "RCB", "KKR", "DC", "PBKS", "RR", "SRH", "GT", "LSG"] as const;
export type TeamCode = (typeof TEAM_CODES)[number];

export type TeamTheme = {
  name: string;
  short: TeamCode;
  /** Primary brand colour (badge background). */
  primary: string;
  /** Secondary brand colour (accent / border). */
  secondary: string;
  /** Text colour that is legible on `primary`. */
  onPrimary: string;
};

export const TEAMS: Record<TeamCode, TeamTheme> = {
  CSK: { name: "Chennai Super Kings", short: "CSK", primary: "#F9CD05", secondary: "#0081E9", onPrimary: "#1A1A1A" },
  MI: { name: "Mumbai Indians", short: "MI", primary: "#004BA0", secondary: "#D1AB3E", onPrimary: "#FFFFFF" },
  RCB: { name: "Royal Challengers Bengaluru", short: "RCB", primary: "#C8102E", secondary: "#1A1A1A", onPrimary: "#FFFFFF" },
  KKR: { name: "Kolkata Knight Riders", short: "KKR", primary: "#3A225D", secondary: "#B3A123", onPrimary: "#FFFFFF" },
  DC: { name: "Delhi Capitals", short: "DC", primary: "#17449B", secondary: "#EF1B23", onPrimary: "#FFFFFF" },
  PBKS: { name: "Punjab Kings", short: "PBKS", primary: "#D71920", secondary: "#A7A9AC", onPrimary: "#FFFFFF" },
  RR: { name: "Rajasthan Royals", short: "RR", primary: "#EA1A85", secondary: "#254AA5", onPrimary: "#FFFFFF" },
  SRH: { name: "Sunrisers Hyderabad", short: "SRH", primary: "#F26522", secondary: "#1A1A1A", onPrimary: "#1A1A1A" },
  GT: { name: "Gujarat Titans", short: "GT", primary: "#1B2133", secondary: "#B8975A", onPrimary: "#FFFFFF" },
  LSG: { name: "Lucknow Super Giants", short: "LSG", primary: "#0057E2", secondary: "#F28B00", onPrimary: "#FFFFFF" },
};

export const ROLES = ["WK", "BAT", "AR", "BOWL"] as const;
export type Role = (typeof ROLES)[number];

export type RoleTheme = {
  label: string;
  /** Tailwind classes for the role chip (light + dark). */
  chip: string;
  /** Raw colour for non-Tailwind uses (charts, SVG). */
  hex: string;
};

export const ROLE_THEME: Record<Role, RoleTheme> = {
  WK: {
    label: "Wicket-keeper",
    chip: "bg-amber-100 text-amber-900 ring-amber-300 dark:bg-amber-500/15 dark:text-amber-200 dark:ring-amber-500/30",
    hex: "#D97706",
  },
  BAT: {
    label: "Batter",
    chip: "bg-sky-100 text-sky-900 ring-sky-300 dark:bg-sky-500/15 dark:text-sky-200 dark:ring-sky-500/30",
    hex: "#0284C7",
  },
  AR: {
    label: "All-rounder",
    chip: "bg-violet-100 text-violet-900 ring-violet-300 dark:bg-violet-500/15 dark:text-violet-200 dark:ring-violet-500/30",
    hex: "#7C3AED",
  },
  BOWL: {
    label: "Bowler",
    chip: "bg-emerald-100 text-emerald-900 ring-emerald-300 dark:bg-emerald-500/15 dark:text-emerald-200 dark:ring-emerald-500/30",
    hex: "#059669",
  },
};
