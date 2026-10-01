import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CompareEntry } from "../types";
import { CompareTable } from "./compare-table";
import { bestIndices } from "./metrics";

const bat = (o: Partial<CompareEntry["batting"]>): CompareEntry["batting"] => ({
  innings: 100, not_outs: 10, runs: 3000, balls: 2200, average: 33, strike_rate: 136, fifties: 20, hundreds: 1,
  thirties: 30, ducks: 5, fours: 300, sixes: 100, dot_pct: 35, highest: "100", ...o,
});
const bowl = (o: Partial<CompareEntry["bowling"]>): CompareEntry["bowling"] => ({
  innings: 0, overs: "0", balls: 0, runs: 0, wickets: 0, economy: null, average: null, strike_rate: null, best: null,
  three_plus: 0, four_plus: 0, five_plus: 0, maidens: 0, dot_pct: null, ...o,
});
const entry = (id: string, b: Partial<CompareEntry["batting"]>, w: Partial<CompareEntry["bowling"]> = {}): CompareEntry => ({
  id, name: id.toUpperCase(), matches: 100, last_team: null, batting: bat(b), bowling: bowl(w),
  fielding: { catches: 10, stumpings: 0, run_outs: 1 }, batting_phases: [], bowling_phases: [],
});

describe("bestIndices", () => {
  it("picks max or min, shares ties, ignores nulls and ineligible", () => {
    expect(bestIndices([1, 3, 2], "high")).toEqual([1]);
    expect(bestIndices([7.5, 6.9, 8], "low")).toEqual([1]);
    expect(bestIndices([3, 3, 1], "high")).toEqual([0, 1]);
    expect(bestIndices([null, 5, 4], "high")).toEqual([1]);
    expect(bestIndices([9, 5, 4], "high", [false, true, true])).toEqual([1]);
  });
  it("highlights nothing when all tie, fewer than two compete, or the row is informational", () => {
    expect(bestIndices([2, 2], "high")).toEqual([]);
    expect(bestIndices([2, null], "high")).toEqual([]);
    expect(bestIndices([1, 2], null)).toEqual([]);
  });
});

describe("CompareTable", () => {
  it("marks the best cell per row, including lower-is-better rows", () => {
    const players = [
      entry("a", { runs: 9000, strike_rate: 135 }, { balls: 60, economy: 8.8, overs: "10" }),
      entry("b", { runs: 6000, strike_rate: 140 }, { balls: 3000, economy: 7.2, overs: "500" }),
    ];
    const { container } = render(<CompareTable players={players} caption="test" />);
    const best = (row: string) => [...container.querySelectorAll(`tr[data-row="${row}"] td`)].map((td) => td.hasAttribute("data-best"));
    expect(best("runs")).toEqual([true, false]);
    expect(best("bat_sr")).toEqual([false, true]);
    expect(best("econ")).toEqual([false, true]);
    expect(best("ct")).toEqual([false, false]); // tie → no highlight
    expect(container.querySelector('tr[data-row="runs"] td[data-best]')?.textContent).toContain("(best)");
  });
});
