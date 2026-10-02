import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import { WANKHEDE_FIXTURE } from "./fixtures";
import type { VenueCard } from "./types";
import { VenueCardView } from "./venue-card";

beforeAll(() => {
  // Recharts' ResponsiveContainer needs ResizeObserver, which jsdom lacks.
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

describe("VenueCardView", () => {
  it("shows par 2023+ next to all-time with the inflation note", () => {
    render(<VenueCardView venue={WANKHEDE_FIXTURE} />);
    expect(screen.getByRole("heading", { level: 1, name: "Wankhede Stadium" })).toBeInTheDocument();

    const par = screen.getByRole("table", { name: /par scores and results at this venue/i });
    const row = within(par).getByRole("row", { name: /par 1st innings/i });
    // 196.7 → 197 (2023+), 173.4 → 173 (all-time), change +24
    expect(within(row).getAllByRole("cell").map((c) => c.textContent)).toEqual(["197", "173", "▲ +24"]);
    expect(within(par).getByRole("columnheader", { name: /2023\+/ })).toHaveTextContent("n=27");
    expect(screen.getByText(/scoring has inflated since 2022/i)).toBeInTheDocument();
    // Recency-weighted par is offered as the alternative.
    expect(screen.getByText("190")).toBeInTheDocument();
  });

  it("renders the headline tiles, toss split and phase bars", () => {
    render(<VenueCardView venue={WANKHEDE_FIXTURE} />);
    expect(screen.getByText("Chase win 2023+").nextElementSibling).toHaveTextContent("56%");
    expect(screen.getByRole("img", { name: /2023\+: toss winners chose to field 26 times and bat 2 times out of 28/i })).toBeInTheDocument();
    const phases = screen.getByRole("figure", { name: /run rate by phase/i });
    expect(phases).toHaveAccessibleName(expect.stringContaining("Powerplay 9.73 runs per over since 2023 vs 8.04 all-time"));
  });

  it("offers a table view of the phase chart", async () => {
    render(<VenueCardView venue={WANKHEDE_FIXTURE} />);
    const section = screen.getByRole("heading", { name: "Phase run rates" }).closest("section")!;
    await userEvent.click(within(section).getByRole("button", { name: "Table" }));
    const table = within(section).getByRole("table");
    expect(within(table).getByRole("row", { name: /death/i })).toHaveTextContent("11.18");
  });

  it("lists record totals and venue leaders linking to player profiles", () => {
    render(<VenueCardView venue={WANKHEDE_FIXTURE} />);
    const highest = screen.getByRole("region", { name: "Highest totals" });
    expect(within(highest).getAllByRole("listitem")[0]).toHaveTextContent("249/4");
    const lowest = screen.getByRole("region", { name: "Lowest totals" });
    // All-out totals print without "/10".
    expect(within(lowest).getAllByRole("listitem")[0]).toHaveTextContent(/67\s*15\.2 ov/);
    const scorers = screen.getByRole("region", { name: "Top run-scorers here" });
    expect(within(scorers).getByRole("link", { name: /RG Sharma/ })).toHaveAttribute("href", "/players/740742ef");
  });

  it("keeps labelled slots for pace vs spin and dew", () => {
    render(<VenueCardView venue={WANKHEDE_FIXTURE} />);
    expect(screen.getByRole("heading", { name: "Pace vs spin wickets" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dew factor" })).toBeInTheDocument();
  });

  it("flags a small 2023+ sample and survives missing numbers", () => {
    const thin: VenueCard = {
      ...WANKHEDE_FIXTURE,
      recent: { matches: 2, avg_first_innings: 179, median_first_innings: null, avg_second_innings: null, chase_win_pct: null, bat_first_win_pct: null },
      par_weighted: null,
      highest_totals: [],
      top_wicket_takers: [],
    };
    render(<VenueCardView venue={thin} />);
    expect(screen.getByText(/only 2 completed matches here since 2023/i)).toBeInTheDocument();
    expect(screen.getByText("No completed innings recorded here.")).toBeInTheDocument();
    expect(screen.getByText("No wickets recorded at this ground yet.")).toBeInTheDocument();
  });

  it("shows the ground photo hero with its Commons credit when the venue has one", () => {
    const withPhoto: VenueCard = {
      ...WANKHEDE_FIXTURE,
      image_url: "/venues/154-1600.webp",
      thumb_url: "/venues/154-640.webp",
      image_credit: {
        author: "G patkar",
        license: "CC BY-SA 3.0",
        license_url: "https://creativecommons.org/licenses/by-sa/3.0",
        file_page: "https://commons.wikimedia.org/wiki/File:Wankhede_Stadium.jpg",
      },
    };
    const { container } = render(<VenueCardView venue={withPhoto} />);
    expect(screen.getByRole("heading", { level: 1, name: "Wankhede Stadium" })).toBeInTheDocument();
    expect(container.querySelector('img[src="/venues/154-1600.webp"]')).not.toBeNull();
    // Credit is shown twice (desktop pill + mobile line); both link the file page and licence.
    const authors = screen.getAllByRole("link", { name: "G patkar" });
    expect(authors[0]).toHaveAttribute("href", "https://commons.wikimedia.org/wiki/File:Wankhede_Stadium.jpg");
    expect(screen.getAllByRole("link", { name: "CC BY-SA 3.0" })[0]).toHaveAttribute("href", "https://creativecommons.org/licenses/by-sa/3.0");
    expect(screen.getByRole("link", { name: /all venues/i })).toHaveAttribute("href", "/venues");
  });

  it("keeps the text header when there is no photo", () => {
    const { container } = render(<VenueCardView venue={WANKHEDE_FIXTURE} />);
    expect(container.querySelector("img[src^='/venues/']")).toBeNull();
    expect(screen.queryByText(/via Wikimedia Commons/)).toBeNull();
  });
});
