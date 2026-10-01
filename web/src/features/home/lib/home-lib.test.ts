import { describe, expect, it } from "vitest";

import type { HomeState, Wagon, Worm, XI } from "../types";
import { countdown } from "./countdown";
import { parsePreview, planHero, resolveHero } from "./rotation";
import { wagonRays } from "./wagon-geometry";
import { buildParticles, makeScale, pointOn, stepParticles, TIMELINE, yTicks } from "./worm-geometry";
import { layoutXI, pickRows } from "./xi-layout";

const team = (id: number, code: string) => ({ id, name: code, short_code: code });
const match = {
  id: 1535465,
  date: "2026-05-31",
  season: 2026,
  title: "Final",
  stage: "Final",
  match_number: null,
  venue: null,
  team1: team(56, "GT"),
  team2: team(46, "RCB"),
  winner_id: 46,
  result: "RCB won by 5 wickets",
  scores: [],
};
const offSeason: HomeState = {
  phase: "off_season",
  now: "2026-10-02T12:00:00+05:30",
  hero: "C",
  hero_match_id: 1535465,
  hero_reason: "Off-season",
  next_fixture: null,
  last_match: match,
  season: null,
};
const worm: Worm = {
  match,
  ball_count: 4,
  y_max: 60,
  innings: [
    {
      innings: 1,
      team: team(56, "GT"),
      runs: 10,
      wickets: 1,
      overs: "0.2",
      balls: [
        { x: 1 / 6, runs: 4, wickets: 0, kind: "four", label: "0.1" },
        { x: 2 / 6, runs: 10, wickets: 1, kind: "wicket", label: "0.2" },
      ],
    },
    {
      innings: 2,
      team: team(46, "RCB"),
      runs: 7,
      wickets: 0,
      overs: "0.2",
      balls: [
        { x: 1 / 6, runs: 6, wickets: 0, kind: "six", label: "0.1" },
        { x: 2 / 6, runs: 7, wickets: 0, kind: "run", label: "0.2" },
      ],
    },
  ],
};

describe("hero rotation", () => {
  it("parses only A/B/C previews", () => {
    expect(parsePreview("A")).toBe("A");
    expect(parsePreview(["C"])).toBe("C");
    expect(parsePreview("x")).toBeNull();
    expect(parsePreview(undefined)).toBeNull();
  });

  it("off-season → C on the hero match", () => {
    const plan = planHero(offSeason);
    expect(plan).toMatchObject({ requested: "C", heroMatchId: 1535465, wormMatchId: 1535465 });
    expect(resolveHero(plan, { worm }, match).kind).toBe("C");
  });

  it("pre-match B worm fallback uses the last match, not the fixture", () => {
    const pre: HomeState = {
      ...offSeason,
      phase: "pre_match",
      hero: "B",
      hero_match_id: 999,
      next_fixture: { id: 999, start: "2027-03-20T19:30:00+05:30", title: "Match 1", venue: null, team1: team(1, "CSK"), team2: team(2, "MI"), status: "provisional" },
    };
    const plan = planHero(pre);
    expect(plan).toMatchObject({ requested: "B", heroMatchId: 999, wormMatchId: 1535465 });
    const r = resolveHero(plan, { xi: null, worm }, null);
    expect(r.kind).toBe("C");
    expect(r.note).toMatch(/not persisted/);
  });

  it("A falls back to C when shot data is missing, and to none without a worm", () => {
    const plan = planHero(offSeason, "A");
    expect(resolveHero(plan, { wagon: null, worm }, match).kind).toBe("C");
    expect(resolveHero(plan, { wagon: null, worm: null }, match).kind).toBe("none");
    const wagon: Wagon = {
      match_id: 1,
      batter: "V Kohli",
      team: null,
      runs: 4,
      balls: 1,
      not_out: true,
      left_handed: false,
      shots: [{ over: 2, ball: 1, label: "2.1", runs: 4, direction: 52, distance_pct: 100, zone: 1, zone_name: "fine leg", bowler: "M Siraj" }],
      source: "test",
    };
    expect(resolveHero(plan, { wagon, worm }, match).kind).toBe("A");
  });

  it("B needs exactly 11 picked players", () => {
    const players = Array.from({ length: 22 }, (_, i) => ({
      id: `p${i}`,
      name: `P ${i}`,
      short_name: `P${i}`,
      team: i % 2 ? "GT" : "RCB",
      role: (["WK", "BAT", "AR", "BOWL"] as const)[i % 4],
      points: 100 - i,
      picked: i < 11,
      captain: i === 0 ? ("C" as const) : i === 1 ? ("VC" as const) : null,
    }));
    const xi: XI = { match_id: 1, kind: "actual", teams: ["GT", "RCB"], players, total: 900 };
    expect(resolveHero(planHero(offSeason, "B"), { xi, worm }, match).kind).toBe("B");
    const short = { ...xi, players: players.map((p, i) => ({ ...p, picked: i < 10 })) };
    expect(resolveHero(planHero(offSeason, "B"), { xi: short, worm }, match).kind).toBe("C");

    const L = layoutXI(players, ["GT", "RCB"], 720, 540);
    expect(L.wide).toBe(true);
    expect(L.pitch.size).toBe(11);
    expect(L.bench.size).toBe(22);
    expect(pickRows(players).flat()).toHaveLength(11);
    const narrow = layoutXI(players, ["GT", "RCB"], 358, 500);
    for (const [x] of narrow.pitch.values()) expect(x).toBeGreaterThan(0);
  });
});

describe("geometry", () => {
  it("one particle per ball plus dust, settling on the worm", () => {
    const s = makeScale(400, 300, worm.y_max);
    const p = buildParticles(worm, s, 10);
    expect(p.n).toBe(14);
    expect(p.real).toBe(4);
    stepParticles(p, TIMELINE.end + 5000);
    for (let i = 0; i < p.n; i++) {
      expect(p.px[i]).toBeCloseTo(p.tx[i], 0);
      expect(p.py[i]).toBeCloseTo(p.ty[i], 0);
    }
    expect(pointOn([{ x: 0, y: 0 }, { x: 2, y: 4 }], 0.5)).toEqual({ x: 1, y: 2 });
    expect(yTicks(180)).toEqual([0, 50, 100, 150]);
  });

  it("wagon rays stay inside the rope and mirror for left-handers", () => {
    const shot = { over: 2, ball: 1, label: "2.1", runs: 4, direction: 0, distance_pct: 100, zone: 2, zone_name: "square leg", bowler: "X" };
    const [r] = wagonRays([shot]);
    const [l] = wagonRays([shot], true);
    expect(r.tip!.x).toBeLessThan(0); // leg side on the left for a right-hander
    expect(l.tip!.x).toBeGreaterThan(0);
    expect((r.tip!.x / 190) ** 2 + (r.tip!.y / 180) ** 2).toBeLessThan(1);
    expect(r.title).toBe("2.1 · X → square leg · 4");
  });

  it("countdown splits and clamps", () => {
    expect(countdown(90_061_000, 0)).toEqual({ days: 1, hours: 1, minutes: 1, seconds: 1, total: 90_061 });
    expect(countdown(0, 5000).total).toBe(0);
  });
});
