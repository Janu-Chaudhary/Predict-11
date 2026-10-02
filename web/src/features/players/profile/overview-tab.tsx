"use client";

import type { ReactNode } from "react";

import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { StatTile } from "@/components/data/stat-tile";
import { Sparkline } from "@/components/data/sparkline";
import { TeamBadge } from "@/components/player/team-badge";
import { cn } from "@/lib/utils";

import { displayName, fmt, fmtDate, teamCode } from "../format";
import { FormBars } from "../form-bars";
import type { PlayerProfile, SeasonLine } from "../types";
import { Panel } from "../ui";
import { ProfileLayout } from "./profile-layout";

export function OverviewTab({ p, skill, rail }: { p: PlayerProfile; skill: "bat" | "bowl"; rail: ReactNode }) {
  const bat = p.batting;
  const bowl = p.bowling;
  const hasBat = bat.innings > 0;
  const hasBowl = bowl.balls > 0;
  // One discipline only: its panel spans the page, so it carries two extra tiles.
  const solo = hasBat !== hasBowl;
  const tiles = cn("grid grid-cols-2 gap-2 sm:grid-cols-4 md:gap-3", solo && "xl:grid-cols-6");

  const batting = hasBat && (
    <Panel title="Batting" key="bat">
      <div className={tiles}>
        <StatTile label="Runs" value={bat.runs} format={(n) => fmt(n)} hint={`${fmt(bat.innings)} inns · ${fmt(bat.not_outs)} NO`} />
        <StatTile label="Average" value={bat.average} format={(n) => fmt(n, 1)} hint={`HS ${bat.highest ?? "–"}`} />
        <StatTile label="Strike rate" value={bat.strike_rate} format={(n) => fmt(n, 1)} hint={`${fmt(bat.balls)} balls`} />
        <StatTile label="50s / 100s" value={`${bat.fifties} / ${bat.hundreds}`} hint={`4s ${fmt(bat.fours)} · 6s ${fmt(bat.sixes)}`} />
        {solo && <StatTile label="Boundaries" value={bat.fours + bat.sixes} format={(n) => fmt(n)} hint={`4s ${fmt(bat.fours)} · 6s ${fmt(bat.sixes)}`} className="max-xl:hidden" />}
        {solo && <StatTile label="Dot ball %" value={bat.dot_pct} format={(n) => fmt(n, 1)} hint={`30s ${bat.thirties} · ducks ${bat.ducks}`} className="max-xl:hidden" />}
      </div>
    </Panel>
  );
  const bowling = hasBowl && (
    <Panel title="Bowling" key="bowl">
      <div className={tiles}>
        <StatTile label="Wickets" value={bowl.wickets} hint={`${fmt(bowl.innings)} inns · ${bowl.overs} ov`} />
        <StatTile label="Economy" value={bowl.economy} format={(n) => fmt(n, 2)} hint={`Dot ${fmt(bowl.dot_pct, 1)}%`} />
        <StatTile label="Average" value={bowl.average} format={(n) => fmt(n, 1)} hint={`SR ${fmt(bowl.strike_rate, 1)}`} />
        <StatTile label="Best" value={bowl.best} hint={`3w+ ${bowl.three_plus} · 5w ${bowl.five_plus}`} />
        {solo && <StatTile label="Dot ball %" value={bowl.dot_pct} format={(n) => fmt(n, 1)} hint={`${fmt(bowl.balls)} balls`} className="max-xl:hidden" />}
        {solo && <StatTile label="Maidens" value={bowl.maidens} hint={`4w+ ${bowl.four_plus}`} className="max-xl:hidden" />}
      </div>
    </Panel>
  );

  const both = hasBat && hasBowl;
  return (
    <ProfileLayout
      band={
        hasBat || hasBowl ? (
          <div className={cn("grid grid-cols-1 gap-4 lg:gap-6", both && "xl:grid-cols-2")}>{skill === "bowl" ? [bowling, batting] : [batting, bowling]}</div>
        ) : (
          <p className="text-sm text-muted-foreground">No batting or bowling recorded in this scope.</p>
        )
      }
      main={
        <>
          <FormPanel p={p} skill={skill} />
          <SeasonTable p={p} />
        </>
      }
      rail={rail}
    />
  );
}

function FormPanel({ p, skill }: { p: PlayerProfile; skill: "bat" | "bowl" }) {
  const showBowl = skill === "bowl" ? p.form_bowling.length > 0 : p.form_batting.length === 0 && p.form_bowling.length > 0;
  if (!showBowl && p.form_batting.length === 0) return null;

  if (showBowl) {
    const chron = [...p.form_bowling].reverse();
    const econ = chron.map((f) => {
      const [o, b = "0"] = f.overs.split(".");
      const balls = Number(o) * 6 + Number(b);
      return balls ? (f.runs / balls) * 6 : 0;
    });
    const wkts = chron.reduce((s, f) => s + f.wickets, 0);
    const runsB = chron.reduce((s, f) => s + f.runs, 0);
    const ballsB = chron.reduce((s, f) => {
      const [o, b = "0"] = f.overs.split(".");
      return s + Number(o) * 6 + Number(b);
    }, 0);
    return (
      <Panel
        title={`Form · last ${chron.length} bowling innings`}
        action={<Sparkline values={econ} label={`Economy over the last ${chron.length} innings, oldest to newest: ${econ.map((e) => e.toFixed(1)).join(", ")}`} width={112} />}
      >
        <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <FormBars
            stretch
            label={`Wickets in the last ${chron.length} bowling innings, newest last`}
            max={Math.max(4, ...chron.map((f) => f.wickets))}
            items={chron.map((f) => ({
              key: f.match_id,
              value: f.wickets,
              label: f.figures,
              title: `${fmtDate(f.date)} vs ${f.opponent ?? "?"}: ${f.figures} (${f.overs} ov)`,
              emphasis: f.wickets >= 3 ? "high" : f.wickets === 0 ? "low" : null,
            }))}
          />
          <FormSummary
            items={[
              { label: "Wickets", value: fmt(wkts) },
              { label: "Economy", value: fmt(ballsB ? (runsB / ballsB) * 6 : null, 2) },
              { label: "Average", value: fmt(wkts ? runsB / wkts : null, 1) },
              { label: "3w+", value: fmt(chron.filter((f) => f.wickets >= 3).length) },
            ]}
          />
        </div>
        <p className="mt-2 text-xs text-muted-foreground">Bars = wickets (gold = 3+), line = economy. Newest on the right.</p>
      </Panel>
    );
  }

  const chron = [...p.form_batting].reverse();
  const total = chron.reduce((s, f) => s + f.runs, 0);
  const balls = chron.reduce((s, f) => s + f.balls, 0);
  const outs = chron.filter((f) => !f.not_out).length;
  return (
    <Panel
      title={`Form · last ${chron.length} innings`}
      action={<Sparkline values={chron.map((f) => f.runs)} label={`Runs over the last ${chron.length} innings, oldest to newest: ${chron.map((f) => f.runs).join(", ")}`} width={112} />}
    >
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <FormBars
          stretch
          label={`Runs in the last ${chron.length} innings, newest last`}
          max={Math.max(50, ...chron.map((f) => f.runs))}
          items={chron.map((f) => ({
            key: f.match_id,
            value: f.runs,
            label: `${f.runs}${f.not_out ? "*" : ""}`,
            title: `${fmtDate(f.date)} vs ${f.opponent ?? "?"}: ${f.score}${f.how_out ? `, ${f.how_out}` : ""}`,
            emphasis: f.runs >= 50 ? "high" : f.runs < 10 ? "low" : null,
          }))}
        />
        <FormSummary
          items={[
            { label: "Runs", value: fmt(total) },
            { label: "Average", value: fmt(outs ? total / outs : null, 1) },
            { label: "Strike rate", value: fmt(balls ? (total / balls) * 100 : null, 1) },
            { label: "50+", value: fmt(chron.filter((f) => f.runs >= 50).length) },
          ]}
        />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">Bars = runs (gold = 50+), * = not out. Newest on the right.</p>
    </Panel>
  );
}

/** Totals over the form window, beside the bars. */
function FormSummary({ items }: { items: { label: string; value: string }[] }) {
  return (
    <dl className="num grid grid-cols-4 gap-2 sm:grid-cols-2 sm:gap-x-6 sm:gap-y-3 sm:border-l sm:border-border sm:pl-6">
      {items.map((i) => (
        <div key={i.label} className="min-w-0">
          <dt className="text-overline truncate text-muted-foreground">{i.label}</dt>
          <dd className="font-condensed text-xl leading-7 font-bold lg:text-[1.75rem] lg:leading-9">{i.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function SeasonTable({ p }: { p: PlayerProfile }) {
  const cols: StatColumn<SeasonLine>[] = [
    { key: "season", header: "Season", value: (r) => r.season, align: "left", sortable: true, sticky: true, defaultDir: "desc" },
    {
      key: "team",
      header: "Team",
      align: "left",
      value: (r) => r.team ?? "",
      cell: (r) => (r.team ? <TeamBadge team={teamCode(r.team) ?? ""} /> : null),
    },
    { key: "m", header: "M", value: (r) => r.matches, sortable: true },
    { key: "runs", header: "Runs", value: (r) => r.batting.runs, sortable: true, cell: (r) => <span className="font-semibold">{fmt(r.batting.runs)}</span> },
    { key: "avg", header: "Avg", value: (r) => r.batting.average, sortable: true, cell: (r) => fmt(r.batting.average, 1) },
    { key: "sr", header: "SR", value: (r) => r.batting.strike_rate, sortable: true, cell: (r) => fmt(r.batting.strike_rate, 1) },
    { key: "hs", header: "HS", value: (r) => r.batting.highest, hideBelow: "sm" },
    { key: "wk", header: "Wkts", value: (r) => r.bowling.wickets, sortable: true },
    { key: "econ", header: "Econ", value: (r) => r.bowling.economy, sortable: true, defaultDir: "asc", cell: (r) => fmt(r.bowling.economy, 2) },
    { key: "ct", header: "Ct", value: (r) => r.fielding.catches, sortable: true, hideBelow: "sm" },
  ];
  return (
    <section aria-labelledby="by-season-h">
      <h2 id="by-season-h" className="text-overline mb-2 text-muted-foreground">
        By season
      </h2>
      <StatTable caption={`${displayName(p)}: IPL stats by season`} columns={cols} rows={p.by_season} rowKey={(r) => String(r.season)} initialSort={{ key: "season", dir: "desc" }} />
    </section>
  );
}
