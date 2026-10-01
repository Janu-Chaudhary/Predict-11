import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FixturePicker } from "./components/fixture-picker";
import { PointsTableView, zoneFor } from "./components/points-table";
import { ScenarioTeamList, sortScenarioTeams } from "./components/scenario-teams";
import { formatNrr, formatPct, whatTeamNeeds } from "./format";
import type { PointsRow, ScenarioFixture, ScenarioTeam, TeamRef } from "./types";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const T = (id: number, short_code: string, name: string): TeamRef => ({ id, short_code, name });
const RCB = T(46, "RCB", "Royal Challengers Bengaluru");
const GT = T(56, "GT", "Gujarat Titans");
const SRH = T(45, "SRH", "Sunrisers Hyderabad");
const RR = T(54, "RR", "Rajasthan Royals");
const PBKS = T(51, "PBKS", "Punjab Kings");
const DC = T(52, "DC", "Delhi Capitals");

// Real 2026 final table (top 6) from /api/v1/seasons/2026/table.
const row = (position: number, team: TeamRef, won: number, lost: number, nr: number, points: number, nrr: number, form: PointsRow["form"]): PointsRow => ({
  position,
  team,
  played: 14,
  won,
  lost,
  no_result: nr,
  tied: 0,
  points,
  nrr,
  runs_for: 0,
  overs_for: "0",
  runs_against: 0,
  overs_against: "0",
  form,
  qualified: position <= 4,
});
const ROWS: PointsRow[] = [
  row(1, RCB, 9, 5, 0, 18, 0.783, ["L", "W", "W", "W", "L"]),
  row(2, GT, 9, 5, 0, 18, 0.695, ["W", "W", "W", "L", "W"]),
  row(3, SRH, 9, 5, 0, 18, 0.524, ["L", "W", "L", "W", "W"]),
  row(4, RR, 8, 6, 0, 16, 0.189, ["L", "L", "L", "W", "W"]),
  row(5, PBKS, 7, 6, 1, 15, 0.309, ["L", "L", "L", "L", "W"]),
  row(6, DC, 7, 7, 0, 14, -0.651, ["L", "L", "W", "N", "W"]),
];

describe("format", () => {
  it("signs NRR with a true minus and 3 decimals", () => {
    expect(formatNrr(0.783)).toBe("+0.783");
    expect(formatNrr(-0.651)).toBe("−0.651");
    expect(formatNrr(0.0001)).toBe("0.000");
  });
  it("never prints false certainty", () => {
    expect(formatPct(0.8757)).toBe("88%");
    expect(formatPct(0.9963)).toBe(">99%");
    expect(formatPct(0.001)).toBe("<1%");
    expect(formatPct(0)).toBe("0%");
    expect(formatPct(1)).toBe("100%");
  });
  it("zones: gold top 2, violet 3-4", () => {
    expect([1, 2, 3, 4, 5].map(zoneFor)).toEqual(["q1", "q1", "elim", "elim", null]);
  });
});

describe("PointsTableView", () => {
  it("renders the 2026 top 4 in order with signed, coloured NRR and form", () => {
    render(<PointsTableView rows={ROWS} caption="IPL 2026 points table" />);
    const table = screen.getByRole("table", { name: "IPL 2026 points table" });
    const bodyRows = within(table).getAllByRole("row").slice(1).filter((r) => !r.hasAttribute("aria-hidden"));
    expect(bodyRows.map((r) => within(r).getAllByRole("img")[0].getAttribute("aria-label"))).toEqual(ROWS.map((r) => r.team.name));
    expect(within(bodyRows[0]).getByText("+0.783")).toHaveClass("text-positive");
    expect(within(bodyRows[5]).getByText("−0.651")).toHaveClass("text-negative");
    expect(within(bodyRows[0]).getByRole("list", { name: /Last 5: lost, won, won, won, lost/ })).toBeInTheDocument();
    expect(within(bodyRows[5]).getByRole("list", { name: /no result/ })).toBeInTheDocument();
    expect(within(bodyRows[0]).getByText(", Qualifier 1 (top 2)")).toBeInTheDocument();
  });

  it("draws the playoff line right after 4th", () => {
    render(<PointsTableView rows={ROWS} caption="t" />);
    const all = screen.getAllByRole("row", { hidden: true });
    const lineIdx = all.findIndex((r) => r.getAttribute("data-testid") === "playoff-line");
    expect(all[lineIdx - 1]).toHaveTextContent("Rajasthan Royals");
    expect(all[lineIdx + 1]).toHaveTextContent("Punjab Kings");
    expect(screen.getAllByTestId("playoff-line")).toHaveLength(1);
  });
});

const team = (t: TeamRef, o: Partial<ScenarioTeam>): ScenarioTeam => ({
  team: t,
  played: 12,
  points: 12,
  wins: 6,
  remaining: 2,
  max_points: 16,
  p_top4: 0.5,
  p_top4_incl_ties: 0.6,
  p_top4_tie_dependent: 0.1,
  p_top2: 0.2,
  p_top2_incl_ties: 0.3,
  p_top2_tie_dependent: 0.1,
  clinched_top4: false,
  eliminated: false,
  clinched_top2: false,
  out_of_top2: false,
  ...o,
});

// Shape of 2026 after match 56 (from /scenarios?after_match=56).
const SC: ScenarioTeam[] = [
  team(RCB, { points: 14, remaining: 3, max_points: 20, p_top4: 0.6875, p_top4_incl_ties: 0.8806 }),
  team(GT, { points: 16, remaining: 2, max_points: 20, p_top4: 0.8757, p_top4_incl_ties: 0.9963 }),
  team(DC, { points: 10, remaining: 2, max_points: 14, p_top4: 0.001, p_top4_incl_ties: 0.032 }),
  team(T(48, "MI", "Mumbai Indians"), { points: 6, remaining: 3, max_points: 12, p_top4: 0, p_top4_incl_ties: 0, eliminated: true }),
  team(T(53, "CSK", "Chennai Super Kings"), { points: 12, remaining: 3, max_points: 18 }),
  team(SRH, { points: 14, remaining: 2, max_points: 18 }),
];

describe("scenarios", () => {
  it("sorts by top-4 odds with eliminated teams last", () => {
    expect(sortScenarioTeams(SC).map((t) => t.team.short_code)).toEqual(["GT", "RCB", "SRH", "CSK", "DC", "MI"]) // equal odds → more points first;
  });

  it("explains what a team needs in plain words", () => {
    // Rivals' maxes: 20, 18, 18, 14, 12 → 4th best is 14, so 15+ pts is safe.
    expect(whatTeamNeeds(SC[0], SC).text).toBe("3 left, max 20 pts. Win 1 of 3 (16 pts) to qualify without needing NRR.");
    expect(whatTeamNeeds(SC[3], SC)).toEqual({ tone: "eliminated", text: "MI are out: even 12 pts can't reach the top 4." });
    expect(whatTeamNeeds(team(GT, { clinched_top4: true, p_top2_incl_ties: 0.62 }), SC).text).toMatch(/through to the playoffs\. Top 2 in 62%/);
  });

  it("shows bars with both probabilities and an eliminated badge", () => {
    render(<ScenarioTeamList teams={SC} />);
    expect(screen.getByRole("img", { name: "Top 4: 88% on points alone, up to >99% if net run rate breaks ties" })).toBeInTheDocument();
    const mi = screen.getByTestId("scenario-MI");
    expect(within(mi).getByText("Eliminated")).toBeInTheDocument();
    expect(within(mi).getByRole("img", { name: "Top 4: 0%" })).toBeInTheDocument();
  });

  it("marks numbers as approximate while a pick recomputes", () => {
    render(<ScenarioTeamList teams={SC} pending />);
    expect(screen.getByRole("list")).toHaveAttribute("aria-busy", "true");
    expect(screen.getAllByText("≈").length).toBeGreaterThan(0);
  });
});

describe("FixturePicker", () => {
  const fixtures: ScenarioFixture[] = [
    { match_id: 1529300, match_number: 57, date: "2026-05-13", team1_id: 50, team2_id: 46, actual_winner_id: 46, picked_winner_id: null },
  ];
  const byId = new Map<number, TeamRef>([
    [50, T(50, "KKR", "Kolkata Knight Riders")],
    [46, RCB],
  ]);

  it("picks, toggles off, and marks the actual result", async () => {
    const onPick = vi.fn();
    const { rerender } = render(<FixturePicker fixtures={fixtures} teamsById={byId} picks={new Map()} onPick={onPick} />);
    const group = screen.getByRole("group", { name: /Match 57: KKR v RCB/ });
    const [kkr, rcb] = within(group).getAllByRole("button");
    expect(kkr).toHaveAttribute("aria-pressed", "false");
    expect(within(rcb).getByText("actual")).toBeInTheDocument();
    await userEvent.click(kkr);
    expect(onPick).toHaveBeenLastCalledWith(1529300, 50);

    rerender(<FixturePicker fixtures={fixtures} teamsById={byId} picks={new Map([[1529300, 50]])} onPick={onPick} />);
    const kkrOn = screen.getAllByRole("button")[0];
    expect(kkrOn).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(kkrOn);
    expect(onPick).toHaveBeenLastCalledWith(1529300, null);
  });
});
