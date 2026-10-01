"use client";

import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { StatTile } from "@/components/data/stat-tile";
import { TeamBadge } from "@/components/player/team-badge";

import { displayName, fmt, teamCode } from "../format";
import type { PlayerProfile, SeasonLine } from "../types";
import { Panel } from "../ui";

export function FieldingTab({ p }: { p: PlayerProfile }) {
  const f = p.fielding;
  const dismissals = f.catches + f.stumpings + f.run_outs;
  const cols: StatColumn<SeasonLine>[] = [
    { key: "season", header: "Season", value: (r) => r.season, align: "left", sortable: true, sticky: true },
    { key: "team", header: "Team", align: "left", value: (r) => r.team ?? "", cell: (r) => (r.team ? <TeamBadge team={teamCode(r.team) ?? ""} /> : null) },
    { key: "m", header: "M", value: (r) => r.matches, sortable: true },
    { key: "ct", header: "Ct", value: (r) => r.fielding.catches, sortable: true, cell: (r) => <span className="font-semibold">{r.fielding.catches}</span> },
    { key: "st", header: "St", value: (r) => r.fielding.stumpings, sortable: true },
    { key: "ro", header: "RO", value: (r) => r.fielding.run_outs, sortable: true },
    { key: "pm", header: "Ct/M", value: (r) => (r.matches ? r.fielding.catches / r.matches : null), sortable: true, cell: (r) => fmt(r.matches ? r.fielding.catches / r.matches : null, 2) },
  ];
  return (
    <>
      <Panel title="Fielding">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:gap-3">
          <StatTile label="Catches" value={f.catches} hint={`${fmt(p.matches ? f.catches / p.matches : null, 2)} per match`} />
          <StatTile label="Stumpings" value={f.stumpings} />
          <StatTile label="Run-outs" value={f.run_outs} />
          <StatTile label="Dismissals" value={dismissals} hint={`in ${fmt(p.matches)} matches`} />
        </div>
      </Panel>
      <section aria-labelledby="field-season-h">
        <h2 id="field-season-h" className="text-overline mb-2 text-muted-foreground">
          By season
        </h2>
        <StatTable caption={`${displayName(p)}: fielding by season`} columns={cols} rows={p.by_season} rowKey={(r) => String(r.season)} initialSort={{ key: "season", dir: "desc" }} />
      </section>
    </>
  );
}
