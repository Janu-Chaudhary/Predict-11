import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/utils";

import { fmt } from "../format";
import { pcVar } from "./colours";
import { barWidths, rowBest, tally, tallyText, type MetricRow, type Subject } from "./metrics";

/** Category accents (theme tokens) for the section cards. */
export const ACCENT = {
  overview: "var(--brand)",
  batting: "var(--warning)",
  bowling: "var(--info)",
  fielding: "var(--positive)",
  fantasy: "var(--primary)",
  matchups: "var(--negative)",
} as const;

/**
 * Section card: icon tile + display heading with a thin category accent along the top edge,
 * optional right-hand slot (tally / toggle), then the body. Same surface as every card (§2.5).
 */
export function SectionCard({
  id,
  title,
  icon,
  accent,
  aside,
  subtitle,
  children,
  className,
  bodyClassName,
}: {
  id: string;
  title: string;
  icon: ReactNode;
  accent: string;
  aside?: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section
      aria-labelledby={`${id}-h`}
      data-section={id}
      className={cn("relative min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-e1", className)}
      style={{ "--accent": accent } as CSSProperties}
    >
      <div aria-hidden className="absolute inset-x-0 top-0 h-0.5 bg-[linear-gradient(90deg,var(--accent),transparent_75%)]" />
      <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 pt-4 md:px-5">
        <div className="flex min-w-0 items-center gap-2.5">
          <span aria-hidden className="inline-flex size-8 shrink-0 items-center justify-center rounded-lg bg-[color-mix(in_oklch,var(--accent)_14%,transparent)] text-[var(--accent)] [&_svg]:size-[18px]">
            {icon}
          </span>
          <div className="min-w-0">
            <h2 id={`${id}-h`} className="font-display text-lg leading-6 font-semibold">
              {title}
            </h2>
            {subtitle && <p className="line-clamp-2 text-xs text-muted-foreground">{subtitle}</p>}
          </div>
        </div>
        {aside}
      </header>
      <div className={cn("px-4 pt-3 pb-4 md:px-5", bodyClassName)}>{children}</div>
    </section>
  );
}

/** "Kohli leads 7 of 10" with a per-player win count (dot + number, colour never alone). */
export function TallyBadge({ rows, players, names }: { rows: MetricRow[]; players: Subject[]; names: string[] }) {
  const t = tally(rows, players);
  const text = tallyText(t, names);
  if (!text) return null;
  return (
    <div className="flex items-center gap-2" data-tally>
      <span className="num text-xs font-semibold text-foreground">{text}</span>
      {players.length > 2 && (
        <span className="num hidden items-center gap-1.5 text-[11px] text-muted-foreground sm:inline-flex">
          {t.wins.map((w, i) => (
            <span key={players[i].id} className="inline-flex items-center gap-0.5" title={`${names[i]}: ${w}`}>
              <span aria-hidden className="size-1.5 rounded-full" style={{ background: pcVar(i) }} />
              {w}
            </span>
          ))}
        </span>
      )}
    </div>
  );
}

/** Left/right player key above a two-player list so each side is named, not just coloured. */
export function SideKey({ names }: { names: string[] }) {
  if (names.length !== 2) return null;
  return (
    <div aria-hidden className="mb-1 flex items-center justify-between text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
      <span className="inline-flex items-center gap-1.5">
        <span className="size-2 rounded-full" style={{ background: pcVar(0) }} />
        {names[0]}
      </span>
      <span className="inline-flex items-center gap-1.5">
        {names[1]}
        <span className="size-2 rounded-full" style={{ background: pcVar(1) }} />
      </span>
    </div>
  );
}

function RowLabel({ row, ineligibleNote }: { row: MetricRow; ineligibleNote: boolean }) {
  return (
    <>
      {row.label}
      {row.better === "low" && <span className="ml-1 text-[11px] font-normal text-faint">· lower is better</span>}
      {ineligibleNote && <span className="ml-1 text-[11px] font-normal text-faint">· * small sample</span>}
    </>
  );
}

/**
 * One metric compared. Two players: values on either side of the label and a centre-out split bar
 * (each half ∝ the value; lower-is-better rows invert so the better value is longer). Three
 * players: one bar per player. The leader is bold in their team colour plus sr-only "(best)";
 * ties and informational rows have no leader; missing values print "–" with no bar.
 */
export function CompareRow({ row, players, names }: { row: MetricRow; players: Subject[]; names: string[] }) {
  const values = players.map(row.value);
  const eligible = players.map((p) => (row.eligible ? row.eligible(p) : true));
  const best = rowBest(row, players);
  const widths = barWidths(values, row.better);
  const text = players.map((p, i) => (row.display ? row.display(p) : fmt(values[i])));
  const hasValue = values.map((v, i) => (v !== null && Number.isFinite(v)) || text[i] !== "–");
  const smallSample = row.better !== null && players.some((_, i) => hasValue[i] && !eligible[i]);

  const valueEl = (i: number, align: "left" | "right") => {
    const isBest = best.includes(i);
    const muted = !eligible[i] && hasValue[i];
    return (
      <span
        data-best={isBest || undefined}
        className={cn(
          "num whitespace-nowrap tabular-nums",
          players.length === 2 ? "text-[15px] leading-5" : "text-[13px] leading-4",
          align === "right" ? "text-right" : "text-left",
          isBest ? "font-bold" : "font-medium text-foreground/80",
          muted && "text-muted-foreground",
        )}
        style={isBest ? { color: pcVar(i) } : undefined}
      >
        {text[i]}
        {muted && <span className="text-faint">*</span>}
        {isBest && <span className="sr-only"> (best)</span>}
      </span>
    );
  };

  const fill = (i: number) => ({
    background: row.better === null ? "var(--faint)" : pcVar(i),
    opacity: row.better === null ? 0.5 : best.includes(i) ? 1 : eligible[i] ? 0.38 : 0.18,
  });

  if (players.length === 2) {
    return (
      <div data-row={row.key} className="py-2">
        <div className="grid grid-cols-[minmax(4.5rem,auto)_1fr_minmax(4.5rem,auto)] items-baseline gap-2">
          {valueEl(0, "left")}
          <span className="truncate text-center text-[13px] text-muted-foreground">
            <RowLabel row={row} ineligibleNote={smallSample} />
          </span>
          {valueEl(1, "right")}
        </div>
        <div aria-hidden className="mt-1.5 grid grid-cols-2 gap-1">
          <span className="flex h-1.5 justify-end overflow-hidden rounded-l-full bg-surface-2">
            {widths[0] !== null && <span data-bar data-width={widths[0].toFixed(1)} className="block h-full rounded-l-full transition-[width]" style={{ width: `${widths[0]}%`, ...fill(0) }} />}
          </span>
          <span className="flex h-1.5 overflow-hidden rounded-r-full bg-surface-2">
            {widths[1] !== null && <span data-bar data-width={widths[1].toFixed(1)} className="block h-full rounded-r-full transition-[width]" style={{ width: `${widths[1]}%`, ...fill(1) }} />}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div data-row={row.key} className="grid grid-cols-1 gap-x-4 gap-y-1 py-1.5 sm:grid-cols-[minmax(8rem,11rem)_1fr] sm:items-center">
      <span className="text-[13px] text-muted-foreground">
        <RowLabel row={row} ineligibleNote={smallSample} />
      </span>
      <div className="grid gap-0.5">
        {players.map((p, i) => (
          <div key={p.id} className="grid grid-cols-[4.5rem_1fr_4rem] items-center gap-2">
            <span className="truncate text-[11px] text-muted-foreground">{names[i]}</span>
            <span aria-hidden className="h-1.5 overflow-hidden rounded-full bg-surface-2">
              {widths[i] !== null && <span data-bar data-width={widths[i]!.toFixed(1)} className="block h-full rounded-full transition-[width]" style={{ width: `${widths[i]}%`, ...fill(i) }} />}
            </span>
            {valueEl(i, "right")}
          </div>
        ))}
      </div>
    </div>
  );
}

/** A section card of metric rows with its tally. */
export function MetricCard({
  id,
  title,
  icon,
  accent,
  rows,
  players,
  names,
  empty,
  footnote,
  className,
}: {
  id: string;
  title: string;
  icon: ReactNode;
  accent: string;
  rows: MetricRow[];
  players: Subject[];
  names: string[];
  empty?: string;
  footnote?: ReactNode;
  className?: string;
}) {
  return (
    <SectionCard id={id} title={title} icon={icon} accent={accent} aside={<TallyBadge rows={rows} players={players} names={names} />} className={className}>
      {rows.length === 0 ? (
        <p className="py-2 text-sm text-muted-foreground">{empty ?? "No data in this scope."}</p>
      ) : (
        <>
          <SideKey names={names} />
          <div className="divide-y divide-border/60">
            {rows.map((r) => (
              <CompareRow key={r.key} row={r} players={players} names={names} />
            ))}
          </div>
        </>
      )}
      {footnote && <p className="mt-2 text-[11px] leading-4 text-muted-foreground">{footnote}</p>}
    </SectionCard>
  );
}
