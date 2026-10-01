import type { MatchResult } from "@/components/data/form-strip";

import type { FormResult, ScenarioTeam, TeamRef, TeamSummary } from "./types";

const MINUS = "−";

/** NRR with an explicit sign and 3 decimals: +0.783 / −0.651 / 0.000. */
export function formatNrr(nrr: number): string {
  const v = Math.round(nrr * 1000) / 1000;
  if (v === 0) return "0.000";
  return `${v > 0 ? "+" : MINUS}${Math.abs(v).toFixed(3)}`;
}

export function nrrTone(nrr: number): "positive" | "negative" | "neutral" {
  const v = Math.round(nrr * 1000);
  return v > 0 ? "positive" : v < 0 ? "negative" : "neutral";
}

/** Probability → whole percent, never claiming certainty that isn't there. */
export function formatPct(p: number): string {
  if (p <= 0) return "0%";
  if (p >= 1) return "100%";
  const v = p * 100;
  if (v < 1) return "<1%";
  if (v > 99) return ">99%";
  return `${Math.round(v)}%`;
}

export function signed(n: number): string {
  return n > 0 ? `+${n}` : n < 0 ? `${MINUS}${Math.abs(n)}` : "0";
}

export const formToResult = (f: FormResult): MatchResult => (f === "N" ? "NR" : f);

/** URL segment for a team page: the short code (also accepted by the API). */
export const teamSlug = (t: Pick<TeamRef, "short_code">) => t.short_code;

export function findTeam(teams: TeamSummary[] | undefined, slug: string): TeamSummary | undefined {
  if (!teams) return undefined;
  const s = decodeURIComponent(slug).toUpperCase();
  return (
    teams.find((t) => String(t.id) === s || t.short_code.toUpperCase() === s) ??
    teams.find((t) => t.former_names.some((e) => e.short_code.toUpperCase() === s))
  );
}

const DATE = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const DATE_Y = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

export const shortDate = (iso: string) => DATE.format(new Date(`${iso}T00:00:00Z`));
export const longDate = (iso: string) => DATE_Y.format(new Date(`${iso}T00:00:00Z`));

export function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] ?? s[v] ?? s[0]}`;
}

export type NeedTone = "clinched" | "eliminated" | "open";

/**
 * Plain-words "what X needs" from the scenario state. Deterministic: finishing on strictly more
 * points than the 4th-best maximum any rival can still reach guarantees top 4 without NRR.
 */
export function whatTeamNeeds(team: ScenarioTeam, all: ScenarioTeam[]): { tone: NeedTone; text: string } {
  const name = team.team.short_code;
  if (team.clinched_top2) return { tone: "clinched", text: `${name} have sealed a top-2 finish: two shots at the final.` };
  if (team.clinched_top4) {
    const top2 = team.out_of_top2 ? "Top 2 is out of reach." : `Top 2 in ${formatPct(team.p_top2_incl_ties)} of outcomes.`;
    return { tone: "clinched", text: `${name} are through to the playoffs. ${top2}` };
  }
  if (team.eliminated) {
    return {
      tone: "eliminated",
      text:
        team.remaining > 0
          ? `${name} are out: even ${team.max_points} pts can't reach the top 4.`
          : `${name} finished outside the top 4.`,
    };
  }
  const rivalsMax = all
    .filter((t) => t.team.id !== team.team.id)
    .map((t) => t.max_points)
    .sort((a, b) => b - a);
  const fourthMax = rivalsMax[3] ?? 0;
  const safe = fourthMax + 1;
  const winsForSafe = Math.max(0, Math.ceil((safe - team.points) / 2));
  const left = `${team.remaining} left, max ${team.max_points} pts.`;
  let need: string;
  if (team.remaining === 0) need = "Depends on net run rate.";
  else if (winsForSafe === 0) need = "Already safe on points.";
  else if (winsForSafe <= team.remaining)
    need = `Win ${winsForSafe === team.remaining ? `all ${team.remaining}` : `${winsForSafe} of ${team.remaining}`} (${team.points + winsForSafe * 2} pts) to qualify without needing NRR.`;
  else need = `Can't make sure alone: needs other results to go their way${team.p_top4_tie_dependent > 0 ? " and NRR" : ""}.`;
  return { tone: "open", text: `${left} ${need}` };
}
