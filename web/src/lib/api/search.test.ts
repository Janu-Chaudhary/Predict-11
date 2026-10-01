import { afterEach, describe, expect, it, vi } from "vitest";

import { parsePlayerSearch, searchPlayers } from "./search";

describe("parsePlayerSearch", () => {
  it("accepts arrays and common envelopes, dropping malformed hits", () => {
    expect(parsePlayerSearch([{ id: 1, name: "A", team: "CSK" }])).toEqual([{ id: "1", name: "A", team: "CSK", role: undefined }]);
    expect(parsePlayerSearch({ results: [{ player_id: "p", full_name: "B" }, { nope: 1 }] })).toEqual([
      { id: "p", name: "B", team: undefined, role: undefined },
    ]);
    expect(parsePlayerSearch(null)).toEqual([]);
  });
});

describe("searchPlayers", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("maps 404 to unavailable instead of throwing", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 404 })));
    await expect(searchPlayers("koh")).resolves.toMatchObject({ status: "unavailable" });
  });

  it("maps network failure to unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("fetch failed"))));
    await expect(searchPlayers("koh")).resolves.toMatchObject({ status: "unavailable" });
  });

  it("returns parsed hits on 200", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ items: [{ id: "v1", name: "V Kohli", team: "RCB" }] })));
    await expect(searchPlayers("koh")).resolves.toEqual({ status: "ok", hits: [{ id: "v1", name: "V Kohli", team: "RCB", role: undefined }] });
  });
});
