import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { MilestoneCard, MilestoneProgressBar } from "./milestone-card";
import { MilestonesWatchView } from "./milestones-watch";
import { groupMilestones, milestoneProgress } from "./progress";
import type { Milestone } from "./types";

const ms = (over: Partial<Milestone> & Pick<Milestone, "stat" | "current" | "target">): Milestone => ({
  player: { id: `p-${over.stat}-${over.current}`, name: `Player ${over.current}` },
  team: "Mumbai Indians",
  needed: over.target - over.current,
  text: "",
  ...over,
});

const MOCK: Milestone[] = [
  ms({ player: { id: "hp", name: "HH Pandya" }, stat: "runs", current: 2955, target: 3000, team: "Mumbai Indians" }),
  ms({ player: { id: "kp", name: "KH Pandya" }, stat: "runs", current: 1982, target: 2000, team: "Royal Challengers Bengaluru" }),
  ms({ player: { id: "kr", name: "K Rabada" }, stat: "wickets", current: 148, target: 150, team: "Gujarat Titans" }),
  ms({ player: { id: "kn", name: "KK Nair" }, stat: "sixes", current: 49, target: 50, team: "Delhi Capitals" }),
];

describe("milestoneProgress", () => {
  it("measures from the previous round number, not from zero", () => {
    expect(milestoneProgress({ stat: "runs", current: 2955, target: 3000 })).toMatchObject({ from: 2000, to: 3000, pct: 95 });
    // Below 1,000 runs the ladder steps by 500.
    expect(milestoneProgress({ stat: "runs", current: 980, target: 1000 })).toMatchObject({ from: 500, pct: 96 });
    expect(milestoneProgress({ stat: "wickets", current: 148, target: 150 })).toMatchObject({ from: 100, pct: 96 });
    // Sixes step by 100 once past 100.
    expect(milestoneProgress({ stat: "sixes", current: 195, target: 200 })).toMatchObject({ from: 100, pct: 95 });
    expect(milestoneProgress({ stat: "sixes", current: 49, target: 50 })).toMatchObject({ from: 0, pct: 98 });
  });

  it("never reports 100% before the target and clamps out-of-range values", () => {
    expect(milestoneProgress({ stat: "matches", current: 99, target: 100 }).pct).toBe(98);
    expect(milestoneProgress({ stat: "runs", current: 1999.9, target: 2000 }).pct).toBeLessThanOrEqual(99);
    expect(milestoneProgress({ stat: "runs", current: 3000, target: 3000 })).toMatchObject({ ratio: 1, pct: 100 });
    expect(milestoneProgress({ stat: "mystery", current: 40, target: 50 })).toMatchObject({ from: 0, pct: 80 });
  });

  it("groups by stat in a fixed order, closest first", () => {
    const groups = groupMilestones(MOCK);
    expect(groups.map((g) => g.stat)).toEqual(["runs", "wickets", "sixes"]);
    expect(groups[0].items.map((m) => m.player.name)).toEqual(["KH Pandya", "HH Pandya"]);
  });
});

describe("MilestoneProgressBar", () => {
  it("exposes an accessible progressbar sized to the progress", () => {
    render(<MilestoneProgressBar milestone={MOCK[0]} />);
    const bar = screen.getByRole("progressbar", { name: "HH Pandya: 2,955 of 3,000 runs" });
    expect(bar).toHaveAttribute("aria-valuemin", "2000");
    expect(bar).toHaveAttribute("aria-valuemax", "3000");
    expect(bar).toHaveAttribute("aria-valuenow", "2955");
    expect(screen.getByTestId("milestone-fill")).toHaveStyle({ width: "95.5%" });
  });
});

describe("MilestoneCard", () => {
  it("reads 'needs N for target' with team badge and profile link", () => {
    render(<MilestoneCard milestone={MOCK[0]} />);
    const card = screen.getByRole("article", { name: "HH Pandya" });
    expect(card).toHaveTextContent(/needs\s*45\s*for 3,000 IPL runs/);
    expect(within(card).getByLabelText("Mumbai Indians")).toHaveTextContent("MI");
    expect(within(card).getByRole("link", { name: "HH Pandya" })).toHaveAttribute("href", "/players/hp");
  });
});

describe("MilestonesWatchView", () => {
  it("groups cards by type and filters with chips", async () => {
    render(<MilestonesWatchView milestones={MOCK} season={2026} asOf="2026-05-31" />);
    expect(screen.getByRole("heading", { name: /^Runs/ })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(4);

    await userEvent.click(screen.getByRole("button", { name: /^Wickets/ }));
    expect(screen.getByRole("button", { name: /^Wickets/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(screen.queryByRole("heading", { name: /^Runs/ })).not.toBeInTheDocument();
  });

  it("explains an empty list instead of dead-ending", () => {
    render(<MilestonesWatchView milestones={[]} season={2012} asOf={null} />);
    expect(screen.getByRole("heading", { name: "No milestones within reach for IPL 2012" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /see current streaks/i })).toHaveAttribute("href", "/records/streaks");
  });
});
