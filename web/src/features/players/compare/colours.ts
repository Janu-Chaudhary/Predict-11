import { getTeam, pickMatchColours, type ThemeName } from "@/lib/tokens";

/** Theme-specific series colour for each compared player (CSS colour strings). */
export type PlayerColour = { light: string; dark: string };

/** Fallbacks when a player has no team or every team colour is taken (fixed order, never cycled). */
const FALLBACK = ["var(--chart-1)", "var(--chart-3)", "var(--chart-4)"];

function pickFor(teams: (string | null)[], theme: ThemeName): string[] {
  const out: string[] = [];
  teams.forEach((team, i) => {
    if (!team) {
      out.push(FALLBACK.find((c) => !out.includes(c)) ?? FALLBACK[i % FALLBACK.length]);
      return;
    }
    const t = getTeam(team);
    const own = theme === "dark" ? t.chartDark : t.chartLight;
    const alt = theme === "dark" ? t.chartAltDark : t.chartAltLight;
    // Clash rule from tokens.pickMatchColours, applied against every player already coloured.
    const clashes = (c: string) =>
      out.some((prev, j) => prev === c || (teams[j] && c === own && pickMatchColours(teams[j]!, team, theme).away.source !== "chart"));
    const choice = !clashes(own) ? own : !out.includes(alt) && !clashes(alt) ? alt : (FALLBACK.find((c) => !out.includes(c)) ?? own);
    out.push(choice);
  });
  return out;
}

/** Team chart colours (getTeam(code).chartLight / chartDark), de-clashed between the players. */
export function playerColours(teams: (string | null)[]): PlayerColour[] {
  const light = pickFor(teams, "light");
  const dark = pickFor(teams, "dark");
  return teams.map((_, i) => ({ light: light[i], dark: dark[i] }));
}

/** CSS custom property each player's colour is exposed as (`--pc0`…). */
export const pcVar = (i: number) => `var(--pc${i})`;

/** Short name for tight labels: surname from the display name ("Virat Kohli" → "Kohli"). */
export function shortName(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts.length > 1 ? parts[parts.length - 1] : name;
}

/** Surnames, falling back to full names when two players share one. */
export function shortNames(names: string[]): string[] {
  const s = names.map(shortName);
  return s.map((x, i) => (s.indexOf(x) !== s.lastIndexOf(x) ? names[i] : x));
}
