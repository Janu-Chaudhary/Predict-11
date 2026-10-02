import { describe, expect, it } from "vitest";

import { cumulative, filterMatches, finalMatchId, matchLabel, rowToPlayer, shortTitle, teamCounts, xiToPitch } from "./lib";
import type { PlayerRow, SeasonMatch, XiCard, XiPlayer } from "./types";

const header = (id: number, extra: Partial<SeasonMatch["match"]> = {}): SeasonMatch["match"] => ({
  match_id: id,
  date: "2026-05-31",
  season: 2026,
  match_number: null,
  stage: null,
  title: "Match",
  team1: { id: 1, name: "Gujarat Titans", short_code: "GT" },
  team2: { id: 2, name: "Royal Challengers Bengaluru", short_code: "RCB" },
  venue: null,
  venue_name: null,
  city: null,
  winner_id: null,
  result_text: null,
  scores: [],
  ...extra,
});

const row = (id: number, model: number | null, base: number | null, best: number | null, extra: Partial<SeasonMatch["match"]> = {}): SeasonMatch => ({
  match: header(id, extra),
  n_players: 22,
  model_xi_points: model,
  baseline_xi_points: base,
  best_xi_points: best,
  model_minus_baseline: model !== null && base !== null ? model - base : null,
  model_beat_baseline: model !== null && base !== null ? model > base : null,
  captain: null,
  baseline_captain_top2: null,
  mae_model: null,
  mae_base: null,
  coverage: null,
});

const pick = (id: string, role: XiPlayer["role"], pred: number, mult = 1): XiPlayer => ({
  player_id: id,
  name: `Player ${id}`,
  image_url: null,
  team: id.startsWith("g") ? "GT" : "RCB",
  team_name: "",
  role,
  multiplier: mult,
  selected_on: pred,
  pred_mean: pred,
  q10: pred - 20,
  q50: pred - 5,
  q90: pred + 40,
  baseline: 30,
  actual: 50,
  points: 50 * mult,
  credits: null,
});

describe("predictions lib", () => {
  it("accumulates season totals in order, treating nulls as 0", () => {
    const rows = cumulative([row(1, 800, 700, 1200, { match_number: 1 }), row(2, null, 650, 1000, { match_number: 2 }), row(3, 900, 950, 1300, { stage: "Final" })]);
    expect(rows.map((r) => r.model)).toEqual([800, 800, 1700]);
    expect(rows.map((r) => r.baseline)).toEqual([700, 1350, 2300]);
    expect(rows.at(-1)).toMatchObject({ match: "F", best: 3500, margin: -50 });
  });

  it("short titles and labels", () => {
    expect(shortTitle(header(1, { match_number: 17 }))).toBe("M17");
    expect(shortTitle(header(1, { stage: "Qualifier 2" }))).toBe("Q2");
    expect(shortTitle(header(1, { stage: "Eliminator" }))).toBe("E");
    expect(matchLabel(header(1, { title: "Final" }))).toBe("Final · GT v RCB · 31 May");
  });

  it("filters by who won and finds the final", () => {
    const ms = [row(1, 800, 700, 1200), row(2, 600, 650, 1000), row(3, 1, 1, 1, { stage: "Final" }), row(4, 1, 1, 1)];
    expect(filterMatches(ms, "won").map((m) => m.match.match_id)).toEqual([1]);
    expect(filterMatches(ms, "lost").map((m) => m.match.match_id)).toEqual([2]);
    expect(filterMatches(ms, "all")).toHaveLength(4);
    expect(finalMatchId(ms)).toBe(3);
    expect(finalMatchId(ms.slice(0, 2))).toBe(2);
    expect(finalMatchId([])).toBeNull();
  });

  it("maps an XI to pitch players by role with C/VC and the p10/p50/p90 range", () => {
    const xi: XiCard = {
      key: "model",
      label: "Model XI",
      picks: [pick("r1", "BOWL", 40), pick("g1", "BAT", 70, 2), pick("g2", "WK", 50, 1.5), pick("r2", "BAT", 80)],
      captain: "g1",
      vice_captain: "g2",
      actual_points: 0,
      selected_on: 0,
      credits_total: null,
      credits_complete: false,
      overlap_with_best: 0,
    };
    const ps = xiToPitch(xi);
    expect(ps.map((p) => p.id)).toEqual(["g2", "r2", "g1", "r1"]);
    expect(ps.find((p) => p.id === "g1")).toMatchObject({ captain: true, projection: { floor: 50, median: 65, ceiling: 110 } });
    expect(ps.find((p) => p.id === "g2")?.viceCaptain).toBe(true);
    expect(teamCounts(xi)).toEqual({ RCB: 2, GT: 2 });
    const r: PlayerRow = { ...pick("g1", "BAT", 70), in_model_xi: true, in_base_xi: false, in_best_xi: false, model_mult: 2, base_mult: null, best_mult: null, actual_rank: 3, credits: 9 };
    expect(rowToPlayer(r, xi)).toMatchObject({ id: "g1", captain: true, credits: 9, team: "GT" });
  });
});
