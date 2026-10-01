import { describe, expect, it } from "vitest";

import { normalizeRange, rangeGeometry } from "./range";

describe("rangeGeometry", () => {
  it("maps floor/median/ceiling to track percentages", () => {
    expect(rangeGeometry({ floor: 10, median: 40, ceiling: 100 }, 0, 200)).toEqual({ start: 5, width: 45, marker: 20 });
  });

  it("respects a non-zero scale minimum", () => {
    expect(rangeGeometry({ floor: 0, median: 50, ceiling: 100 }, -100, 100)).toEqual({ start: 50, width: 50, marker: 75 });
  });

  it("clamps values outside the scale to the track edges", () => {
    const g = rangeGeometry({ floor: -20, median: 60, ceiling: 500 }, 0, 120);
    expect(g.start).toBe(0);
    expect(g.width).toBe(100);
    expect(g.marker).toBe(50);
  });

  it("re-orders an unordered range", () => {
    expect(normalizeRange({ floor: 80, median: 10, ceiling: 40 })).toEqual({ floor: 10, median: 40, ceiling: 80 });
    expect(rangeGeometry({ floor: 60, median: 30, ceiling: 0 }, 0, 120)).toEqual({ start: 0, width: 50, marker: 25 });
  });

  it("collapses to zero for a degenerate scale instead of NaN", () => {
    expect(rangeGeometry({ floor: 1, median: 2, ceiling: 3 }, 50, 50)).toEqual({ start: 0, width: 0, marker: 0 });
  });

  it("handles a zero-width range", () => {
    expect(rangeGeometry({ floor: 30, median: 30, ceiling: 30 }, 0, 120)).toEqual({ start: 25, width: 0, marker: 25 });
  });
});
