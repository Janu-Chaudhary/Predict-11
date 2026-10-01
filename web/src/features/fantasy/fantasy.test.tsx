import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { BEST_XIS_2026, LEADERBOARD_2026, MATCH_XI_1527674, PLAYER_KOHLI, TEAM_OF_SEASON_2026 } from "./fixtures";
import { categoryShares, consistencyWord, describeDistribution, filterLeaderboard, fmtPts, leaderHref, parseMinMatches, parseRole, parseSort, rangeText, sortLeaderboard } from "./format";
import { MatchXiCard } from "./match-xi-view";
import { consistencyScore, leaderboard, matchBestXi, playerFantasy, seasonBestXis, teamOfSeason } from "./normalize";
import { FantasyDistribution } from "./player-fantasy";
import { TeamOfSeasonCard } from "./best-xi-view";
import type { LeaderRow } from "./types";

const row = (id: string, o: Partial<LeaderRow>): LeaderRow => ({
  rank: null,
  player: { id, name: id },
  team: "MI",
  role: "BAT",
  credits: null,
  ppc: null,
  recent: [],
  matches: 10,
  total: 0,
  mean: null,
  median: null,
  sd: null,
  p10: null,
  p90: null,
  max: null,
  consistency: null,
  pct_50: null,
  pct_100: null,
  ...o,
});

describe("leaderboard sorting and filters", () => {
  const rows = [
    row("a", { total: 900, mean: 60, consistency: 40, ppc: 6 }),
    row("b", { total: 1200, mean: 80, consistency: 20, ppc: null, role: "WK" }),
    row("c", { total: 700, mean: 90, consistency: 70, ppc: 9, matches: 4, role: "BOWL" }),
    row("d", { total: 900, mean: 55, consistency: 40, ppc: 4 }),
  ];
  const ids = (rs: LeaderRow[]) => rs.map((r) => r.player.id);

  it("sorts by each metric, highest first", () => {
    expect(ids(sortLeaderboard(rows, "total"))).toEqual(["b", "a", "d", "c"]);
    expect(ids(sortLeaderboard(rows, "mean"))).toEqual(["c", "b", "a", "d"]);
    expect(ids(sortLeaderboard(rows, "consistency"))).toEqual(["c", "a", "d", "b"]);
  });

  it("sinks rows without credits when sorting by points per credit", () => {
    expect(ids(sortLeaderboard(rows, "ppc"))).toEqual(["c", "a", "d", "b"]);
  });

  it("breaks ties on total then name, and does not mutate the input", () => {
    const before = ids(rows);
    expect(ids(sortLeaderboard([row("z", { total: 5, mean: 1 }), row("y", { total: 5, mean: 1 })], "mean"))).toEqual(["y", "z"]);
    expect(ids(rows)).toEqual(before);
  });

  it("filters by role and minimum matches", () => {
    expect(ids(filterLeaderboard(rows, "ALL", 5))).toEqual(["a", "b", "d"]);
    expect(ids(filterLeaderboard(rows, "WK", 1))).toEqual(["b"]);
    expect(ids(filterLeaderboard(rows, "BOWL", 5))).toEqual([]);
  });

  it("round-trips URL state with defaults omitted", () => {
    expect(parseSort("ppc")).toBe("ppc");
    expect(parseSort("nope")).toBe("total");
    expect(parseRole("ar")).toBe("AR");
    expect(parseRole("x")).toBe("ALL");
    expect(parseMinMatches("0")).toBe(5);
    expect(leaderHref({ season: 2026, sort: "total", role: "ALL", min: 5 }, 2026)).toBe("/fantasy");
    expect(leaderHref({ season: 2025, sort: "mean", role: "BOWL", min: 3 }, 2026)).toBe("/fantasy?season=2025&sort=mean&role=BOWL&min=3");
  });
});

describe("normalize (live contract)", () => {
  it("maps leaderboard rows: team code, n → matches, cv → consistency", () => {
    const lb = leaderboard(LEADERBOARD_2026);
    expect(lb.credits_available).toBe(true);
    const top = lb.rows[0];
    expect(top.player.id).toBe("470f446b");
    expect(top.team).toBe("RR");
    expect(top.matches).toBe(16);
    expect(top.consistency).toBeCloseTo(31, 0);
    expect(top.ppc).toBeCloseTo(19.36);
  });

  it("maps a player's distribution, mix and last 10 oldest → newest", () => {
    const p = playerFantasy(PLAYER_KOHLI);
    expect(p.matches).toBe(279);
    expect(p.pct_100).toBeCloseTo(15.1);
    expect(p.mix?.batting).toBe(11347);
    expect(p.last10).toHaveLength(10);
    expect(p.last10[0].date! <= p.last10[9].date!).toBe(true);
    expect(p.last10[0].opponent).toBe("GT");
  });

  it("marks C/VC from the XI ids and keeps the form XI projection", () => {
    const m = matchBestXi(MATCH_XI_1527674);
    expect(m.home).toBe("SRH");
    expect(m.best?.picks.filter((p) => p.captain)).toHaveLength(1);
    expect(m.best?.picks.filter((p) => p.vice_captain)).toHaveLength(1);
    expect(m.best?.total).toBe(1329.5);
    expect(m.naive?.picks[0].projected).not.toBeNull();
    expect(m.gap).toBe(421.5);
  });

  it("derives team-of-season C/VC from the two biggest scorers", () => {
    const t = teamOfSeason(TEAM_OF_SEASON_2026);
    const xi = t.by_total!;
    expect(xi.picks).toHaveLength(11);
    const c = xi.picks.find((p) => p.captain)!;
    expect(c.points).toBe(Math.max(...xi.picks.map((p) => p.points)));
    expect(c.effective).toBe(c.points * 2);
  });

  it("maps the per-match season list", () => {
    const s = seasonBestXis(BEST_XIS_2026);
    expect(s.matches[0].home).toBe("SRH");
    expect(s.matches[0].top_scorer?.name).toBe("Ishan Kishan");
  });

  it("consistency score clamps and falls back to sd / mean", () => {
    expect(consistencyScore(0.37)).toBeCloseTo(63);
    expect(consistencyScore(1.4)).toBe(0);
    expect(consistencyScore(null, 50, 25)).toBe(50);
    expect(consistencyScore(null, 0, 10)).toBeNull();
  });
});

describe("distribution formatting", () => {
  it("formats points and ranges", () => {
    expect(fmtPts(96)).toBe("96");
    expect(fmtPts(168.5)).toBe("168.5");
    expect(fmtPts(null)).toBe("–");
    expect(rangeText({ p10: 14, median: 96, p90: 211 })).toBe("14–96–211");
    expect(rangeText({ p10: null, median: 96, p90: 211 })).toBeNull();
    expect(consistencyWord(63)).toBe("Steady");
    expect(consistencyWord(31)).toBe("Mixed");
    expect(consistencyWord(10)).toBe("Volatile");
  });

  it("describes a distribution in words for screen readers", () => {
    const d = playerFantasy(PLAYER_KOHLI);
    expect(describeDistribution(d)).toMatch(/^279 matches, mean 53\.9, floor 9\.8, median 45, ceiling 112\.6, consistency 23 of 100$/);
  });

  it("turns the category mix into shares that sum to 100, dropping negatives", () => {
    const s = categoryShares({ batting: 60, bowling: -4, fielding: 20, lineup: 10, bonuses: 10 });
    expect(s.map((x) => x.key)).toEqual(["batting", "fielding", "bonuses", "lineup"]);
    expect(s.reduce((a, x) => a + x.pct, 0)).toBeCloseTo(100);
    expect(categoryShares(null)).toEqual([]);
  });

  it("renders the profile panel: range, tiles, mix and per-season table", () => {
    render(<FantasyDistribution data={playerFantasy(PLAYER_KOHLI)} scopeLabel="Career" />);
    expect(screen.getByRole("img", { name: /floor 10, median 45, ceiling 113/i })).toBeInTheDocument();
    expect(screen.getByText("47%")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Batting 75%/ })).toBeInTheDocument();
    const table = screen.getByRole("table", { name: /by season/i });
    expect(within(table).getAllByRole("row").length).toBeGreaterThan(1);
  });
});

describe("best-XI rendering", () => {
  it("shows the hindsight XI on the pitch with C/VC, totals and the gap", async () => {
    render(<MatchXiCard data={matchBestXi(MATCH_XI_1527674)} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/SRH\s*v\s*RCB/);
    const pitch = screen.getByRole("region", { name: "Pitch view" });
    const tokens = within(pitch).getAllByRole("button");
    expect(tokens).toHaveLength(11);
    expect(within(pitch).getByRole("button", { name: /Ishan Kishan.*captain/ })).toBeInTheDocument();
    expect(screen.getByText("1,329.5")).toBeInTheDocument();
    expect(screen.getByText("+422")).toBeInTheDocument();
    // Form XI lists the pre-match projection next to the realised points.
    const formXi = screen.getByRole("list", { name: "Form XI" });
    expect(within(formXi).getAllByRole("listitem")).toHaveLength(11);
    // Switch the hindsight XI to the list view.
    await userEvent.click(screen.getAllByRole("button", { name: /List/ })[0]);
    expect(screen.getByRole("list", { name: "Hindsight best XI" })).toBeInTheDocument();
  });

  it("switches the team of the season between season total and per-match", async () => {
    render(<TeamOfSeasonCard data={teamOfSeason(TEAM_OF_SEASON_2026)} />);
    expect(screen.getByText("Season points")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Pitch view" })).getAllByRole("button")).toHaveLength(11);
    await userEvent.click(screen.getByRole("button", { name: "Per match" }));
    expect(screen.getByText("Points / match")).toBeInTheDocument();
  });
});
