"use client";

import { ChevronRight, Flag, Flame } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { TeamBadge } from "@/components/player/team-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { teamCode } from "@/features/venues/team-code";

import { milestoneProgress, STAT_LABEL } from "./progress";
import { useMilestones, useStreaks } from "./queries";

const SHORT: Record<string, string> = {
  score30: "30+ scores",
  wicket: "Wickets in consecutive innings",
  no_duck: "Innings without a duck",
};

const fmt = (n: number) => n.toLocaleString("en-IN");

/** Side-rail card shell for the records pages. */
function RailCard({ id, icon: Icon, title, note, href, cta, children }: { id: string; icon: typeof Flag; title: string; note: ReactNode; href: string; cta: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="min-w-0 rounded-xl border border-border bg-card shadow-e1">
      <header className="px-4 pt-4 pb-2">
        <h2 id={id} className="flex items-center gap-2 text-base font-semibold">
          <Icon aria-hidden className="size-4 text-muted-foreground" strokeWidth={1.75} />
          {title}
        </h2>
        <p className="mt-0.5 text-xs text-muted-foreground">{note}</p>
      </header>
      {children}
      <Link
        href={href}
        className="flex h-11 items-center justify-between border-t border-border px-4 text-sm font-medium text-brand outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
      >
        {cta}
        <ChevronRight aria-hidden className="size-4" />
      </Link>
    </section>
  );
}

function RailSkeleton({ label }: { label: string }) {
  return (
    <div role="status" aria-busy="true" aria-label={label} className="grid gap-3 rounded-xl border border-border bg-card p-4">
      <Skeleton className="h-4 w-40" />
      {Array.from({ length: 6 }, (_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  );
}

/** Streaks still running in the scope, top few per board (shown beside the milestones watch). */
export function RunningStreaksRail({ season, perBoard = 4 }: { season: number | null; perBoard?: number }) {
  const q = useStreaks(season);
  if (q.isPending) return <RailSkeleton label="Loading running streaks" />;
  if (q.isError) return null;
  const boards = q.data.boards.filter((b) => b.current.length > 0);
  const href = season ? `/records/streaks?season=${season}` : "/records/streaks";
  return (
    <RailCard
      id="rail-streaks"
      icon={Flame}
      title={season ? `Running at end of ${season}` : "Running streaks"}
      note="Consecutive innings. Length in innings."
      href={href}
      cta="All streaks"
    >
      {boards.length === 0 ? (
        <p className="px-4 pb-3 text-sm text-muted-foreground">No streak is running.</p>
      ) : (
        <div className="grid gap-3 pb-2">
          {boards.map((b) => (
            <div key={b.type} className="min-w-0">
              <h3 className="text-overline px-4 pb-1 text-muted-foreground">{SHORT[b.type] ?? b.label}</h3>
              <ol>
                {b.current.slice(0, perBoard).map((e) => {
                  const code = teamCode(e.team);
                  return (
                    <li key={`${e.player.id}-${e.start_date}`}>
                      <Link
                        href={`/players/${encodeURIComponent(e.player.id)}`}
                        className="flex h-10 items-center gap-2.5 px-4 text-sm outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                      >
                        {code ? <TeamBadge team={code} /> : <span className="w-9 shrink-0" />}
                        <span className="min-w-0 flex-1 truncate font-medium">{e.player.name}</span>
                        <span className="num shrink-0 font-semibold">{e.length}</span>
                        <span className="w-7 shrink-0 text-[11px] text-muted-foreground">inns</span>
                      </Link>
                    </li>
                  );
                })}
              </ol>
            </div>
          ))}
        </div>
      )}
    </RailCard>
  );
}

/** The closest career milestones (by share of the way to the next round number). */
export function ClosestMilestonesRail({ season, limit = 10 }: { season: number | null; limit?: number }) {
  const q = useMilestones(season);
  if (q.isPending) return <RailSkeleton label="Loading closest milestones" />;
  if (q.isError) return null;
  const rows = q.data.milestones
    .map((m) => ({ m, p: milestoneProgress(m) }))
    .sort((a, b) => b.p.ratio - a.p.ratio || a.m.needed - b.m.needed)
    .slice(0, limit);
  const href = season ? `/records/milestones?season=${season}` : "/records/milestones";
  return (
    <RailCard
      id="rail-milestones"
      icon={Flag}
      title="Closest milestones"
      note={<>IPL career totals to the end of {q.data.season}. Nearest round numbers first.</>}
      href={href}
      cta="Milestones watch"
    >
      {rows.length === 0 ? (
        <p className="px-4 pb-3 text-sm text-muted-foreground">No milestones within reach for {q.data.season}.</p>
      ) : (
        <ol className="pb-2">
          {rows.map(({ m, p }) => {
            const code = teamCode(m.team);
            const unit = STAT_LABEL[m.stat]?.unit ?? m.stat;
            return (
              <li key={`${m.player.id}-${m.stat}-${m.target}`}>
                <Link
                  href={`/players/${encodeURIComponent(m.player.id)}`}
                  className="block px-4 py-2 outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                >
                  <span className="flex items-center gap-2.5 text-sm">
                    {code ? <TeamBadge team={code} /> : <span className="w-9 shrink-0" />}
                    <span className="min-w-0 flex-1 truncate font-medium">{m.player.name}</span>
                    <span className="num shrink-0 text-xs text-muted-foreground">
                      needs <span className="text-sm font-semibold text-foreground">{fmt(m.needed)}</span> for {fmt(m.target)} {unit}
                    </span>
                  </span>
                  <span aria-hidden className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-surface-3">
                    <span className="block h-full rounded-full bg-primary" style={{ width: `${p.ratio * 100}%` }} />
                  </span>
                </Link>
              </li>
            );
          })}
        </ol>
      )}
    </RailCard>
  );
}
