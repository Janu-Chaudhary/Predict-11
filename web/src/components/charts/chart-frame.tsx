"use client";

import { ChartLine, Table2 } from "lucide-react";
import { useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

export type TableView = { columns: string[]; rows: (string | number)[][] };

/**
 * Card wrapper every chart sits in (§2.7): title, optional legend, an `aria-label` summary,
 * and a Chart ⇄ Table toggle so the data is never locked inside the picture.
 */
export function ChartFrame({
  title,
  summary,
  legend,
  table,
  actions,
  children,
  className,
}: {
  title: ReactNode;
  /** One-sentence description of what the chart shows, used as the figure's accessible name. */
  summary: string;
  legend?: ReactNode;
  table?: TableView;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const [view, setView] = useState<"chart" | "table">("chart");
  return (
    // w-full + min-w-0: never sized by its content. Recharts' ResponsiveContainer measures its
    // parent, so a content-sized frame (flex row / items-start column) collapsed to zero width.
    <section className={cn("w-full min-w-0 rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4", className)}>
      <header className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-overline text-muted-foreground">{title}</h3>
        <div className="flex items-center gap-1">
          {actions}
          {table && (
            <div role="group" aria-label="View" className="inline-flex rounded-[10px] bg-surface-2 p-0.5">
              {(["chart", "table"] as const).map((v) => {
                const Icon = v === "chart" ? ChartLine : Table2;
                return (
                  <button
                    key={v}
                    type="button"
                    aria-pressed={view === v}
                    onClick={() => setView(v)}
                    className={cn(
                      "inline-flex h-7 items-center gap-1 rounded-lg px-2 text-xs font-medium text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      view === v && "bg-card text-foreground shadow-e1",
                    )}
                  >
                    <Icon aria-hidden className="size-3.5" />
                    {v === "chart" ? "Chart" : "Table"}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </header>
      {legend && view === "chart" && <div className="mb-2">{legend}</div>}
      {view === "chart" || !table ? (
        <figure role="figure" aria-label={summary} className="m-0">
          {children}
          <figcaption className="sr-only">{summary}</figcaption>
        </figure>
      ) : (
        <div className="max-h-80 overflow-auto rounded-lg border border-border">
          <table className="num w-full text-[13px]">
            <caption className="sr-only">{summary}</caption>
            <thead>
              <tr>
                {table.columns.map((c, i) => (
                  <th key={c} scope="col" className={cn("text-overline sticky top-0 bg-surface-2 px-3 py-2 text-muted-foreground", i ? "text-right" : "text-left")}>
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((r, ri) => (
                <tr key={ri} className="border-t border-border">
                  {r.map((cell, ci) => (
                    <td key={ci} className={cn("h-8 px-3", ci ? "text-right" : "text-left")}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/** Direct-label style legend: swatch (solid or dashed line) + label. */
export function SeriesLegend({ items }: { items: { label: string; color: string; dashed?: boolean }[] }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {items.map((i) => (
        <li key={i.label} className="inline-flex items-center gap-1.5">
          <svg aria-hidden width="18" height="8">
            <line x1="1" x2="17" y1="4" y2="4" stroke={i.color} strokeWidth="2.5" strokeLinecap="round" strokeDasharray={i.dashed ? "4 3" : undefined} />
          </svg>
          <span className="text-foreground">{i.label}</span>
        </li>
      ))}
    </ul>
  );
}
