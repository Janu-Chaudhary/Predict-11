import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { confidenceFor } from "@/lib/confidence";

import { ConfidenceBadge } from "./confidence-badge";

describe("confidenceFor thresholds", () => {
  it.each([
    [0, "low"],
    [29, "low"],
    [30, "medium"],
    [64, "medium"],
    [99, "medium"],
    [100, "high"],
    [812, "high"],
  ] as const)("n=%i → %s", (n, level) => {
    expect(confidenceFor(n)).toBe(level);
  });

  it("treats NaN / negative / infinite n as low", () => {
    expect(confidenceFor(Number.NaN)).toBe("low");
    expect(confidenceFor(-5)).toBe("low");
    expect(confidenceFor(Number.POSITIVE_INFINITY)).toBe("low");
  });

  it("accepts custom thresholds", () => {
    expect(confidenceFor(12, { medium: 10, high: 20 })).toBe("medium");
    expect(confidenceFor(20, { medium: 10, high: 20 })).toBe("high");
  });
});

describe("ConfidenceBadge", () => {
  it("prints n and the level as text (not colour alone)", () => {
    const { container } = render(<ConfidenceBadge n={64} />);
    expect(container.firstChild).toHaveAttribute("data-level", "medium");
    expect(screen.getByText("Medium confidence, sample size 64")).toBeInTheDocument();
    expect(container).toHaveTextContent("n=64 · medium");
  });

  it("lets an explicit level override the n rule", () => {
    const { container } = render(<ConfidenceBadge n={5} level="high" />);
    expect(container.firstChild).toHaveAttribute("data-level", "high");
  });
});
