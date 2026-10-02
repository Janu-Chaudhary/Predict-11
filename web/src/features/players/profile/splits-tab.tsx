"use client";

import type { ReactNode } from "react";

import { ConfidenceBadge } from "@/components/data/confidence-badge";
import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { TeamBadge } from "@/components/player/team-badge";
import { cn } from "@/lib/utils";

import { H2H_THRESHOLDS } from "../../h2h/confidence";
import { displayName, fmt, PHASE_LABEL, teamCode } from "../format";
import type { PlayerProfile, Split } from "../types";
import { MetricBar, Panel } from "../ui";
import { BatterTypesTable, BowlerHandsTable } from "./matchup-tables";
import { ProfileLayout } from "./profile-layout";

export function SplitsTab({ p, skill, rail }: { p: PlayerProfile; skill: "bat" | "bowl"; rail: ReactNode }) {
  const batPhases = p.batting_phases.filter((x) => x.balls > 0);
  const bowlPhases = p.bowling_phases.filter((x) => x.balls > 0);
  const srMax = Math.max(200, ...batPhases.map((x) => x.strike_rate ?? 0));
  const econMax = Math.max(12, ...bowlPhases.map((x) => x.economy ?? 0));

  const bat = batPhases.length > 0 && (
    <Panel title="Strike rate by phase" key="bat">
      <div role="list" aria-label="Batting strike rate by phase">
        {batPhases.map((x) => (
          <div role="listitem" key={x.phase}>
            <MetricBar
              label={PHASE_LABEL[x.phase] ?? x.phase}
              value={x.strike_rate}
              max={srMax}
              display={fmt(x.strike_rate, 1)}
              hint={
                <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
                  {fmt(x.runs)} runs off {fmt(x.balls)} balls · {x.outs} outs · boundary {fmt(x.boundary_pct, 1)}%
                  <ConfidenceBadge n={x.balls} thresholds={H2H_THRESHOLDS} showN={false} />
                </span>
              }
            />
          </div>
        ))}
      </div>
    </Panel>
  );
  const bowl = bowlPhases.length > 0 && (
    <Panel title="Economy by phase" key="bowl">
      <div role="list" aria-label="Bowling economy by phase (lower is better)">
        {bowlPhases.map((x) => (
          <div role="listitem" key={x.phase}>
            <MetricBar
              label={PHASE_LABEL[x.phase] ?? x.phase}
              value={x.economy}
              max={econMax}
              tone="primary"
              display={fmt(x.economy, 2)}
              hint={
                <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
                  {x.wickets} wkts in {fmt(x.balls)} balls · dot {fmt(x.dot_pct, 1)}%
                  <ConfidenceBadge n={x.balls} thresholds={H2H_THRESHOLDS} showN={false} />
                </span>
              }
            />
          </div>
        ))}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">Runs per over; lower is better.</p>
    </Panel>
  );

  const since = p.filters.since ?? undefined;
  const season = p.filters.season ?? undefined;
  const types = p.batting.balls > 0 && <BatterTypesTable key="types" id={p.id} name={displayName(p)} since={since} season={season} />;
  const hands = p.bowling.balls > 0 && <BowlerHandsTable key="hands" id={p.id} name={displayName(p)} since={since} season={season} />;

  const phases = [bat, bowl].filter(Boolean).length;
  return (
    <ProfileLayout
      band={phases > 0 && <div className={cn("grid grid-cols-1 gap-4 lg:gap-6", phases === 2 && "xl:grid-cols-2")}>{skill === "bowl" ? [bowl, bat] : [bat, bowl]}</div>}
      main={skill === "bowl" ? [hands, types] : [types, hands]}
      rail={rail}
      footer={
        <div className="grid grid-cols-1 gap-4 lg:gap-6 xl:grid-cols-2">
          <SplitTable title="Venues" caption={`${displayName(p)}: venue splits`} rows={p.venues} skill={skill} />
          <SplitTable title="Against teams" caption={`${displayName(p)}: splits by opponent`} rows={p.vs_teams} skill={skill} teams />
        </div>
      }
    />
  );
}

function SplitTable({ title, caption, rows, skill, teams = false }: { title: string; caption: string; rows: Split[]; skill: "bat" | "bowl"; teams?: boolean }) {
  if (rows.length === 0) return null;
  const name: StatColumn<Split> = {
    key: "name",
    header: teams ? "Opponent" : "Venue",
    value: (r) => r.name,
    align: "left",
    sortable: true,
    sticky: true,
    className: teams ? "max-w-[11rem] sm:max-w-none" : "max-w-[11rem] sm:max-w-none xl:max-w-[12rem] 2xl:max-w-[15rem]",
    cell: (r) =>
      teams ? (
        <span className="inline-flex items-center gap-2">
          <TeamBadge team={teamCode(r.name) ?? ""} />
          <span className="max-sm:sr-only">{r.name}</span>
        </span>
      ) : (
        <span className="block truncate" title={r.name}>
          {r.name}
        </span>
      ),
  };
  const batCols: StatColumn<Split>[] = [
    { key: "runs", header: "Runs", value: (r) => r.batting.runs, sortable: true, cell: (r) => <span className="font-semibold">{fmt(r.batting.runs)}</span> },
    { key: "bf", header: "Balls", value: (r) => r.batting.balls, sortable: true, hideBelow: "sm" },
    { key: "avg", header: "Avg", value: (r) => r.batting.average, sortable: true, cell: (r) => fmt(r.batting.average, 1) },
    { key: "sr", header: "SR", value: (r) => r.batting.strike_rate, sortable: true, cell: (r) => fmt(r.batting.strike_rate, 1) },
  ];
  const bowlCols: StatColumn<Split>[] = [
    { key: "wk", header: "Wkts", value: (r) => r.bowling.wickets, sortable: true, cell: (r) => <span className={skill === "bowl" ? "font-semibold" : ""}>{r.bowling.wickets}</span> },
    { key: "econ", header: "Econ", value: (r) => r.bowling.economy, sortable: true, defaultDir: "asc", cell: (r) => fmt(r.bowling.economy, 2) },
  ];
  const cols: StatColumn<Split>[] = [
    name,
    { key: "m", header: "M", value: (r) => r.matches, sortable: true },
    ...(skill === "bowl" ? [...bowlCols, ...batCols.slice(0, 1)] : [...batCols, ...bowlCols]),
  ];
  return (
    <section aria-label={title}>
      <h2 className="text-overline mb-2 text-muted-foreground">{title}</h2>
      <StatTable
        caption={caption}
        columns={cols}
        rows={rows}
        rowKey={(r) => String(r.id)}
        initialSort={{ key: "m", dir: "desc" }}
        maxHeight="26rem"
        footer={teams ? undefined : `Top ${rows.length} venues by matches played.`}
      />
    </section>
  );
}
