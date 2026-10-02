import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

import { curveRows, Waterfall } from "./charts";
import { improved } from "./compare-tab";
import { roleFor } from "./diagrams";
import { withRemainder } from "./explain-tab";
import { filterFeatures, shares } from "./features-tab";
import { SAMPLE_TELEMETRY_WIRE } from "./fixtures";
import { fmtSigned, verdict } from "./format";
import { GlossaryTab, searchGlossary } from "./glossary-tab";
import { GLOSSARY, GLOSSARY_BY_ID } from "./glossary";
import { captureRatio, coverageInsight, curveInsight, pairInsight, reliabilityInsight, tuningInsight } from "./insights";
import { LabView, pickRun } from "./lab-view";
import { searchMatches } from "./match-picker";
import { explanation, keyFor, matchDetail, matchRows, phaseOf, runs, telemetry } from "./normalize";
import { overlap, xiToPitch } from "./predictions-tab";
import { parseLabState } from "./state";
import type { RunSummary } from "./types";
import { LabProvider, MetricTile, labHref, type LabState } from "./ui";

const T = telemetry(SAMPLE_TELEMETRY_WIRE);
const STATE: LabState = parseLabState({});

function wrap(ui: ReactNode, state: LabState = STATE, qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
  return render(
    <QueryClientProvider client={qc}>
      <LabProvider value={state}>{ui}</LabProvider>
    </QueryClientProvider>,
  );
}

describe("telemetry normaliser", () => {
  it("tolerates an empty or junk payload", () => {
    for (const v of [{}, null, "x", [], { evaluations: "nope", features: 3, curves: { final: { mean: {} } } }]) {
      const t = telemetry(v);
      expect(t.features).toEqual([]);
      expect(t.evaluations).toEqual([]);
      expect(t.curves).toEqual({});
      expect(t.shap).toBeNull();
      expect(t.data.target).toBeNull();
    }
  });

  it("reads the sample fixture", () => {
    expect(T.version).toBe("fixture-run");
    expect(T.features.map((f) => f.name)).toEqual(["ewm_5", "mean_5", "bats_first"]); // nameless entry dropped
    expect(T.data.rowsBySeason.map((r) => r.year)).toEqual([2023, 2024, 2025, 2026]);
    expect(T.data.target?.hist).toHaveLength(2); // bin with a bad edge dropped
    expect(T.data.target?.byRole.map((r) => r.role)).toEqual(["WK", "BOWL"]);
    // evaluations ordered cv → test → walk-forward
    expect(T.evaluations.map((e) => e.label)).toEqual(["CV 2024", "Test 2025", "Walk-forward 2026"]);
    const cv = T.evaluations[0].summary;
    expect(cv.mae).toEqual({ model: null, baseline: null, diff: null, ci: [null, null] });
    expect(T.perMatch.test?.rows).toHaveLength(1);
    expect(T.calibration.test?.coverage.inside80).toBe(0.76);
    expect(T.calibration.walkforward).toBeUndefined();
    expect(T.residuals.test?.byRole.map((r) => r.label)).toEqual(["WK", "BOWL"]);
    expect(T.shap?.dependence.ewm_5).toHaveLength(3);
    expect(T.environment).toEqual({ lightgbm: "4.7.0", cpu_count: 8 });
    expect(T.correlations?.features).toEqual(["ewm_5", "mean_5"]);
  });

  it("parses phase keys", () => {
    expect(phaseOf("test:2025")).toEqual({ kind: "test", season: 2025, label: "Test 2025" });
    expect(phaseOf("walkforward:2026").label).toBe("Walk-forward 2026");
    expect(phaseOf("cv:2020").kind).toBe("cv");
    expect(keyFor({ "test:2025": 1 }, "test")).toBe("test:2025");
    expect(keyFor({}, "test")).toBeNull();
  });

  it("reads runs, matches, match detail and explanations", () => {
    const r = runs([{ version: "v1", is_latest: true, has_telemetry: true, test: { key: "test:2025", mae: { model: 30, baseline: 33, diff: -3, ci95: [-4, -2] } } }, {}]);
    expect(r[0].test?.mae.diff).toBe(-3);
    expect(r[1].version).toBe("unknown");
    const m = matchRows([{ info: { match_id: 5, team1: { name: "Mumbai Indians", code: "MI" } }, phase: "walkforward", n_players: 22 }]);
    expect(m[0]).toMatchObject({ phase: "walkforward", nPlayers: 22, info: { matchId: 5, team1: { code: "MI" }, team2: null } });
    const d = matchDetail({ players: [{ player_id: "a", role: "XX" }], xi: { model: { picks: [{ player_id: "a", multiplier: 2 }], captain: "a" } } });
    expect(d.players[0].role).toBe("BAT");
    expect(d.xi.model?.captain).toBe("a");
    expect(d.xi.hindsight).toBeNull();
    const e = explanation({ base_value: 30, prediction: 41, contributions: [{ feature: "x", shap: 11, value: null }, { feature: "bad" }] });
    expect(e.contributions).toHaveLength(1);
  });
});

describe("formatting and insights", () => {
  it("verdicts respect direction and the CI", () => {
    expect(verdict({ model: 1, baseline: 0, diff: 1, ci: [0.5, 1.5] }, true)).toBe("better");
    expect(verdict({ model: 30, baseline: 33, diff: -3, ci: [-4, -2] }, false)).toBe("better");
    expect(verdict({ model: 1, baseline: 0, diff: 1, ci: [-0.5, 2] }, true)).toBe("tie");
    expect(verdict({ model: 1, baseline: 0, diff: null, ci: [null, null] }, true)).toBe("unknown");
    expect(fmtSigned(-2.345, 1)).toBe("−2.3");
    expect(fmtSigned(0, 1)).toBe("±0.0");
  });

  it("explains results from the numbers", () => {
    const test = T.evaluations.find((e) => e.kind === "test")!;
    expect(pairInsight(test.summary.bestXi, "bestXi", "Test 2025")).toMatch(/reliably better/);
    expect(pairInsight(T.evaluations[2].summary.bestXi, "bestXi", "WF")).toMatch(/could be luck/);
    expect(coverageInsight(0.81)).toMatch(/well calibrated/);
    expect(coverageInsight(0.7)).toMatch(/too narrow/);
    expect(reliabilityInsight(T.calibration.test!)).toMatch(/over-predicts/);
    const c = curveInsight(T.curves.final.mean, "mean");
    expect(c).toMatch(/best at round 300/);
    expect(c).toMatch(/overfit/);
    expect(tuningInsight(T.tuning, T.chosenParams)).toMatch(/2 settings were tried.*best setting is the one used/);
    expect(captureRatio(800, 700, 1200)).toBeCloseTo(0.2);
  });
});

describe("helpers", () => {
  it("round-trips URL state and rejects junk", () => {
    const s = parseLabState({ tab: "predictions", run: "lgbm-1", phase: "walkforward", match: "123", player: "ab12" });
    expect(s).toMatchObject({ tab: "predictions", run: "lgbm-1", phase: "walkforward", match: 123, player: "ab12" });
    expect(parseLabState(Object.fromEntries(new URLSearchParams(labHref(s).split("?")[1])))).toEqual(s);
    expect(parseLabState({ tab: "nope", run: "../x", match: "12a", player: "<script>" })).toEqual(STATE);
    expect(labHref(STATE)).toBe("/lab");
  });

  it("picks the run, folds SHAP remainders, filters features and matches", () => {
    const rs = [{ version: "a", isLatest: false }, { version: "b", isLatest: true }] as RunSummary[];
    expect(pickRun(rs, "a")?.version).toBe("a");
    expect(pickRun(rs, "zzz")?.version).toBe("b");
    expect(pickRun([], null)).toBeNull();
    const ex = T.shap!.examples[0];
    const all = withRemainder(ex);
    expect(all.at(-1)).toMatchObject({ feature: "all other features", shap: 5 });
    expect(all.reduce((s, c) => s + c.shap, ex.base!)).toBeCloseTo(ex.pred!);
    expect(filterFeatures(T.features, "last-5", new Set()).map((f) => f.name)).toEqual(["mean_5"]);
    expect(filterFeatures(T.features, "", new Set(["Conditions"])).map((f) => f.name)).toEqual(["bats_first"]);
    expect(shares(T.features, "gain").get("ewm_5")).toBeCloseTo(0.6);
    const ms = matchRows([{ info: { match_id: 1, date: "2025-03-22", team1: { name: "Kolkata Knight Riders", code: "KKR" }, team2: { name: "Mumbai Indians", code: "MI" }, venue: "Eden Gardens" } }]);
    expect(searchMatches(ms, "kkr eden")).toHaveLength(1);
    expect(searchMatches(ms, "csk")).toHaveLength(0);
    expect(roleFor(2019, 2020, "validate")).toBe("inner");
    expect(roleFor(2021, 2020, "validate")).toBe("unused");
    expect(curveRows({ train: [3, 2, 1], valid: [4, 3, 3], metric: "l2", bestIter: 2, iters: 201 }).map((r) => r.iter)).toEqual([1, 101, 201]);
  });

  it("compares runs and XIs", () => {
    expect(improved({ phase: "test", metric: "mae", a: 34, b: 33, delta: -1, higherIsBetter: false })).toBe(true);
    expect(improved({ phase: "test", metric: "p10_p90_coverage", a: 0.7, b: 0.78, delta: 0.08, higherIsBetter: true })).toBe(true);
    expect(improved({ phase: "test", metric: "p10_p90_coverage", a: 0.79, b: 0.9, delta: 0.11, higherIsBetter: true })).toBe(false);
    const xi = { picks: [{ playerId: "a", name: "A B", imageUrl: null, team: "MI", role: "BOWL" as const, multiplier: 2, value: 50, actual: 61.5, points: 123 }, { playerId: "b", name: "C", imageUrl: null, team: "MI", role: "WK" as const, multiplier: 1, value: 10, actual: 3, points: 3 }], captain: "a", viceCaptain: null, actualPoints: 126, selectedOn: 110 };
    const pitch = xiToPitch(xi);
    expect(pitch.map((p) => p.id)).toEqual(["b", "a"]); // role order WK first
    expect(pitch[1]).toMatchObject({ captain: true, projection: { median: 62 } });
    expect(overlap(xi, { ...xi, picks: xi.picks.slice(0, 1) })).toBe(1);
  });

  it("glossary ids are unique and every related link resolves", () => {
    expect(new Set(GLOSSARY.map((g) => g.id)).size).toBe(GLOSSARY.length);
    for (const g of GLOSSARY) for (const r of g.related ?? []) expect(GLOSSARY_BY_ID[r], `${g.id} → ${r}`).toBeDefined();
    expect(searchGlossary("pinball", null).map((g) => g.id)).toContain("pinball-loss");
    expect(searchGlossary("", "Explainability").every((g) => g.category === "Explainability")).toBe(true);
  });
});

describe("components", () => {
  it("MetricTile shows model, baseline and an accessible CI", () => {
    wrap(<MetricTile metric="mae" pair={{ model: 33.5, baseline: 35.8, diff: -2.3, ci: [-3.1, -1.5] }} />);
    expect(screen.getByText("33.50")).toBeInTheDocument();
    expect(screen.getByText(/vs 35.80 baseline/)).toBeInTheDocument();
    expect(screen.getByText("Model better")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /95% interval −3.10 to −1.50/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /MAE per player/ })).toHaveAttribute("href", "/lab?tab=glossary#term-mae");
  });

  it("Waterfall ends at base + Σ SHAP", () => {
    wrap(<Waterfall base={38} contribs={[{ feature: "ewm_5", value: 70, shap: 15 }, { feature: "x", value: null, shap: -3 }]} />);
    expect(screen.getByText("Prediction").parentElement).toHaveTextContent("50.0");
  });

  it("Glossary renders anchored entries", () => {
    const { container } = wrap(<GlossaryTab />);
    expect(container.querySelector("#term-shap")).not.toBeNull();
    expect(screen.getAllByText("Pinball (quantile) loss").length).toBeGreaterThan(0);
  });

  it("LabView shows the honest no-run state and no numbers", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(["lab", "runs"], []);
    wrap(<LabView state={STATE} />, STATE, qc);
    expect(screen.getByText(/No training run yet: the model is training/)).toBeInTheDocument();
    expect(screen.queryByText(/Headline results/)).toBeNull();
    expect(screen.getByText("What the model predicts, and when")).toBeInTheDocument();
  });
});
