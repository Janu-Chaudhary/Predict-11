import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PlayerAvatar, initials } from "./player-avatar";
import { TeamBadge } from "./team-badge";

describe("PlayerAvatar", () => {
  it("falls back to initials without a URL", () => {
    const { container } = render(<PlayerAvatar name="Ruturaj Gaikwad" team="CSK" />);
    expect(container.firstChild).toHaveAttribute("data-state", "fallback");
    expect(container).toHaveTextContent("RG");
  });

  it("shows a skeleton while loading and initials after a load error", () => {
    const { container } = render(<PlayerAvatar name="MS Dhoni" src="https://documents.iplt20.com/x.png" />);
    expect(container.firstChild).toHaveAttribute("data-state", "loading");
    fireEvent.error(container.querySelector("img")!);
    expect(container.firstChild).toHaveAttribute("data-state", "fallback");
    expect(container).toHaveTextContent("MD");
  });

  it("computes initials from first and last names", () => {
    expect(initials("Jasprit Jasbirsingh Bumrah")).toBe("JB");
    expect(initials("  ")).toBe("?");
  });
});

describe("TeamBadge", () => {
  it("renders the crest for a current franchise with an accessible name", () => {
    const { container } = render(<TeamBadge team="RCB" />);
    expect(screen.getByRole("img", { name: "Royal Challengers Bengaluru" })).toHaveTextContent("RCB");
    expect(container.querySelector("img")?.getAttribute("src")).toContain("rcb.png");
  });

  it("uses the monogram for historical teams and after a logo error", () => {
    const { container, rerender } = render(<TeamBadge team="GL" size="lg" />);
    expect(container.querySelector("img")).toBeNull();
    rerender(<TeamBadge team="MI" size="lg" />);
    fireEvent.error(container.querySelector("img")!);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByRole("img", { name: "Mumbai Indians" })).toHaveTextContent("MI");
  });

  it("marks a clashing away badge", () => {
    render(<TeamBadge team="DC" opponent="MI" side="away" />);
    expect(screen.getByRole("img", { name: "Delhi Capitals" })).toHaveAttribute("data-clash", "true");
  });
});
