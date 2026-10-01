import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next-themes", () => ({ useTheme: () => ({ resolvedTheme: "dark" }) }));

import { MatchCard } from "./match-card";
import type { HomeState } from "./types";

const t = (id: number, code: string, name: string) => ({ id, short_code: code, name });
const state: HomeState = {
  phase: "off_season",
  now: "2026-10-02T12:00:00+05:30",
  hero: "C",
  hero_match_id: 1535465,
  hero_reason: "Off-season",
  next_fixture: null,
  last_match: {
    id: 1535465,
    date: "2026-05-31",
    season: 2026,
    title: "Final",
    stage: "Final",
    match_number: null,
    venue: { id: 171, name: "Narendra Modi Stadium", city: "Ahmedabad" },
    team1: t(56, "GT", "Gujarat Titans"),
    team2: t(46, "RCB", "Royal Challengers Bengaluru"),
    winner_id: 46,
    result: "RCB won by 5 wickets",
    scores: [
      { innings: 1, team_id: 56, runs: 155, wickets: 8, overs: "20" },
      { innings: 2, team_id: 46, runs: 161, wickets: 5, overs: "18" },
    ],
  },
  season: {
    year: 2026,
    champion: t(46, "RCB", "Royal Challengers Bengaluru"),
    runner_up: t(56, "GT", "Gujarat Titans"),
    final_match_id: 1535465,
    next_season: "IPL 2027 starts ~March",
  },
};

describe("MatchCard", () => {
  it("off-season: next season hint, champion, final result and table/records links", () => {
    render(<MatchCard state={state} />);
    expect(screen.getByText("IPL 2027 starts ~March")).toBeInTheDocument();
    expect(screen.getByText("Champions 2026")).toBeInTheDocument();
    expect(screen.getByText("RCB won by 5 wickets")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /2026 table/ })).toHaveAttribute("href", "/table?season=2026");
    expect(screen.getByRole("link", { name: "Records" })).toHaveAttribute("href", "/records");
    expect(screen.queryByRole("timer")).toBeNull();
  });

  it("pre-match: countdown and one gold Build CTA", () => {
    render(
      <MatchCard
        state={{
          ...state,
          phase: "pre_match",
          next_fixture: {
            id: 7,
            start: new Date(Date.now() + 3 * 3600_000).toISOString(),
            title: "Match 1",
            venue: null,
            team1: t(1, "CSK", "Chennai Super Kings"),
            team2: t(2, "MI", "Mumbai Indians"),
            status: "provisional",
          },
        }}
      />,
    );
    expect(screen.getByRole("timer", { name: "Time to start" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Build my XI/ })).toHaveAttribute("href", "/build");
    expect(screen.getByText("Provisional · XI at toss")).toBeInTheDocument();
  });
});
