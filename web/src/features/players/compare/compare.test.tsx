import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CompareEntry } from "../types";
import { playerColours, shortNames } from "./colours";
import { CompareRow, MetricCard } from "./compare-ui";
import { barWidths, bestIndices, COMPARE_ROWS, rowsFor, tally, tallyText, visibleRows, type Subject } from "./metrics";
import { radarRows } from "./skill-radar";

const bat = (o: Partial<CompareEntry["batting"]>): CompareEntry["batting"] => ({
  innings: 100, not_outs: 10, runs: 3000, balls: 2200, average: 33, strike_rate: 136, fifties: 20, hundreds: 1,
  thirties: 30, ducks: 5, fours: 300, sixes: 100, dot_pct: 35, highest: "100", ...o,
});
const bowl = (o: Partial<CompareEntry["bowling"]>): CompareEntry["bowling"] => ({
  innings: 0, overs: "0", balls: 0, runs: 0, wickets: 0, economy: null, average: null, strike_rate: null, best: null,
  three_plus: 0, four_plus: 0, five_plus: 0, maidens: 0, dot_pct: null, ...o,
});
const entry = (id: string, b: Partial<CompareEntry["batting"]>, w: Partial<CompareEntry["bowling"]> = {}): Subject => ({
  id, name: id.toUpperCase(), matches: 100, last_team: null, batting: bat(b), bowling: bowl(w),
  fielding: { catches: 10, stumpings: 0, run_outs: 1 }, batting_phases: [], bowling_phases: [],
});
const row = (key: string) => COMPARE_ROWS.find((r) => r.key === key)!;

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

describe("barWidths", () => {
  it("scales to the max for higher-is-better and informational rows", () => {
    expect(barWidths([50, 100], "high")).toEqual([50, 100]);
    expect(barWidths([25, 100, 75], null)).toEqual([25, 100, 75]);
  });
  it("inverts lower-is-better so the smaller value is the longer bar", () => {
    const [a, b] = barWidths([8, 6], "low") as number[];
    expect(b).toBe(100);
    expect(a).toBeCloseTo(75);
  });
  it("draws no bar for missing values and zero-length bars when everything is zero", () => {
    expect(barWidths([null, 40], "high")).toEqual([null, 100]);
    expect(barWidths([undefined, null], "low")).toEqual([null, null]);
    expect(barWidths([0, 0], "high")).toEqual([0, 0]);
  });
});

describe("tally", () => {
  const a = entry("a", { runs: 9000, strike_rate: 135, fifties: 30 }, { balls: 60, economy: 8.8, overs: "10" });
  const b = entry("b", { runs: 6000, strike_rate: 140, fifties: 30 }, { balls: 3000, economy: 7.2, overs: "500" });
  it("counts contested rows only and ignores ties and informational rows", () => {
    const rows = [row("runs"), row("bat_sr"), row("50s"), row("inns"), row("econ")];
    const t = tally(rows, [a, b]);
    // runs → a; SR → b; 50s tie (contested, no winner); innings informational; econ → b
    expect(t).toEqual({ wins: [1, 2], contested: 4 });
    expect(tallyText(t, ["A", "B"])).toBe("B leads 2 of 4");
    expect(tallyText({ wins: [2, 2], contested: 5 }, ["A", "B"])).toBe("Level · 2 each of 5");
    expect(tallyText({ wins: [0, 0], contested: 0 }, ["A", "B"])).toBeNull();
  });
  it("hides rows nobody has a value for", () => {
    const keys = visibleRows([entry("x", {}), entry("y", {})], rowsFor(["Bowling"])).map((r) => r.key);
    expect(keys).toContain("wkts"); // 0 is a value
    expect(keys).not.toContain("econ");
    expect(keys).not.toContain("best");
  });
});

describe("CompareRow / MetricCard", () => {
  const players = [
    entry("a", { runs: 9000, strike_rate: 135 }, { balls: 60, economy: 8.8, overs: "10" }),
    entry("b", { runs: 6000, strike_rate: 140 }, { balls: 3000, economy: 7.2, overs: "500" }),
  ];
  const best = (c: HTMLElement, key: string) => [...c.querySelectorAll(`[data-row="${key}"] [data-best], [data-row="${key}"] .num`)].filter((el) => el.classList.contains("num")).map((el) => el.hasAttribute("data-best"));

  it("marks the leader per row, including lower-is-better rows, and ties get no leader", () => {
    const { container } = render(<MetricCard id="t" title="T" icon={null} accent="red" rows={[row("runs"), row("bat_sr"), row("econ"), row("ct")]} players={players} names={["A", "B"]} />);
    expect(best(container, "runs")).toEqual([true, false]);
    expect(best(container, "bat_sr")).toEqual([false, true]);
    expect(best(container, "econ")).toEqual([false, true]);
    expect(best(container, "ct")).toEqual([false, false]);
    expect(container.querySelector('[data-row="runs"] [data-best]')?.textContent).toContain("(best)");
    expect(container.querySelector('[data-row="econ"]')?.textContent).toContain("lower is better");
    expect(container.querySelector("[data-tally]")?.textContent).toContain("B leads 2 of 4") // the tied catches row is contested, won by nobody;
  });

  it("sizes the split bar proportionally and leaves missing values without a bar", () => {
    const { container } = render(<CompareRow row={row("runs")} players={players} names={["A", "B"]} />);
    const w = [...container.querySelectorAll("[data-bar]")].map((el) => Number(el.getAttribute("data-width")));
    expect(w).toEqual([100, 66.7]);
    const noBowl = [players[0], entry("c", {})];
    const { container: c2 } = render(<CompareRow row={row("econ")} players={noBowl} names={["A", "C"]} />);
    expect(c2.querySelectorAll("[data-bar]")).toHaveLength(1);
    expect(c2.textContent).toContain("–");
  });

  it("renders one bar per player for three players", () => {
    const three = [...players, entry("c", { runs: 3000 })];
    const { container } = render(<CompareRow row={row("runs")} players={three} names={["A", "B", "C"]} />);
    expect(container.querySelectorAll("[data-bar]")).toHaveLength(3);
    expect(container.querySelectorAll("[data-best]")).toHaveLength(1);
  });
});

describe("helpers", () => {
  it("de-clashes team colours and falls back for unknown teams", () => {
    const [a, b] = playerColours(["CSK", "CSK"]);
    expect(a.dark).not.toBe(b.dark);
    expect(a.light).not.toBe(b.light);
    expect(playerColours(["RCB"])[0].dark).toBe("#EF4B5F");
    expect(playerColours([null])[0].light).toMatch(/^var\(--chart-/);
  });
  it("uses surnames unless two players share one", () => {
    expect(shortNames(["MS Dhoni", "Virat Kohli"])).toEqual(["Dhoni", "Kohli"]);
    expect(shortNames(["Rohit Sharma", "Ishant Sharma"])).toEqual(["Rohit Sharma", "Ishant Sharma"]);
  });
  it("maps percentiles to radar rows with null for unranked axes", () => {
    const rows = radarRows(
      {
        filters: { season: null, since: null },
        axes: [{ key: "economy", label: "Economy", better: "low", sample: "", population: 300 }],
        players: [
          { id: "a", axes: [{ key: "economy", value: 8.8, percentile: null }] },
          { id: "b", axes: [{ key: "economy", value: 7.2, percentile: 91.5 }] },
        ],
      },
      ["a", "b"],
    );
    expect(rows).toEqual([{ axis: "Economy", key: "economy", p0: null, p1: 91.5 }]);
  });
});
