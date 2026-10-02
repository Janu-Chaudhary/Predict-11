import type { Player } from "@/lib/mock";
import type { TeamCode } from "@/lib/tokens";

import type { PlayerRow, SeasonMatch, XiCard } from "./types";

const ROLE_ORDER = { WK: 0, BAT: 1, AR: 2, BOWL: 3 } as const;

/** Short x-axis label: "M17", "Q1", "E", "Q2", "F". */
export function shortTitle(m: SeasonMatch["match"]): string {
  if (m.match_number) return `M${m.match_number}`;
  const s = (m.stage ?? "").toLowerCase();
  if (s.includes("qualifier 1")) return "Q1";
  if (s.includes("qualifier 2")) return "Q2";
  if (s.includes("eliminator")) return "E";
  if (s.includes("final")) return "F";
  return m.title;
}

export type CumulativeRow = { match: string; model: number; baseline: number; best: number; margin: number | null };

/** Running season totals (model / baseline / best possible) in match order; nulls add 0. */
export function cumulative(matches: SeasonMatch[]): CumulativeRow[] {
  let model = 0;
  let baseline = 0;
  let best = 0;
  return matches.map((m) => {
    model += m.model_xi_points ?? 0;
    baseline += m.baseline_xi_points ?? 0;
    best += m.best_xi_points ?? 0;
    return { match: shortTitle(m.match), model: Math.round(model), baseline: Math.round(baseline), best: Math.round(best), margin: m.model_minus_baseline };
  });
}

/** Predicted XI → the shared PitchView's Player shape (range = model p10 / p50 / p90). */
export function xiToPitch(xi: XiCard): Player[] {
  return [...xi.picks]
    .sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role] || (b.pred_mean ?? 0) - (a.pred_mean ?? 0))
    .map((p) => ({
      id: p.player_id,
      name: p.name,
      team: p.team as TeamCode,
      role: p.role,
      credits: p.credits ?? 0,
      projection: { floor: Math.round(p.q10 ?? 0), median: Math.round(p.q50 ?? p.pred_mean ?? 0), ceiling: Math.round(p.q90 ?? 0) },
      captain: p.player_id === xi.captain,
      viceCaptain: p.player_id === xi.vice_captain,
      photoUrl: p.image_url,
    }));
}

export type MatchFilter = "all" | "won" | "lost";

export function filterMatches(matches: SeasonMatch[], f: MatchFilter): SeasonMatch[] {
  if (f === "all") return matches;
  return matches.filter((m) => m.model_minus_baseline !== null && (f === "won" ? m.model_minus_baseline > 0 : m.model_minus_baseline < 0));
}

export const round0 = (n: number | null | undefined) => (n === null || n === undefined || !Number.isFinite(n) ? null : Math.round(n));

/** Any match row (all players of both teams) → PlayerCard's Player, with C/VC from an XI. */
export function rowToPlayer(p: PlayerRow, xi: XiCard | null): Player {
  return {
    id: p.player_id,
    name: p.name,
    team: p.team as TeamCode,
    role: p.role,
    credits: p.credits ?? 0,
    projection: { floor: Math.round(p.q10 ?? 0), median: Math.round(p.q50 ?? p.pred_mean ?? 0), ceiling: Math.round(p.q90 ?? 0) },
    captain: xi?.captain === p.player_id,
    viceCaptain: xi?.vice_captain === p.player_id,
    photoUrl: p.image_url,
  };
}

/** The season's final (stage "Final"), else its last match; null for an empty season. */
export function finalMatchId(matches: SeasonMatch[]): number | null {
  const f = [...matches].reverse().find((m) => (m.match.stage ?? "").toLowerCase() === "final");
  return (f ?? matches.at(-1))?.match.match_id ?? null;
}

/** "Final · GT v RCB · 31 May" style picker label. */
export function matchLabel(m: SeasonMatch["match"]): string {
  const d = m.date ? new Date(`${m.date}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }) : "";
  return `${m.title} · ${m.team1?.short_code ?? "?"} v ${m.team2?.short_code ?? "?"}${d ? ` · ${d}` : ""}`;
}

/** Players per team code in an XI, e.g. {GT: 5, RCB: 6}. */
export function teamCounts(xi: XiCard): Record<string, number> {
  const c: Record<string, number> = {};
  for (const p of xi.picks) c[p.team] = (c[p.team] ?? 0) + 1;
  return c;
}
