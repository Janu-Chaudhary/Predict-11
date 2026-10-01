import { render } from "@testing-library/react";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import { StatLineChart, isolatedPoints, seriesColor } from "./stat-charts";

// jsdom has no layout: give ResponsiveContainer a real box so Recharts draws the SVG.
beforeAll(() => {
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
    width: 600, height: 224, top: 0, left: 0, right: 600, bottom: 224, x: 0, y: 0, toJSON: () => ({}),
  } as DOMRect);
});
afterAll(() => vi.restoreAllMocks());

// A venue's par score by season: unused in 2020 (null), so 2019 has no neighbour.
const seasons = [
  { season: 2019, "avg.first": 171.2 },
  { season: 2020, "avg.first": null },
  { season: 2021, "avg.first": 160.5 },
  { season: 2022, "avg.first": 181 },
];

describe("StatLineChart", () => {
  it("marks points with no plotted neighbour", () => {
    expect([...isolatedPoints(seasons, "avg.first")]).toEqual([0]);
    expect([...isolatedPoints([{ s: 1, v: 5 }], "v")]).toEqual([0]);
    expect([...isolatedPoints([{ s: 1, v: 5 }, { s: 2, v: 6 }], "v")]).toEqual([]);
  });

  it("draws sparse series and keys that are not valid CSS identifiers", () => {
    const { container } = render(
      <StatLineChart title="Par" summary="Par by season" data={seasons} xKey="season" series={[{ key: "avg.first", label: "Avg 1st inns" }]} />,
    );
    expect(container.querySelector("svg.recharts-surface")).not.toBeNull();
    // the colour itself, never an (invalid) var(--color-avg.first)
    const curve = container.querySelector(".recharts-line-curve");
    expect(curve).toHaveAttribute("stroke", seriesColor({ key: "avg.first", label: "" }, 0));
    // 2019 stands alone between the chart edge and a null: drawn as a dot
    expect(container.querySelectorAll("[data-isolated]")).toHaveLength(1);
  });

  it("draws a single-point series as a dot instead of nothing", () => {
    const { container } = render(
      <StatLineChart title="One" summary="One season" data={[{ season: 2026, v: 190 }]} xKey="season" series={[{ key: "v", label: "V" }]} />,
    );
    expect(container.querySelectorAll("[data-isolated]")).toHaveLength(1);
  });
});
