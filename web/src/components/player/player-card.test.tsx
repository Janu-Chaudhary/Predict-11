import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Player } from "@/lib/mock";

import { PlayerCard } from "./player-card";

const player: Player = {
  id: "x1",
  name: "Test Player",
  team: "RCB",
  role: "AR",
  credits: 9,
  projection: { floor: 12, median: 36, ceiling: 84 },
};

describe("PlayerCard", () => {
  it("renders name, team, role, credits and projection range", () => {
    render(<PlayerCard player={player} />);
    const card = screen.getByRole("article", { name: "Test Player" });
    expect(within(card).getByLabelText("Royal Challengers Bengaluru")).toHaveTextContent("RCB");
    expect(within(card).getByText("All-rounder")).toBeInTheDocument();
    expect(within(card).getByText("9.0")).toBeInTheDocument();
    expect(
      within(card).getByRole("img", { name: "Projected points: floor 12, median 36, ceiling 84" }),
    ).toBeInTheDocument();
  });

  it("positions the range band and median marker on the default 0–120 scale", () => {
    render(<PlayerCard player={player} />);
    expect(screen.getByTestId("range-band")).toHaveStyle({ left: "10%", width: "60%" });
    expect(screen.getByTestId("range-marker")).toHaveStyle({ left: "30%" });
  });

  it("calls lock / exclude handlers via mouse and keyboard", async () => {
    const user = userEvent.setup();
    const onToggleLock = vi.fn();
    const onToggleExclude = vi.fn();
    render(<PlayerCard player={player} onToggleLock={onToggleLock} onToggleExclude={onToggleExclude} />);

    await user.click(screen.getByRole("button", { name: "Lock Test Player" }));
    expect(onToggleLock).toHaveBeenCalledWith("x1");

    screen.getByRole("button", { name: "Exclude Test Player" }).focus();
    await user.keyboard("{Enter}");
    expect(onToggleExclude).toHaveBeenCalledWith("x1");
  });

  it("reflects locked / excluded state with aria-pressed", () => {
    const { rerender } = render(<PlayerCard player={player} status="locked" />);
    expect(screen.getByRole("button", { name: "Unlock Test Player" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Exclude Test Player" })).toHaveAttribute("aria-pressed", "false");

    rerender(<PlayerCard player={player} status="excluded" />);
    expect(screen.getByRole("button", { name: "Include Test Player" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("article")).toHaveAttribute("data-status", "excluded");
  });
});
