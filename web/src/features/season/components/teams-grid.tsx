"use client";

import { Trophy } from "lucide-react";
import Link from "next/link";

import { GridPageSkeleton } from "@/components/loaders/page-skeletons";
import { TeamBadge } from "@/components/player/team-badge";
import { PageHeader, SectionHeader } from "@/components/shell/page-header";
import { getTeam } from "@/lib/tokens";

import { useTeams } from "../queries";
import type { TeamSummary } from "../types";
import { ErrorState } from "./states";

export function seasonSpan(seasons: number[]): string {
  if (!seasons.length) return "–";
  const first = seasons[0];
  const last = seasons[seasons.length - 1];
  return first === last ? String(first) : `${first}–${last}`;
}

function TeamCard({ t }: { t: TeamSummary }) {
  const theme = getTeam(t.short_code);
  return (
    <li>
      <Link
        href={`/teams/${encodeURIComponent(t.short_code)}`}
        className="group relative flex min-h-[88px] items-center gap-3 overflow-hidden rounded-xl border border-border bg-card px-4 py-3 shadow-e1 outline-none transition-colors hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
      >
        {/* Team colour as accent only: a 3 px top border (§2.3). */}
        <span aria-hidden className="absolute inset-x-0 top-0 h-[3px]" style={{ backgroundColor: theme.primary }} />
        <TeamBadge team={t.short_code} size="lg" />
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold">{t.name}</h3>
          <p className="num mt-0.5 text-xs text-muted-foreground">
            {seasonSpan(t.seasons)} · {t.seasons.length} season{t.seasons.length === 1 ? "" : "s"}
          </p>
          {t.former_names.length > 0 && (
            <p className="mt-0.5 truncate text-[11px] text-faint">
              Formerly {t.former_names.filter((e) => e.name !== t.name).map((e) => e.name).join(", ") || t.former_names[0].name}
            </p>
          )}
        </div>
        {t.titles.length > 0 && (
          <span className="num flex shrink-0 items-center gap-1 text-sm font-semibold" title={`Titles: ${t.titles.join(", ")}`}>
            <Trophy aria-hidden className="size-4 text-gold-text" />
            {t.titles.length}
            <span className="sr-only"> title{t.titles.length === 1 ? "" : "s"}: {t.titles.join(", ")}</span>
          </span>
        )}
      </Link>
    </li>
  );
}

export function TeamsGrid() {
  const q = useTeams();
  if (q.isPending) return <GridPageSkeleton label="Loading teams" count={10} />;
  const header = <PageHeader overline="IPL" title="Teams" subtitle="Every franchise since 2008. Tap through for season-by-season finishes, results and head-to-heads." />;
  if (q.isError)
    return (
      <>
        {header}
        <ErrorState title="Couldn't load teams" error={q.error} onRetry={() => q.refetch()} />
      </>
    );
  const active = q.data.filter((t) => t.active).sort((a, b) => b.titles.length - a.titles.length || a.name.localeCompare(b.name));
  const defunct = q.data.filter((t) => !t.active).sort((a, b) => a.seasons[0] - b.seasons[0]);
  return (
    <>
      {header}
      <section aria-labelledby="active-h">
        <SectionHeader id="active-h" title={`Current franchises · ${active.length}`} />
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {active.map((t) => (
            <TeamCard key={t.id} t={t} />
          ))}
        </ul>
      </section>
      {defunct.length > 0 && (
        <section aria-labelledby="defunct-h" className="mt-8">
          <SectionHeader id="defunct-h" title={`Former franchises · ${defunct.length}`} />
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {defunct.map((t) => (
              <TeamCard key={t.id} t={t} />
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
