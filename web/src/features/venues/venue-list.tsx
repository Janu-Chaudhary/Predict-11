"use client";

import { MapPin, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { StatTable, type StatColumn } from "@/components/data/stat-table";
import { TableSkeleton } from "@/components/loaders/page-skeletons";
import { EmptyState } from "@/components/shell/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { ErrorState } from "./error-state";
import { fmtInt, fmtPct, fmtRuns } from "./format";
import { useVenues } from "./queries";
import type { VenueSummary } from "./types";

/** Below this many 2023+ matches a par score is shown but flagged as a small sample. */
export const SMALL_SAMPLE = 10;

type Scope = "active" | "all";

function columns(recentFrom: number): StatColumn<VenueSummary>[] {
  return [
    {
      key: "name",
      header: "Venue",
      align: "left",
      sortable: true,
      sticky: true,
      value: (v) => v.name,
      className: "max-w-[11rem] sm:max-w-[18rem] md:max-w-none",
      cell: (v) => (
        <Link
          href={`/venues/${v.id}`}
          className="block min-w-0 rounded py-1 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="block truncate font-medium text-foreground">{v.name}</span>
          <span className="block truncate text-xs text-muted-foreground">{v.city ?? "City not recorded"}</span>
        </Link>
      ),
    },
    {
      key: "par_recent",
      header: `Par ${recentFrom}+`,
      label: `Average first-innings score since ${recentFrom}`,
      sortable: true,
      value: (v) => v.par_recent,
      cell: (v) =>
        v.par_recent === null ? (
          <span className="text-faint">–</span>
        ) : (
          <span className="inline-flex items-baseline gap-1">
            {v.matches_recent < SMALL_SAMPLE && (
              <span className="text-[11px] font-medium text-warning" title={`Only ${v.matches_recent} matches since ${recentFrom}`}>
                n={v.matches_recent}
              </span>
            )}
            <span className="font-semibold">{fmtRuns(v.par_recent)}</span>
          </span>
        ),
    },
    {
      key: "par_all_time",
      header: "Par all-time",
      sortable: true,
      value: (v) => v.par_all_time,
      cell: (v) => <span className="text-muted-foreground">{fmtRuns(v.par_all_time)}</span>,
      hideBelow: "sm",
    },
    {
      key: "chase",
      header: `Chase win ${recentFrom}+`,
      sortable: true,
      value: (v) => v.chase_win_pct_recent,
      cell: (v) => fmtPct(v.chase_win_pct_recent),
      hideBelow: "md",
    },
    {
      key: "matches_recent",
      header: `Matches ${recentFrom}+`,
      sortable: true,
      value: (v) => v.matches_recent,
      cell: (v) => fmtInt(v.matches_recent),
      hideBelow: "md",
    },
    {
      key: "matches",
      header: "Matches",
      sortable: true,
      value: (v) => v.matches,
      cell: (v) => fmtInt(v.matches),
    },
    {
      key: "seasons",
      header: "Seasons",
      sortable: true,
      value: (v) => v.last_season,
      cell: (v) => (v.first_season === null ? "–" : v.first_season === v.last_season ? String(v.first_season) : `${v.first_season}–${v.last_season}`),
      hideBelow: "lg",
    },
  ];
}

export function VenueListSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading venues">
      <div className="mb-3 flex flex-wrap gap-2">
        <Skeleton className="h-11 w-60 rounded-[10px]" />
        <Skeleton className="h-11 w-56 rounded-[10px]" />
      </div>
      <TableSkeleton rows={12} cols={6} />
    </div>
  );
}

export function VenueList() {
  const q = useVenues();
  const [scope, setScope] = useState<Scope>("active");
  const [filter, setFilter] = useState("");

  const rows = useMemo(() => {
    const all = q.data?.venues ?? [];
    const term = filter.trim().toLowerCase();
    return all
      .filter((v) => scope === "all" || v.matches_recent > 0)
      .filter((v) => !term || v.name.toLowerCase().includes(term) || (v.city ?? "").toLowerCase().includes(term));
  }, [q.data, scope, filter]);

  if (q.isPending) return <VenueListSkeleton />;
  if (q.isError) {
    return <ErrorState title="Couldn’t load venues" error={q.error} onRetry={() => q.refetch()} retrying={q.isFetching} action={{ href: "/table", label: "See the points table" }} />;
  }

  const { recent_from: recentFrom, venues } = q.data;
  const activeCount = venues.filter((v) => v.matches_recent > 0).length;

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Which grounds" className="inline-flex rounded-[10px] bg-surface-2 p-1">
          {(
            [
              ["active", `Used since ${recentFrom}`, activeCount],
              ["all", "All grounds", venues.length],
            ] as const
          ).map(([key, label, n]) => (
            <button
              key={key}
              type="button"
              aria-pressed={scope === key}
              onClick={() => setScope(key)}
              className={cn(
                "inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-medium text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring",
                scope === key && "bg-card text-foreground shadow-e1",
              )}
            >
              {label}
              <span className="num text-xs text-muted-foreground">{n}</span>
            </button>
          ))}
        </div>
        <label className="relative flex h-11 min-w-0 flex-1 items-center sm:max-w-64">
          <span className="sr-only">Filter venues by name or city</span>
          <Search aria-hidden className="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
          <input
            type="search"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter by ground or city"
            className="h-11 w-full rounded-[10px] border border-border bg-card pr-3 pl-9 text-sm outline-none placeholder:text-faint focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          compact
          icon={MapPin}
          title="No ground matches that filter"
          why={filter ? `Nothing in ${scope === "active" ? `grounds used since ${recentFrom}` : "the venue list"} matches “${filter.trim()}”.` : "No venues have hosted an IPL match in this window."}
          when="Clear the filter or switch to All grounds."
        />
      ) : (
        <StatTable
          key={scope}
          caption={`IPL venues, ${rows.length} shown. Par is the average first-innings score; ${recentFrom}+ is the impact-player era.`}
          columns={columns(recentFrom)}
          rows={rows}
          rowKey={(v) => String(v.id)}
          initialSort={{ key: scope === "active" ? "matches_recent" : "matches", dir: "desc" }}
          maxHeight="none"
          footer={
            <>
              Par = average first-innings total in completed, non-DLS matches. Scoring has inflated since 2022 (powerplay run rate 7.8 → 10.1), so the{" "}
              {recentFrom}+ column is the one to plan with. <span className="font-medium text-warning">n=</span> marks fewer than {SMALL_SAMPLE} matches.
            </>
          }
        />
      )}
    </div>
  );
}
