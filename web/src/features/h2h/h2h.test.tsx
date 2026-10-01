import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { h2hConfidence, resolveConfidence } from "./confidence";
import { KOHLI_V_BUMRAH } from "./fixtures";
import { H2HCard, howOutList } from "./h2h-card";

const batter = { id: "ba607b88", name: "V Kohli" };
const bowler = { id: "462411b3", name: "JJ Bumrah" };

describe("h2h confidence thresholds", () => {
  it("low < 12, medium 12–29, high ≥ 30", () => {
    expect(h2hConfidence(0)).toBe("low");
    expect(h2hConfidence(11)).toBe("low");
    expect(h2hConfidence(12)).toBe("medium");
    expect(h2hConfidence(29)).toBe("medium");
    expect(h2hConfidence(30)).toBe("high");
    expect(h2hConfidence(108)).toBe("high");
  });
  it("prefers a known server label, else falls back to balls", () => {
    expect(resolveConfidence("medium", 200)).toBe("medium");
    expect(resolveConfidence("weird", 5)).toBe("low");
    expect(resolveConfidence(null, 40)).toBe("high");
  });
});

describe("H2HCard", () => {
  it("shows headline numbers, dismissal types and a high-confidence badge", () => {
    render(<H2HCard batter={batter} bowler={bowler} pair={KOHLI_V_BUMRAH} />);
    expect(screen.getByRole("heading", { name: /V Kohli v JJ Bumrah/ })).toBeInTheDocument();
    const value = (label: string) => screen.getByText(label, { selector: "dt" }).nextElementSibling?.textContent;
    expect(value("Balls")).toBe("108");
    expect(value("Runs")).toBe("159");
    expect(value("Outs")).toBe("5");
    expect(value("SR")).toBe("147.2");
    expect(value("Dot %")).toBe("36.1");
    expect(value("4s")).toBe("16");
    expect(value("6s")).toBe("6");
    const outs = screen.getByRole("list", { name: "Dismissals by type" });
    expect(within(outs).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["caught3", "lbw2"]);
    expect(document.querySelector("[data-level]")?.getAttribute("data-level")).toBe("high");
    expect(screen.queryByText(/Small sample/)).not.toBeInTheDocument();
  });

  it("warns on small samples", () => {
    render(<H2HCard batter={batter} bowler={bowler} pair={{ ...KOHLI_V_BUMRAH, balls: 7, confidence: "low" }} />);
    expect(screen.getByText(/Small sample/)).toBeInTheDocument();
    expect(document.querySelector("[data-level]")?.getAttribute("data-level")).toBe("low");
  });

  it("orders how-out by count", () => {
    expect(howOutList({ bowled: 1, caught: 4, lbw: 0 })).toEqual([{ kind: "caught", n: 4 }, { kind: "bowled", n: 1 }]);
  });
});
