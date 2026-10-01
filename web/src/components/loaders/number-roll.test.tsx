import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { digitOffset, rollTokens } from "@/lib/digits";

import { NumberRoll } from "./number-roll";

describe("rollTokens", () => {
  it("splits digits and static characters, keyed from the right", () => {
    expect(rollTokens("-1,284.5")).toEqual([
      { kind: "char", value: "-", key: "c7--" },
      { kind: "digit", value: 1, key: "d6" },
      { kind: "char", value: ",", key: "c5-," },
      { kind: "digit", value: 2, key: "d4" },
      { kind: "digit", value: 8, key: "d3" },
      { kind: "digit", value: 4, key: "d2" },
      { kind: "char", value: ".", key: "c1-." },
      { kind: "digit", value: 5, key: "d0" },
    ]);
  });

  it("keeps unit columns stable when the number grows (98 → 102)", () => {
    const before = rollTokens("98").map((t) => t.key);
    const after = rollTokens("102").map((t) => t.key);
    expect(after.slice(-2)).toEqual(before);
  });

  it("maps a digit to a 10%-per-glyph offset", () => {
    expect(digitOffset(0)).toBe("translateY(-0%)");
    expect(digitOffset(7)).toBe("translateY(-70%)");
  });
});

describe("NumberRoll", () => {
  it("exposes the whole value once to assistive tech and positions each column", () => {
    const { container } = render(<NumberRoll value={612} />);
    expect(screen.getByRole("img", { name: "612" })).toBeInTheDocument();
    const cols = container.querySelectorAll<HTMLElement>("[data-digit]");
    expect([...cols].map((c) => c.dataset.digit)).toEqual(["6", "1", "2"]);
    expect(cols[0]).toHaveStyle({ transform: "translateY(-60%)" });
  });

  it("rolls to the new value on change and honours a custom format and label", () => {
    const fmt = (n: number) => n.toFixed(1);
    const { rerender, container } = render(<NumberRoll value={98.5} format={fmt} label="Credits used 98.5" />);
    rerender(<NumberRoll value={99.5} format={fmt} label="Credits used 99.5" />);
    expect(screen.getByRole("img", { name: "Credits used 99.5" })).toHaveAttribute("data-value", "99.5");
    const cols = container.querySelectorAll<HTMLElement>("[data-digit]");
    expect(cols[1]).toHaveStyle({ transform: "translateY(-90%)" });
  });

  it("disables the transition under reduced motion via motion-reduce", () => {
    const { container } = render(<NumberRoll value={5} />);
    expect(container.querySelector("[data-digit]")).toHaveClass("motion-reduce:transition-none");
  });
});
