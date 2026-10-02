import { BarChart3, Crown, Gauge, Target, type LucideIcon } from "lucide-react";
import type { Metadata } from "next";

import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";

export const metadata: Metadata = { title: "Accuracy" };

/** The three reports this page will carry once the model is backtested. No numbers until then. */
const REPORTS: { id: string; icon: LucideIcon; title: string; body: string; axis: string }[] = [
  {
    id: "acc-baselines",
    icon: BarChart3,
    title: "Per-season results vs baselines",
    body: "Projection error for every replayed season, next to simple baselines, so you can see whether the model earns its keep.",
    axis: "error by season",
  },
  {
    id: "acc-captain",
    icon: Crown,
    title: "Captain hit-rate",
    body: "How often one of the model’s top-2 captain picks was actually among the match’s highest fantasy scorers.",
    axis: "hit-rate by season",
  },
  {
    id: "acc-calibration",
    icon: Gauge,
    title: "Calibration",
    body: "Do the floor–ceiling ranges contain the actual score as often as they claim? A well-calibrated 80% range should hold about 80% of the time.",
    axis: "claimed vs observed coverage",
  },
];

function PlannedReport({ r }: { r: (typeof REPORTS)[number] }) {
  const Icon = r.icon;
  return (
    <section aria-labelledby={r.id} className="flex min-w-0 flex-col rounded-xl border border-border bg-card p-4 shadow-e1 lg:p-5">
      <div className="flex items-center gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-muted-foreground">
          <Icon aria-hidden className="size-5" strokeWidth={1.75} />
        </span>
        <h2 id={r.id} className="font-display text-lg leading-6 font-semibold">
          {r.title}
        </h2>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{r.body}</p>
      {/* Empty chart frame: shows where the report goes without drawing invented data. */}
      <div
        aria-hidden
        className="mt-4 grid min-h-40 flex-1 place-items-center rounded-lg border border-dashed border-border bg-[repeating-linear-gradient(0deg,transparent_0_31px,var(--border)_31px_32px)] text-xs text-faint"
      >
        {r.axis}
      </div>
      <p className="mt-3 inline-flex w-fit items-center rounded-full bg-surface-2 px-2.5 py-1 text-xs font-medium text-muted-foreground">Awaiting backtest</p>
    </section>
  );
}

export default function AccuracyPage() {
  return (
    <>
      <PageHeader overline="Trust" title="Accuracy" subtitle="The public backtest behind every projection, warts and all." />
      <div className="grid gap-4 lg:gap-5">
        <EmptyState
          icon={Target}
          title="Backtest results not published yet"
          why="The projection model hasn’t been backtested, so there is nothing honest to show."
          when="After the model is trained, every season is replayed and scored here."
          action={{ href: "/matches", label: "Browse matches" }}
        />
        <h2 className="text-overline text-muted-foreground">Coming here</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:gap-5 xl:grid-cols-3">
          {REPORTS.map((r) => (
            <PlannedReport key={r.id} r={r} />
          ))}
        </div>
      </div>
    </>
  );
}
