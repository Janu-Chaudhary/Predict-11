/** URL state of the Lab (plain module: usable from server components and client code). */
export const LAB_TABS = ["overview", "data", "features", "training", "evaluation", "explain", "predictions", "compare", "glossary"] as const;
export type LabTab = (typeof LAB_TABS)[number];

export type LabState = {
  tab: LabTab;
  run: string | null;
  phase: "test" | "walkforward";
  match: number | null;
  player: string | null;
  a: string | null;
  b: string | null;
};

export function labHref(state: LabState, patch: Partial<LabState> = {}): string {
  const s = { ...state, ...patch };
  const qs = new URLSearchParams();
  if (s.tab !== "overview") qs.set("tab", s.tab);
  if (s.run) qs.set("run", s.run);
  if (s.phase !== "test") qs.set("phase", s.phase);
  if (s.match !== null) qs.set("match", String(s.match));
  if (s.player) qs.set("player", s.player);
  if (s.a) qs.set("a", s.a);
  if (s.b) qs.set("b", s.b);
  const q = qs.toString();
  return `/lab${q ? `?${q}` : ""}`;
}
