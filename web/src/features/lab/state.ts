import { LAB_TABS, type LabState, type LabTab } from "./ui-state";

export type { LabState, LabTab };

const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);
const VERSION = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const PLAYER = /^[A-Za-z0-9_-]{1,32}$/;

/** URL search params → Lab state; anything malformed falls back to a default. */
export function parseLabState(sp: Record<string, string | string[] | undefined>): LabState {
  const tab = first(sp.tab);
  const run = first(sp.run);
  const match = first(sp.match);
  const player = first(sp.player);
  const a = first(sp.a);
  const b = first(sp.b);
  return {
    tab: (LAB_TABS as readonly string[]).includes(tab ?? "") ? (tab as LabTab) : "overview",
    run: run && VERSION.test(run) ? run : null,
    phase: first(sp.phase) === "walkforward" ? "walkforward" : "test",
    match: match && /^\d{1,12}$/.test(match) ? Number(match) : null,
    player: player && PLAYER.test(player) ? player : null,
    a: a && VERSION.test(a) ? a : null,
    b: b && VERSION.test(b) ? b : null,
  };
}
