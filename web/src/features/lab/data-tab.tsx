"use client";

import { ShieldCheck } from "lucide-react";

import { StatTile } from "@/components/data/stat-tile";
import { ROLE_THEME, type Role } from "@/lib/tokens";

import { BarsChart, C, HistogramChart } from "./charts";
import { ROLE_STYLE, SplitStrip, roleFor, type SeasonRole } from "./diagrams";
import { fmtCompact, fmtInt, fmtNum, fmtPct } from "./format";
import { histPeak, targetInsight } from "./insights";
import type { Telemetry } from "./types";
import { Grid, KeyValues, LabCard, ProseCard, SectionTitle, Term } from "./ui";

const ROLE_FILL: Record<SeasonRole, string> = {
  train: "var(--chart-1)",
  inner: "color-mix(in oklch, var(--chart-1) 55%, var(--surface-2))",
  validate: "var(--chart-2)",
  test: "var(--chart-4)",
  walkforward: "var(--chart-3)",
  unused: "var(--surface-3)",
};

/** Role of a season in the final protocol (test model + walk-forward). */
function finalRole(y: number, t: Telemetry): SeasonRole {
  const { testSeason, wfSeason, cvSeasons } = t.protocol;
  if (wfSeason && y === wfSeason) return "walkforward";
  if (testSeason && y === testSeason) return "test";
  if (cvSeasons.includes(y)) return "validate";
  return testSeason ? roleFor(y, testSeason, "test") : "train";
}

export function DataTab({ t }: { t: Telemetry }) {
  const tg = t.data.target;
  const seasons = t.data.rowsBySeason;
  const recent = seasons.filter((s) => s.year >= 2023).reduce((a, s) => a + s.n, 0);
  const peak = tg ? histPeak(tg.hist) : null;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Player-match rows" value={t.data.rows} format={fmtCompact} hint="one row = one player in one match" />
        <StatTile label="Matches" value={t.data.matches} format={fmtInt} hint={seasons.length ? `${seasons[0].year}–${seasons.at(-1)!.year}` : undefined} />
        <StatTile label="Players" value={t.data.players} format={fmtInt} />
        <StatTile label="Average target" value={tg?.mean ?? null} format={(n) => fmtNum(n, 1)} unit="pts" hint={tg?.sd ? `σ ${fmtNum(tg.sd, 1)} pts` : undefined} />
      </div>

      <LabCard
        title="Which seasons train, validate and test"
        caption="Each row is one model fit; each square a season. The model is always trained only on seasons before the one it is scored on."
        learn={{
          concept: (
            <>
              Time-ordered data can&apos;t be shuffled into random folds: that would let the model learn from 2024 to predict 2021. <Term id="rolling-origin">Rolling-origin CV</Term> trains on
              everything before season Y and scores Y. Inside each training window, the last season is held back for <Term id="early-stopping">early stopping</Term> (
              <Term id="inner-validation">inner validation</Term>).
            </>
          ),
          read: "Violet = trained on; hatched = inner validation used to pick the number of trees; gold = the CV fold being scored (used to tune hyper-parameters); green = the test season, scored exactly once; blue = walk-forward.",
          good: "No coloured square to the right of the scored season, and the test season never used for any decision.",
          ours: `${t.protocol.cvSeasons.length} CV folds (${t.protocol.cvSeasons.join(", ")}) chose the settings; ${t.protocol.testSeason ?? "?"} is the one-shot test; ${t.protocol.wfSeason ?? "?"} is replayed walk-forward in blocks of ${t.protocol.wfBlock ?? "?"} matches.`,
        }}
      >
        <SplitStrip protocol={t.protocol} years={seasons.map((s) => s.year)} />
      </LabCard>

      <Grid cols={2}>
        <LabCard
          title="Rows per season"
          caption="How many player-match rows each season contributes, coloured by its role in the final protocol."
          table={{ columns: ["Season", "Rows", "Role"], rows: seasons.map((s) => [s.year, s.n, ROLE_STYLE[finalRole(s.year, t)].label]) }}
          legend={
            <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              {(["train", "validate", "test", "walkforward"] as const).map((k) => (
                <li key={k} className="inline-flex items-center gap-1.5">
                  <span className="size-2.5 rounded-sm" style={{ background: ROLE_FILL[k] }} />
                  {k === "validate" ? "CV fold (also trained on later)" : ROLE_STYLE[k].label}
                </li>
              ))}
            </ul>
          }
          learn={{
            concept: "More rows = more examples to learn from. Seasons with more matches (74 since 2022) or the impact-player rule (an extra player per side since 2023) add rows.",
            read: "Bar height = rows. Colour = the season's role when the final model is evaluated.",
            good: "Enough rows in recent seasons, because recent cricket is the most relevant. Recency weighting further up-weights them.",
            ours: `${fmtPct(t.data.rows ? recent / t.data.rows : null)} of all rows are from 2023 onwards (the impact-player era).`,
          }}
        >
          <BarsChart data={seasons.map((s) => ({ season: String(s.year), rows: s.n, role: finalRole(s.year, t) }))} xKey="season" series={[{ key: "rows", label: "Rows", color: C.model }]} colorOf={(r) => ROLE_FILL[r.role as SeasonRole]} height={240} />
        </LabCard>

        {tg && (
          <LabCard
            title="The target: Dream11 points per player-match"
            caption="Distribution of the number the model learns to predict, across all rows."
            table={{ columns: ["Points from", "to", "Rows"], rows: tg.hist.map((b) => [b.lo, b.hi, b.n]) }}
            learn={{
              concept: "The target is skewed: most players score modestly, a few score 100+. A model that minimises squared error chases the mean, which the long tail pulls up; quantile heads describe the spread instead.",
              read: "Each bar counts rows whose points fall in that range. Dashed lines mark the mean and median.",
              good: "Understanding the shape tells you which loss to use and why MAE will never be tiny: big hauls are inherently unpredictable.",
              ours: `${targetInsight(tg)}${peak ? ` The most common range is ${fmtNum(peak.lo, 0)}–${fmtNum(peak.hi, 0)} points.` : ""}`,
            }}
          >
            <HistogramChart
              bins={tg.hist}
              name="Rows"
              refX={[
                ...(tg.mean !== null ? [{ x: tg.mean, label: "mean" }] : []),
                ...(tg.p50 !== null ? [{ x: tg.p50, label: "median" }] : []),
              ]}
            />
          </LabCard>
        )}

        {tg && tg.byRole.length > 0 && (
          <LabCard
            title="Target by role"
            caption="Average points and spread for each Dream11 role."
            table={{ columns: ["Role", "Mean", "SD", "Rows"], rows: tg.byRole.map((r) => [r.role, fmtNum(r.mean, 1), fmtNum(r.sd, 1), r.n ?? "–"]) }}
            learn={{
              concept: "Roles earn points differently (bowlers via wickets, batters via runs), so the model gets role as a feature and residuals are checked per role.",
              read: "Bar = mean points. The table view adds standard deviation (how volatile the role is) and row counts.",
              good: "A role with higher SD is harder to predict; expect larger MAE there.",
              ours: (() => {
                const top = tg.byRole.reduce((m, r) => ((r.mean ?? 0) > (m.mean ?? 0) ? r : m), tg.byRole[0]);
                const vol = tg.byRole.reduce((m, r) => ((r.sd ?? 0) > (m.sd ?? 0) ? r : m), tg.byRole[0]);
                return `${top.role} average the most (${fmtNum(top.mean, 1)} pts); ${vol.role} are the most volatile (SD ${fmtNum(vol.sd, 1)}).`;
              })(),
            }}
          >
            <BarsChart
              data={tg.byRole.map((r) => ({ role: r.role, mean: r.mean }))}
              xKey="role"
              series={[{ key: "mean", label: "Mean points", color: C.model }]}
              colorOf={(r) => ROLE_THEME[r.role as Role]?.hex ?? C.model}
              yFmt={(n) => fmtNum(n, 0)}
              height={220}
            />
          </LabCard>
        )}

        {tg && (
          <LabCard title="Target percentiles" caption="Where the points fall: 10% of rows score below p10, 90% below p90.">
            <KeyValues
              items={[
                { k: "Minimum", v: fmtNum(tg.min, 0) },
                { k: "p10", v: fmtNum(tg.p10, 0) },
                { k: "p25", v: fmtNum(tg.p25, 0) },
                { k: "Median (p50)", v: fmtNum(tg.p50, 0) },
                { k: "Mean", v: fmtNum(tg.mean, 1) },
                { k: "p75", v: fmtNum(tg.p75, 0) },
                { k: "p90", v: fmtNum(tg.p90, 0) },
                { k: "Maximum", v: fmtNum(tg.max, 0) },
              ]}
            />
          </LabCard>
        )}
      </Grid>

      <SectionTitle sub="The single most important property of a sports model: it must not peek at the future.">Leakage rules</SectionTitle>
      <ProseCard
        title={
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck aria-hidden className="size-4 text-positive" /> Point-in-time features
          </span>
        }
      >
        <p>
          <Term id="data-leakage">Data leakage</Term> makes offline numbers look great and live predictions disappoint. Every feature here is <Term id="point-in-time">point-in-time</Term>: computed
          only from matches that finished before the toss of the match being predicted.
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Form and craft (rolling means, strike rates, economies) use strictly earlier matches; this match&apos;s scorecard is never an input.</li>
          <li>Season aggregates count only the season&apos;s matches already played.</li>
          <li>Venue and opponent history use earlier matches at that venue / against that team, shrunk toward the league average when the sample is small.</li>
          <li>Matchups use the announced XIs (known at the toss), never who actually batted or bowled.</li>
          <li>Conditions: toss result, batting first, day/night and forecast weather, all known at the toss.</li>
          <li>Evaluation mirrors this: each scored season is predicted by a model trained only on earlier seasons.</li>
        </ul>
        <p className="text-muted-foreground">
          Guard-rail: an automated test perturbs every outcome of a cut-off match and all later matches, and requires that match&apos;s features to stay identical.
        </p>
      </ProseCard>
    </div>
  );
}
