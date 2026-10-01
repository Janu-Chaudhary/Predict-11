"use client";

import { ConfidenceBadge } from "@/components/data/confidence-badge";
import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { TableSkeleton } from "@/components/loaders/page-skeletons";

import { H2H_THRESHOLDS, resolveConfidence } from "../../h2h/confidence";
import { fmt } from "../format";
import { type HandSplit, type TypeSplit, typeLabel, unknownNote, useBatterVsTypes, useBowlerVsHands } from "../matchups";
import { QueryError } from "../ui";

function Note({ text }: { text: string | null }) {
  if (!text) return null;
  return <p className="mt-2 px-1 text-xs text-muted-foreground">{text}</p>;
}

function scopeNote(seasonOnly: boolean) {
  return seasonOnly ? "Single-season scope isn’t available for type splits; showing career." : null;
}

/** D2: batter vs each bowling type (and the pace / spin totals), with a sample-size badge per row. */
export function BatterTypesTable({ id, name, since, seasonOnly = false }: { id: string; name: string; since?: string; seasonOnly?: boolean }) {
  const q = useBatterVsTypes(id, since);
  if (q.isPending) return <TableSkeleton rows={6} cols={6} />;
  if (q.isError) return <QueryError error={q.error} onRetry={() => q.refetch()} what="bowling-type splits" />;
  const d = q.data;
  const rows = [...d.by_group.map((g) => ({ ...g, isGroup: true })), ...d.by_type.map((t) => ({ ...t, isGroup: false }))];
  if (rows.length === 0) return <p className="text-sm text-muted-foreground">No balls faced against a bowler of known type.</p>;
  const cols: StatColumn<TypeSplit & { isGroup: boolean }>[] = [
    {
      key: "type",
      header: "Bowling type",
      align: "left",
      sticky: true,
      value: (r) => r.bowling_type,
      cell: (r) => <span className={r.isGroup ? "font-semibold" : ""}>{r.isGroup ? `All ${r.bowling_type}` : typeLabel(r.bowling_type)}</span>,
    },
    { key: "balls", header: "Balls", value: (r) => r.balls, sortable: true },
    { key: "runs", header: "Runs", value: (r) => r.runs, sortable: true, hideBelow: "sm" },
    { key: "outs", header: "Outs", value: (r) => r.dismissals, sortable: true },
    { key: "sr", header: "SR", value: (r) => r.strike_rate, sortable: true, cell: (r) => <span className="font-semibold">{fmt(r.strike_rate, 1)}</span> },
    { key: "avg", header: "Avg", value: (r) => r.average, sortable: true, cell: (r) => fmt(r.average, 1) },
    { key: "dot", header: "Dot %", value: (r) => r.dot_pct, sortable: true, hideBelow: "md", cell: (r) => fmt(r.dot_pct, 1) },
    { key: "conf", header: "Sample", align: "right", value: (r) => r.balls, cell: (r) => <ConfidenceBadge n={r.balls} level={resolveConfidence(r.confidence, r.balls)} thresholds={H2H_THRESHOLDS} showN={false} /> },
  ];
  return (
    <section aria-label="Against bowling types">
      <h2 className="text-overline mb-2 text-muted-foreground">Against bowling types{d.batting_hand ? ` · ${d.batting_hand === "L" ? "left" : "right"}-hand bat` : ""}</h2>
      <StatTable
        caption={`${name}: batting against each bowling type`}
        columns={cols}
        rows={rows}
        rowKey={(r) => `${r.isGroup ? "g" : "t"}-${r.bowling_type}`}
        rowClassName={(r) => (r.isGroup ? "[&>td]:bg-surface-2/50" : undefined)}
        footer="Pace and spin totals first, then each type. Sample badge: low under 12 balls, medium 12–29, high 30+."
      />
      <Note text={unknownNote(d.coverage, "bowling type")} />
      <Note text={scopeNote(seasonOnly)} />
    </section>
  );
}

/** D2: bowler vs right- and left-handed batters. */
export function BowlerHandsTable({ id, name, since, seasonOnly = false }: { id: string; name: string; since?: string; seasonOnly?: boolean }) {
  const q = useBowlerVsHands(id, since);
  if (q.isPending) return <TableSkeleton rows={2} cols={6} />;
  if (q.isError) return <QueryError error={q.error} onRetry={() => q.refetch()} what="batting-hand splits" />;
  const d = q.data;
  if (d.by_hand.length === 0) return <p className="text-sm text-muted-foreground">No balls bowled to a batter of known hand.</p>;
  const cols: StatColumn<HandSplit>[] = [
    { key: "hand", header: "Batters", align: "left", sticky: true, value: (r) => r.label, cell: (r) => <span>{r.hand === "L" ? "Left-handed" : "Right-handed"} <span className="text-muted-foreground">({r.label})</span></span> },
    { key: "balls", header: "Balls", value: (r) => r.balls, sortable: true },
    { key: "runs", header: "Runs", value: (r) => r.runs_conceded, sortable: true, hideBelow: "sm" },
    { key: "wk", header: "Wkts", value: (r) => r.wickets, sortable: true, cell: (r) => <span className="font-semibold">{r.wickets}</span> },
    { key: "econ", header: "Econ", value: (r) => r.economy, sortable: true, defaultDir: "asc", cell: (r) => fmt(r.economy, 2) },
    { key: "sr", header: "SR", value: (r) => r.strike_rate, sortable: true, defaultDir: "asc", hideBelow: "sm", cell: (r) => fmt(r.strike_rate, 1) },
    { key: "avg", header: "Avg", value: (r) => r.average, sortable: true, defaultDir: "asc", cell: (r) => fmt(r.average, 1) },
    { key: "dot", header: "Dot %", value: (r) => r.dot_pct, sortable: true, hideBelow: "md", cell: (r) => fmt(r.dot_pct, 1) },
    { key: "conf", header: "Sample", value: (r) => r.balls, cell: (r) => <ConfidenceBadge n={r.balls} level={resolveConfidence(r.confidence, r.balls)} thresholds={H2H_THRESHOLDS} showN={false} /> },
  ];
  return (
    <section aria-label="Against batting hands">
      <h2 className="text-overline mb-2 text-muted-foreground">Against batting hands{d.bowling_type ? ` · ${d.bowling_type}` : ""}</h2>
      <StatTable caption={`${name}: bowling against right- and left-handed batters`} columns={cols} rows={d.by_hand} rowKey={(r) => r.hand} footer="Legal balls. SR = balls per wicket; runs include wides and no-balls; run outs excluded." />
      <Note text={unknownNote(d.coverage, "batting hand")} />
      <Note text={scopeNote(seasonOnly)} />
    </section>
  );
}
