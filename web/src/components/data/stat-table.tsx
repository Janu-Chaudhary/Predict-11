"use client";

import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

export type SortDir = "asc" | "desc";

export type StatColumn<T> = {
  key: string;
  header: ReactNode;
  /** Plain-text header for aria/sort announcements when `header` is not a string. */
  label?: string;
  /** Value used for sorting (and default rendering). */
  value: (row: T) => number | string | null | undefined;
  /** Custom cell renderer. */
  cell?: (row: T, index: number) => ReactNode;
  /** Numbers right-aligned (default for numeric values), names left. */
  align?: "left" | "right" | "center";
  sortable?: boolean;
  /** First sort direction when the header is clicked (numbers usually desc). */
  defaultDir?: SortDir;
  /** Stick this column to the left edge during horizontal scroll (usually the name). */
  sticky?: boolean;
  className?: string;
  headerClassName?: string;
  /** Hide below a breakpoint to keep mobile tables narrow. */
  hideBelow?: "sm" | "md" | "lg";
};

const HIDE = { sm: "max-sm:hidden", md: "max-md:hidden", lg: "max-lg:hidden" } as const;

export function compareValues(a: unknown, b: unknown): number {
  const na = a === null || a === undefined || a === "";
  const nb = b === null || b === undefined || b === "";
  if (na && nb) return 0;
  if (na) return 1; // empties always last
  if (nb) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

export function sortRows<T>(rows: T[], col: StatColumn<T> | undefined, dir: SortDir): T[] {
  if (!col) return rows;
  const sign = dir === "asc" ? 1 : -1;
  return rows
    .map((r, i) => [r, i] as const)
    .sort(([a, ia], [b, ib]) => {
      const va = col.value(a);
      const vb = col.value(b);
      const emptyA = va === null || va === undefined || va === "";
      const emptyB = vb === null || vb === undefined || vb === "";
      if (emptyA || emptyB) return compareValues(va, vb) || ia - ib;
      return sign * compareValues(va, vb) || ia - ib;
    })
    .map(([r]) => r);
}

/**
 * Sortable stat table (§2.4/§5.3): sticky header, tabular right-aligned numbers, optional sticky
 * first column, `aria-sort` on headers. Scrolls horizontally *inside its card* on mobile, never
 * the page. Height is capped so the sticky header works inside the scroll region.
 */
export function StatTable<T>({
  columns,
  rows,
  rowKey,
  caption,
  initialSort,
  rowClassName,
  rowLead,
  dense = false,
  maxHeight = "min(70dvh, 44rem)",
  className,
  footer,
}: {
  columns: StatColumn<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string;
  /** Visually hidden caption describing the table (a11y). */
  caption: string;
  initialSort?: { key: string; dir: SortDir };
  rowClassName?: (row: T, index: number) => string | undefined;
  /** Optional leading marker per row (e.g. zone stripe). Rendered inside the first cell. */
  rowLead?: (row: T, index: number) => ReactNode;
  dense?: boolean;
  maxHeight?: string;
  className?: string;
  footer?: ReactNode;
}) {
  const [sort, setSort] = useState<{ key: string; dir: SortDir } | null>(initialSort ?? null);
  const sortCol = columns.find((c) => c.key === sort?.key);
  const sorted = useMemo(() => sortRows(rows, sortCol, sort?.dir ?? "desc"), [rows, sortCol, sort?.dir]);

  const toggle = (col: StatColumn<T>) => {
    setSort((prev) => {
      if (prev?.key !== col.key) return { key: col.key, dir: col.defaultDir ?? (col.align === "left" ? "asc" : "desc") };
      return { key: col.key, dir: prev.dir === "asc" ? "desc" : "asc" };
    });
  };

  const alignOf = (c: StatColumn<T>) => c.align ?? "right";
  const rowH = dense ? "h-9" : "h-11 lg:h-12";

  return (
    // grid + minmax(0,1fr): the card's min-content width is 0, so a wide table scrolls inside its
    // region instead of stretching a grid/flex parent (and the page) to the table's width.
    <div className={cn("grid grid-cols-[minmax(0,1fr)] overflow-hidden rounded-xl border border-border bg-card shadow-e1", className)}>
      {/* `relative`: the sr-only caption is absolutely positioned; without a positioned scroll
          region its containing block was <body>, so it escaped the card and widened the page. */}
      <div className="relative overflow-auto overscroll-x-contain" style={{ maxHeight }} tabIndex={0} role="region" aria-label={caption}>
        <table className="num w-full border-separate border-spacing-0 text-sm leading-5 lg:text-[15px] lg:leading-6">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              {columns.map((c, ci) => {
                const active = sort?.key === c.key;
                const ariaSort = active ? (sort!.dir === "asc" ? "ascending" : "descending") : c.sortable ? "none" : undefined;
                const align = alignOf(c);
                return (
                  <th
                    key={c.key}
                    scope="col"
                    aria-sort={ariaSort}
                    className={cn(
                      "text-overline sticky top-0 z-10 h-10 border-b border-border bg-surface-2 px-3 whitespace-nowrap text-muted-foreground",
                      align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left",
                      c.sticky && "left-0 z-20",
                      ci === 0 && "pl-4",
                      c.hideBelow && HIDE[c.hideBelow],
                      c.headerClassName,
                    )}
                  >
                    {c.sortable ? (
                      <button
                        type="button"
                        onClick={() => toggle(c)}
                        className={cn(
                          "-mx-1 inline-flex min-h-6 items-center gap-1 rounded px-1 uppercase outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
                          align === "right" && "flex-row-reverse",
                          active && "text-foreground",
                        )}
                      >
                        {c.header}
                        {active ? (
                          sort!.dir === "asc" ? (
                            <ArrowUp aria-hidden className="size-3" />
                          ) : (
                            <ArrowDown aria-hidden className="size-3" />
                          )
                        ) : (
                          <ArrowUpDown aria-hidden className="size-3 opacity-40" />
                        )}
                      </button>
                    ) : (
                      c.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, ri) => (
              <tr key={rowKey(row, ri)} className={cn("group/row", rowClassName?.(row, ri))}>
                {columns.map((c, ci) => {
                  const align = alignOf(c);
                  const v = c.value(row);
                  return (
                    <td
                      key={c.key}
                      className={cn(
                        rowH,
                        "border-b border-border bg-card px-3 whitespace-nowrap group-last/row:border-b-0 group-hover/row:bg-surface-2",
                        align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left",
                        c.sticky && "sticky left-0 z-[5]",
                        ci === 0 && "relative pl-4",
                        c.hideBelow && HIDE[c.hideBelow],
                        c.className,
                      )}
                    >
                      {ci === 0 && rowLead?.(row, ri)}
                      {c.cell ? c.cell(row, ri) : v === null || v === undefined || v === "" ? <span className="text-faint">–</span> : v}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {footer && <div className="border-t border-border px-4 py-2.5 text-xs text-muted-foreground">{footer}</div>}
    </div>
  );
}
