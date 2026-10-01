import { describe, expect, it } from "vitest";

import { deltaE } from "./color";
import { CLASH_THRESHOLD, TEAM_CODES, TEAMS, badgesClash, getTeam, pickMatchColours, tierFor } from "./tokens";

describe("deltaE (OKLab)", () => {
  it("is 0 for identical colours and ~1 for black vs white", () => {
    expect(deltaE("#123456", "#123456")).toBe(0);
    expect(deltaE("#000", "#fff")).toBeCloseTo(1, 2);
  });
});

describe("pickMatchColours clash rule", () => {
  it("keeps both chart colours when they are distinct", () => {
    const r = pickMatchColours("CSK", "MI", "dark");
    expect(r.away).toMatchObject({ color: TEAMS.MI.chartDark, dashed: false, source: "chart" });
  });

  it("moves a clashing away team to its alt colour and dashes it (MI v DC blues)", () => {
    expect(deltaE(TEAMS.MI.chartDark, TEAMS.DC.chartDark)).toBeLessThan(CLASH_THRESHOLD);
    const r = pickMatchColours("MI", "DC", "dark");
    expect(r.home.color).toBe(TEAMS.MI.chartDark);
    expect(r.away).toMatchObject({ color: TEAMS.DC.chartAltDark, dashed: true, source: "alt" });
  });

  it("never returns two series closer than the threshold, for any pairing and theme", () => {
    for (const theme of ["dark", "light"] as const) {
      for (const a of TEAM_CODES) {
        for (const b of TEAM_CODES) {
          if (a === b) continue;
          const r = pickMatchColours(a, b, theme);
          if (r.away.source !== "neutral") expect(deltaE(r.home.color, r.away.color)).toBeGreaterThanOrEqual(CLASH_THRESHOLD);
          if (r.away.source !== "chart") expect(r.away.dashed).toBe(true);
        }
      }
    }
  });
});

describe("teams", () => {
  it("resolves historical and alias codes to neutral/canonical themes", () => {
    expect(getTeam("GL").historical).toBe(true);
    expect(getTeam("KXIP").short).toBe("PBKS");
    expect(getTeam("XYZ").name).toBe("XYZ");
  });

  it("flags badge clashes between near-identical primaries", () => {
    expect(badgesClash("MI", "DC")).toBe(true);
    expect(badgesClash("CSK", "MI")).toBe(false);
  });
});

describe("tierFor", () => {
  it.each([
    [0, 0],
    [19.9, 0],
    [20, 1],
    [45, 2],
    [60, 3],
    [80, 4],
    [Number.NaN, 0],
  ])("%d pts → tier %d", (pts, tier) => expect(tierFor(pts)).toBe(tier));
});
