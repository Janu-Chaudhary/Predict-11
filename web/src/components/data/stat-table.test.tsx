import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { StatTable, sortRows, type StatColumn } from "./stat-table";

type R = { name: string; pts: number | null };
const rows: R[] = [
  { name: "B", pts: 10 },
  { name: "A", pts: null },
  { name: "C", pts: 30 },
];
const cols: StatColumn<R>[] = [
  { key: "name", header: "Player", value: (r) => r.name, align: "left", sortable: true },
  { key: "pts", header: "Pts", value: (r) => r.pts, sortable: true },
];

describe("sortRows", () => {
  it("sorts numbers and keeps empties last in both directions", () => {
    expect(sortRows(rows, cols[1], "desc").map((r) => r.name)).toEqual(["C", "B", "A"]);
    expect(sortRows(rows, cols[1], "asc").map((r) => r.name)).toEqual(["B", "C", "A"]);
  });
});

describe("StatTable", () => {
  it("toggles sort with aria-sort on the header", async () => {
    const user = userEvent.setup();
    render(<StatTable caption="Test" columns={cols} rows={rows} rowKey={(r) => r.name} />);
    const header = screen.getByRole("columnheader", { name: /pts/i });
    expect(header).toHaveAttribute("aria-sort", "none");
    await user.click(within(header).getByRole("button"));
    expect(header).toHaveAttribute("aria-sort", "descending");
    const firstCell = screen.getAllByRole("row")[1].querySelector("td");
    expect(firstCell).toHaveTextContent("C");
    await user.click(within(header).getByRole("button"));
    expect(header).toHaveAttribute("aria-sort", "ascending");
  });
});
