"use client";

import { useState } from "react";

import { StatBarChart, StatLineChart } from "@/components/charts/stat-charts";
import { WormChart } from "@/components/charts/worm-chart";
import { ConfidenceBadge } from "@/components/data/confidence-badge";
import { FormStrip } from "@/components/data/form-strip";
import { PlayerRow } from "@/components/data/player-row";
import { CURRENT_SEASON, SeasonSelect } from "@/components/data/season-select";
import { Sparkline } from "@/components/data/sparkline";
import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { StatTile } from "@/components/data/stat-tile";
import { NumberRoll } from "@/components/loaders/number-roll";
import { RowsSkeleton } from "@/components/loaders/page-skeletons";
import { SeamSpin } from "@/components/loaders/seam-spin";
import { StumpsLoader } from "@/components/loaders/stumps-loader";
import { RangeBar } from "@/components/player/range-bar";
import { RoleChip } from "@/components/player/role-chip";
import { TeamBadge, TeamStripe } from "@/components/player/team-badge";
import { SectionHeader } from "@/components/shell/page-header";
import { Button } from "@/components/ui/button";
import { MOCK_XI } from "@/lib/mock";
import { SAMPLE_PLAYER, SAMPLE_POINTS_TABLE, SAMPLE_WORM, type PointsRow } from "@/lib/sample";
import { HISTORICAL_TEAM_CODES, ROLES, TEAM_CODES, getTeam } from "@/lib/tokens";

const signed = (n: number) => (n > 0 ? `+${n.toFixed(2)}` : n.toFixed(2));

const COLUMNS: StatColumn<PointsRow>[] = [
  { key: "pos", header: "#", value: (r) => r.pos, align: "left", sortable: true, defaultDir: "asc", className: "w-10 text-muted-foreground" },
  {
    key: "team",
    header: "Team",
    label: "Team",
    value: (r) => r.team,
    align: "left",
    sticky: true,
    cell: (r) => (
      <span className="flex items-center gap-2">
        <TeamBadge team={r.team} />
        <span className="font-medium max-sm:hidden">{getTeam(r.team).name}</span>
      </span>
    ),
  },
  { key: "p", header: "P", value: (r) => r.p, sortable: true },
  { key: "w", header: "W", value: (r) => r.w, sortable: true },
  { key: "l", header: "L", value: (r) => r.l, sortable: true },
  { key: "nr", header: "NR", value: (r) => r.nr, sortable: true, hideBelow: "sm" },
  { key: "nrr", header: "NRR", value: (r) => r.nrr, sortable: true, cell: (r) => signed(r.nrr) },
  { key: "pts", header: "Pts", value: (r) => r.pts, sortable: true, className: "font-semibold" },
  { key: "form", header: "Form", value: () => null, align: "left", hideBelow: "md", cell: (r) => <FormStrip results={r.form} /> },
];

export function Gallery() {
  const [val, setVal] = useState(612);
  const [season, setSeason] = useState(CURRENT_SEASON);
  return (
    <div className="grid gap-8">
      <section>
        <SectionHeader title="Stat tiles" />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
          <StatTile label="Avg fantasy pts" value={SAMPLE_PLAYER.tiles.avgPts} format={(n) => n.toFixed(1)} delta={{ value: -4.1, label: "vs 2025", format: (n) => n.toFixed(1) }} />
          <StatTile label="Ceiling (p90)" value={SAMPLE_PLAYER.tiles.ceilP90} hint="last 20 inns" />
          <StatTile label="Captain rate" value={SAMPLE_PLAYER.tiles.captainRate} unit="%" />
          <StatTile label="Projected total" value={val} roll hint={<button className="underline" onClick={() => setVal(590 + Math.floor(Math.random() * 60))}>roll</button>} />
        </div>
      </section>

      <section>
        <SectionHeader title="Stat table · sortable, sticky header, scrolls inside the card" action={<SeasonSelect value={season} onValueChange={setSeason} />} />
        <StatTable
          caption="Sample points table"
          columns={COLUMNS}
          rows={SAMPLE_POINTS_TABLE}
          rowKey={(r) => r.team}
          initialSort={{ key: "pos", dir: "asc" }}
          rowLead={(r) =>
            r.pos <= 4 ? <span aria-hidden className={`absolute inset-y-1 left-0 w-[3px] rounded-full ${r.pos <= 2 ? "bg-primary" : "bg-brand"}`} /> : null
          }
          footer={
            <span className="flex flex-wrap gap-x-4 gap-y-1">
              <span className="inline-flex items-center gap-1.5"><span className="h-3 w-[3px] rounded-full bg-primary" /> Qualifier 1</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-3 w-[3px] rounded-full bg-brand" /> Eliminator</span>
            </span>
          }
        />
      </section>

      <div className="grid gap-8 lg:grid-cols-2">
        <section>
          <SectionHeader title="Player rows" />
          <div className="overflow-hidden rounded-xl border border-border bg-card">
            {MOCK_XI.slice(0, 5).map((p) => (
              <PlayerRow
                key={p.id}
                player={p}
                href={null}
                meta={`${p.credits.toFixed(1)} cr · ${p.projection.floor}–${p.projection.ceiling}`}
                stat={{ value: p.projection.median, label: "proj" }}
                className="border-b border-border last:border-b-0"
              />
            ))}
          </div>
        </section>
        <section className="grid content-start gap-4">
          <div>
            <SectionHeader title="Team badges · historical neutral · clash ring" />
            <div className="flex flex-wrap items-center gap-2">
              {TEAM_CODES.map((c) => (
                <TeamBadge key={c} team={c} />
              ))}
              {HISTORICAL_TEAM_CODES.map((c) => (
                <TeamBadge key={c} team={c} />
              ))}
            </div>
            <div className="mt-3 flex items-center gap-3 text-sm">
              <TeamBadge team="MI" size="lg" />
              <span className="text-muted-foreground">v</span>
              <TeamBadge team="DC" size="lg" opponent="MI" side="away" />
              <TeamStripe team="MI" className="h-8" />
              {ROLES.map((r) => (
                <RoleChip key={r} role={r} />
              ))}
            </div>
          </div>
          <div>
            <SectionHeader title="Confidence · form · sparkline" />
            <div className="flex flex-wrap items-center gap-3">
              <ConfidenceBadge n={12} />
              <ConfidenceBadge n={64} />
              <ConfidenceBadge n={812} />
            </div>
            <div className="mt-3 flex flex-wrap items-end gap-6">
              <FormStrip results={["W", "L", "W", "NR", "W"]} />
              <FormStrip scores={SAMPLE_PLAYER.form} max={10} />
              <Sparkline values={SAMPLE_PLAYER.form} label="Fantasy points trend, last 10" />
            </div>
          </div>
          <div>
            <SectionHeader title="Range bar" />
            <div className="grid gap-4 rounded-xl border border-border bg-card p-4">
              <RangeBar range={{ floor: 18, median: 48, ceiling: 96 }} />
              <RangeBar range={{ floor: 12, median: 41, ceiling: 84 }} actual={92} />
              <RangeBar range={{ floor: 22, median: 66, ceiling: 104 }} actual={8} />
            </div>
          </div>
        </section>
      </div>

      <section>
        <SectionHeader title="Loaders" />
        <div className="grid gap-4 md:grid-cols-3">
          <div className="grid min-h-44 place-items-center rounded-xl border border-border bg-card">
            <SeamSpin />
          </div>
          <div className="grid min-h-44 place-items-center gap-3 rounded-xl border border-border bg-card p-4">
            <Button variant="outline" className="h-10 rounded-[10px]">
              <StumpsLoader size={22} label={null} /> Re-optimising…
            </Button>
            <span className="font-condensed text-score-xl">
              <NumberRoll value={val} />
            </span>
          </div>
          <div className="rounded-xl border border-border bg-card p-3">
            <RowsSkeleton rows={3} className="border-0" />
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <WormChart home={SAMPLE_WORM.home} away={{ ...SAMPLE_WORM.away, team: "LSG" }} summary="Sample worm, CSK against LSG." />
        <StatBarChart
          title="Fantasy pts by season"
          summary="Sample: average fantasy points per season, peaking in 2025."
          data={SAMPLE_PLAYER.seasons}
          xKey="season"
          series={[{ key: "pts", label: "Avg pts" }]}
        />
        <StatLineChart
          title="Runs vs projection"
          summary="Sample: runs per season against projection."
          data={SAMPLE_PLAYER.seasons.map((s) => ({ ...s, proj: Math.round(s.runs * 0.92) }))}
          xKey="season"
          series={[
            { key: "runs", label: "Runs" },
            { key: "proj", label: "Projected", dashed: true },
          ]}
        />
      </section>
    </div>
  );
}
