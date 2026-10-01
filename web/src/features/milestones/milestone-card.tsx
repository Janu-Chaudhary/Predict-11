import Link from "next/link";

import { TeamBadge, TeamStripe } from "@/components/player/team-badge";
import { teamCode } from "@/features/venues/team-code";

import { milestoneProgress, STAT_LABEL } from "./progress";
import type { Milestone } from "./types";

const fmt = (n: number) => n.toLocaleString("en-IN");

/** Progress bar from the previous round number to the target, with an accessible value. */
export function MilestoneProgressBar({ milestone, className }: { milestone: Pick<Milestone, "stat" | "current" | "target" | "player">; className?: string }) {
  const p = milestoneProgress(milestone);
  const unit = STAT_LABEL[milestone.stat]?.unit ?? milestone.stat;
  return (
    <div className={className}>
      <div
        role="progressbar"
        aria-label={`${milestone.player.name}: ${fmt(p.current)} of ${fmt(p.to)} ${unit}`}
        aria-valuemin={p.from}
        aria-valuemax={p.to}
        aria-valuenow={p.current}
        aria-valuetext={`${fmt(p.current)} of ${fmt(p.to)} ${unit}, ${p.pct}% of the way from ${fmt(p.from)}`}
        className="h-2 overflow-hidden rounded-full bg-surface-3"
      >
        <div data-testid="milestone-fill" className="h-full rounded-full bg-primary" style={{ width: `${p.ratio * 100}%` }} />
      </div>
      <div className="num mt-1 flex justify-between text-[11px] leading-4 text-muted-foreground">
        <span>{fmt(p.from)}</span>
        <span>
          <span className="font-medium text-foreground">{fmt(p.current)}</span> / {fmt(p.to)}
        </span>
      </div>
    </div>
  );
}

/** One "milestones watch" card: who, how many to go, for what, and the progress bar. */
export function MilestoneCard({ milestone: m }: { milestone: Milestone }) {
  const code = teamCode(m.team);
  const label = STAT_LABEL[m.stat];
  const titleId = `ms-${m.player.id}-${m.stat}`;
  return (
    <article aria-labelledby={titleId} className="relative flex min-w-0 gap-3 rounded-xl border border-border bg-card p-3 shadow-e1 md:p-4">
      {code && <TeamStripe team={code} className="-my-1" />}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          {code && <TeamBadge team={code} />}
          <h3 id={titleId} className="min-w-0 flex-1 truncate text-sm font-semibold">
            <Link href={`/players/${encodeURIComponent(m.player.id)}`} className="rounded outline-none after:absolute after:inset-0 after:rounded-xl hover:underline focus-visible:ring-2 focus-visible:ring-ring">
              {m.player.name}
            </Link>
          </h3>
        </div>
        <p className="mt-2 flex flex-wrap items-baseline gap-x-1.5">
          <span className="text-sm text-muted-foreground">needs</span>
          <span className="font-condensed num text-[1.75rem] leading-8 font-bold">{fmt(m.needed)}</span>
          <span className="text-sm text-muted-foreground">
            for <span className="num font-medium text-foreground">{fmt(m.target)}</span> IPL {label?.unit ?? m.stat}
          </span>
        </p>
        <MilestoneProgressBar milestone={m} className="mt-2" />
      </div>
    </article>
  );
}
