import { cn } from "@/lib/utils";

import { whatTeamNeeds } from "../format";
import type { ScenarioTeam } from "../types";
import { QualifyBar } from "./qualify-bar";
import { StatusPill, TeamName } from "./states";

/** Sort: clinched first, then by top-4 chance (incl. ties), points, then eliminated last. */
export function sortScenarioTeams(teams: ScenarioTeam[]): ScenarioTeam[] {
  return [...teams].sort(
    (a, b) =>
      Number(b.clinched_top4) - Number(a.clinched_top4) ||
      Number(a.eliminated) - Number(b.eliminated) ||
      b.p_top4_incl_ties - a.p_top4_incl_ties ||
      b.p_top4 - a.p_top4 ||
      b.points - a.points,
  );
}

export function ScenarioBadges({ team }: { team: ScenarioTeam }) {
  return (
    <span className="flex flex-wrap gap-1">
      {team.clinched_top2 ? (
        <StatusPill tone="gold">Top 2 ✓</StatusPill>
      ) : team.clinched_top4 ? (
        <StatusPill tone="positive">Qualified ✓</StatusPill>
      ) : null}
      {team.eliminated && <StatusPill tone="negative">Eliminated</StatusPill>}
    </span>
  );
}

/**
 * Per-team qualification odds (§4.7 Scenarios): P(top 4) and P(top 2) bars, clinched /
 * eliminated badges and a plain-words "what X needs" line. `pending` dims numbers with ≈ while
 * a new pick is being computed.
 */
export function ScenarioTeamList({
  teams,
  pending = false,
  className,
}: {
  teams: ScenarioTeam[];
  pending?: boolean;
  className?: string;
}) {
  const sorted = sortScenarioTeams(teams);
  return (
    <ol className={cn("divide-y divide-border overflow-hidden rounded-xl border border-border bg-card shadow-e1", className)} aria-busy={pending}>
      {sorted.map((t) => {
        const need = whatTeamNeeds(t, teams);
        return (
          <li key={t.team.id} className="px-3 py-3 md:px-4" data-testid={`scenario-${t.team.short_code}`}>
            <div className="flex items-center justify-between gap-2">
              <TeamName team={t.team} className="min-w-0" />
              <div className="flex shrink-0 items-center gap-2">
                <ScenarioBadges team={t} />
                <span className="num text-xs whitespace-nowrap text-muted-foreground">
                  <span className="font-semibold text-foreground">{t.points}</span> pts
                  {t.remaining > 0 && <> · max {t.max_points}</>}
                </span>
              </div>
            </div>
            <div className={cn("mt-2 grid gap-1.5 transition-opacity", pending && "opacity-70")}>
              <QualifyBar label="Top 4" sure={t.p_top4} withTies={t.p_top4_incl_ties} pending={pending} />
              <QualifyBar label="Top 2" sure={t.p_top2} withTies={t.p_top2_incl_ties} tone="gold" pending={pending} />
            </div>
            <p className={cn("mt-1.5 text-xs", need.tone === "eliminated" ? "text-muted-foreground" : "text-foreground/90")}>{need.text}</p>
          </li>
        );
      })}
    </ol>
  );
}
