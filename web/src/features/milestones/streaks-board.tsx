"use client";

import { Flame } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/features/venues/error-state";
import { fmtDate } from "@/features/venues/format";
import { teamCode } from "@/features/venues/team-code";
import { cn } from "@/lib/utils";

import { FilterChips } from "./controls";
import { useStreaks } from "./queries";
import type { StreakBoard, StreakEntry } from "./types";

const SHORT: Record<string, string> = {
  score30: "30+ scores",
  wicket: "Wicket streaks",
  no_duck: "No-duck runs",
};

function dateRange(e: StreakEntry, sameSeason: boolean) {
  if (e.start_date === e.end_date) return fmtDate(e.start_date);
  const sy = e.start_date.slice(0, 4);
  const ey = e.end_date.slice(0, 4);
  return sy === ey || sameSeason ? `${fmtDate(e.start_date, false)} – ${fmtDate(e.end_date)}` : `${fmtDate(e.start_date)} – ${fmtDate(e.end_date)}`;
}

function StreakRow({ e, rank, sameSeason, showActive }: { e: StreakEntry; rank: number; sameSeason: boolean; showActive: boolean }) {
  const code = teamCode(e.team);
  return (
    <li className="border-b border-border last:border-b-0">
      <Link
        href={`/players/${encodeURIComponent(e.player.id)}`}
        className="flex min-h-[52px] items-center gap-3 px-3 outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset md:px-4"
      >
        <span className="num w-4 shrink-0 text-xs text-muted-foreground">{rank}</span>
        {code ? <TeamBadge team={code} /> : <span className="w-9 shrink-0" />}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-sm font-medium">{e.player.name}</span>
            {showActive && e.active && (
              <span className="inline-flex h-5 shrink-0 items-center gap-0.5 rounded-full bg-info/15 px-1.5 text-[11px] font-semibold text-info">
                <Flame aria-hidden className="size-3" />
                Running
              </span>
            )}
          </div>
          <div className="num truncate text-xs text-muted-foreground">{dateRange(e, sameSeason)}</div>
        </div>
        <div className="w-12 shrink-0 text-right">
          <div className="num text-base font-semibold">{e.length}</div>
          <div className="text-[11px] leading-4 text-muted-foreground">inns</div>
        </div>
      </Link>
    </li>
  );
}

function StreakList({ title, entries, empty, sameSeason, showActive, id }: { title: string; entries: StreakEntry[]; empty: string; sameSeason: boolean; showActive: boolean; id: string }) {
  return (
    <div className="min-w-0">
      <h3 id={id} className="text-overline mb-1 px-3 text-muted-foreground md:px-4">
        {title}
      </h3>
      {entries.length === 0 ? (
        <p className="px-3 py-3 text-sm text-muted-foreground md:px-4">{empty}</p>
      ) : (
        <ol aria-labelledby={id}>
          {entries.map((e, i) => (
            <StreakRow key={`${e.player.id}-${e.start_date}`} e={e} rank={i + 1} sameSeason={sameSeason} showActive={showActive} />
          ))}
        </ol>
      )}
    </div>
  );
}

export function StreakBoardCard({ board, season }: { board: StreakBoard; season: number | null }) {
  const id = `streak-${board.type}`;
  const scope = season ? `IPL ${season}` : "all IPL seasons";
  return (
    <section aria-labelledby={id} className="min-w-0 rounded-xl border border-border bg-card py-3 shadow-e1 md:py-4">
      <header className="mb-2 px-3 md:px-4">
        <h2 id={id} className="text-base font-semibold">
          {board.label}
        </h2>
        <p className="text-xs text-muted-foreground">Consecutive innings, {scope}. Streak length in innings.</p>
      </header>
      <div className="grid md:grid-cols-2 md:divide-x md:divide-border">
        <StreakList
          id={`${id}-current`}
          title={season ? `Running at end of ${season}` : "Running now"}
          entries={board.current}
          empty={season ? `No streak of this kind was still running at the end of ${season}.` : "No streak of this kind is running."}
          sameSeason={Boolean(season)}
          showActive={false}
        />
        <div className="max-md:mt-3 max-md:border-t max-md:border-border max-md:pt-3">
          <StreakList id={`${id}-longest`} title={season ? `Longest in ${season}` : "Longest ever"} entries={board.longest} empty="No streaks recorded." sameSeason={Boolean(season)} showActive />
        </div>
      </div>
    </section>
  );
}

export function StreaksSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading streaks" className="grid gap-4">
      <div className="flex gap-2 overflow-hidden">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-11 w-28 shrink-0 rounded-full md:h-9" />
        ))}
      </div>
      {Array.from({ length: 2 }, (_, b) => (
        <div key={b} className="rounded-xl border border-border bg-card p-3 md:p-4">
          <Skeleton className="h-4 w-56" />
          <Skeleton className="mt-2 h-2.5 w-72 max-w-full" />
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {Array.from({ length: 2 }, (_, c) => (
              <div key={c} className="grid gap-3">
                {Array.from({ length: 5 }, (_, r) => (
                  <div key={r} className="flex h-10 items-center gap-3">
                    <Skeleton className="h-6 w-9 rounded-full" />
                    <div className="grid flex-1 gap-1.5">
                      <Skeleton className="h-2.5 w-3/5" />
                      <Skeleton className="h-2 w-2/5" />
                    </div>
                    <Skeleton className="h-3 w-6" />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function StreaksView({ boards, season, asOf, initialType = "all" }: { boards: StreakBoard[]; season: number | null; asOf: string | null; initialType?: string }) {
  const [type, setType] = useState(boards.some((b) => b.type === initialType) ? initialType : "all");
  const shown = type === "all" ? boards : boards.filter((b) => b.type === type);
  if (boards.length === 0) {
    return (
      <EmptyState
        icon={Flame}
        title="No streaks to show"
        why={season ? `No innings are loaded for IPL ${season}.` : "No innings are loaded yet."}
        when="Streaks rebuild after each harvested match."
        action={{ href: "/records/milestones", label: "See milestones watch" }}
      />
    );
  }
  return (
    <div className="grid gap-4">
      <FilterChips
        label="Streak type"
        value={type}
        onChange={setType}
        options={[{ key: "all", label: "All streaks" }, ...boards.map((b) => ({ key: b.type, label: SHORT[b.type] ?? b.label }))]}
      />
      <p className="text-xs text-muted-foreground">
        {asOf && <>Data to {fmtDate(asOf)}. </>}A streak is information, not a forecast: the hot-hand effect in T20 is weak.
      </p>
      <div className="grid gap-3 md:gap-4">
        {shown.map((b) => (
          <StreakBoardCard key={b.type} board={b} season={season} />
        ))}
      </div>
    </div>
  );
}

export function Streaks({ season, initialType }: { season: number | null; initialType?: string }) {
  const q = useStreaks(season);
  if (q.isPending) return <StreaksSkeleton />;
  if (q.isError) {
    return (
      <ErrorState
        title="Couldn’t load streaks"
        error={q.error}
        onRetry={() => q.refetch()}
        retrying={q.isFetching}
        action={{ href: "/records/milestones", label: "See milestones instead" }}
      />
    );
  }
  return (
    <div aria-busy={q.isPlaceholderData || undefined} className={cn(q.isPlaceholderData && "opacity-60 transition-opacity")}>
      <StreaksView boards={q.data.boards} season={q.data.season} asOf={q.data.as_of} initialType={initialType} />
    </div>
  );
}
