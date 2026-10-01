"use client";

import { Flag } from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/shell/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/features/venues/error-state";
import { fmtDate } from "@/features/venues/format";
import { cn } from "@/lib/utils";

import { FilterChips } from "./controls";
import { MilestoneCard } from "./milestone-card";
import { groupMilestones, STAT_LABEL } from "./progress";
import { useMilestones } from "./queries";
import type { Milestone } from "./types";

const GRID = "grid gap-3 sm:grid-cols-2 lg:grid-cols-3 md:gap-4";

export function MilestonesSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading milestones">
      <div className="mb-4 flex gap-2 overflow-hidden">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-11 w-24 shrink-0 rounded-full md:h-9" />
        ))}
      </div>
      <Skeleton className="mb-2 h-3 w-24" />
      <div className={GRID}>
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-3 md:p-4">
            <div className="flex items-center gap-2">
              <Skeleton className="h-6 w-9 rounded-full" />
              <Skeleton className="h-3 w-28" />
            </div>
            <Skeleton className="mt-3 h-7 w-40" />
            <Skeleton className="mt-3 h-2 w-full rounded-full" />
            <Skeleton className="mt-1.5 h-2 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Pure view (tested with mocked data). */
export function MilestonesWatchView({ milestones, season, asOf }: { milestones: Milestone[]; season: number; asOf: string | null }) {
  const [stat, setStat] = useState<string>("all");
  const groups = useMemo(() => groupMilestones(milestones), [milestones]);
  const shown = stat === "all" ? groups : groups.filter((g) => g.stat === stat);

  if (milestones.length === 0) {
    return (
      <EmptyState
        icon={Flag}
        title={`No milestones within reach for IPL ${season}`}
        why={`Nobody who played in ${season} is close to a round-number career total (e.g. within 100 runs of 2,000 or 10 wickets of 150).`}
        when="The list refreshes after each harvested match."
        action={{ href: "/records/streaks", label: "See current streaks" }}
      />
    );
  }

  return (
    <div className="grid gap-4">
      <FilterChips
        label="Milestone type"
        value={stat}
        onChange={setStat}
        options={[{ key: "all", label: "All", count: milestones.length }, ...groups.map((g) => ({ key: g.stat, label: STAT_LABEL[g.stat]?.title ?? g.stat, count: g.items.length }))]}
      />
      <p className="text-xs text-muted-foreground">
        IPL career totals up to the end of {season}
        {asOf && <> (last match {fmtDate(asOf)})</>}, for players who appeared in {season}. Bars run from the previous round number to the next. Closest first.
      </p>
      {shown.map((g) => {
        const id = `ms-group-${g.stat}`;
        return (
          <section key={g.stat} aria-labelledby={id} className="grid gap-2">
            <h2 id={id} className="text-overline flex items-center gap-2 text-muted-foreground">
              {STAT_LABEL[g.stat]?.title ?? g.stat}
              <span className="num font-medium text-faint">{g.items.length}</span>
            </h2>
            <ul className={cn(GRID)}>
              {g.items.map((m) => (
                <li key={`${m.player.id}-${m.stat}-${m.target}`} className="min-w-0">
                  <MilestoneCard milestone={m} />
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

export function MilestonesWatch({ season }: { season: number | null }) {
  const q = useMilestones(season);
  if (q.isPending) return <MilestonesSkeleton />;
  if (q.isError) {
    return (
      <ErrorState
        title="Couldn’t load milestones"
        error={q.error}
        onRetry={() => q.refetch()}
        retrying={q.isFetching}
        action={{ href: "/records/streaks", label: "See streaks instead" }}
      />
    );
  }
  return (
    <div aria-busy={q.isPlaceholderData || undefined} className={cn(q.isPlaceholderData && "opacity-60 transition-opacity")}>
      <MilestonesWatchView milestones={q.data.milestones} season={q.data.season} asOf={q.data.as_of} />
    </div>
  );
}
