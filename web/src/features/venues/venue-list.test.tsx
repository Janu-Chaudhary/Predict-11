import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { VenueSummary } from "./types";
import { VenuePhotoCard } from "./venue-list";

const base: VenueSummary = {
  id: 171,
  name: "Narendra Modi Stadium",
  city: "Ahmedabad",
  matches: 53,
  matches_recent: 30,
  first_season: 2010,
  last_season: 2026,
  par_recent: 191.4,
  par_all_time: 172.2,
  chase_win_pct_recent: 46.7,
};

function renderCard(v: VenueSummary) {
  return render(
    <ul>
      <VenuePhotoCard v={v} recentFrom={2023} />
    </ul>,
  );
}

describe("VenuePhotoCard", () => {
  it("shows the photo, stats and a credit tooltip linking the Commons file page", () => {
    const { container } = renderCard({
      ...base,
      image_url: "/venues/171-1600.webp",
      thumb_url: "/venues/171-640.webp",
      image_credit: { author: "A Cricket Premi", license: "CC BY-SA 4.0", license_url: null, file_page: "https://commons.wikimedia.org/wiki/File:X.jpg" },
    });
    expect(container.querySelector('img[src="/venues/171-640.webp"]')).not.toBeNull();
    expect(screen.getByRole("link", { name: "Narendra Modi Stadium" })).toHaveAttribute("href", "/venues/171");
    const credit = screen.getByRole("link", { name: "Photo: A Cricket Premi, CC BY-SA 4.0 via Wikimedia Commons" });
    expect(credit).toHaveAttribute("href", "https://commons.wikimedia.org/wiki/File:X.jpg");
    const stats = screen.getByRole("listitem");
    expect(within(stats).getByText("Matches").nextElementSibling).toHaveTextContent("53");
  });

  it("falls back to a placeholder without a photo and flags small samples", () => {
    const { container } = renderCard({ ...base, matches_recent: 4 });
    expect(container.querySelector("img")).toBeNull();
    expect(screen.queryByRole("link", { name: /wikimedia commons/i })).toBeNull();
    expect(screen.getByText("n=4")).toBeInTheDocument();
  });
});
