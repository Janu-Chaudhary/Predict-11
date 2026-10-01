import { Check } from "lucide-react";

import { TeamBadge } from "@/components/player/team-badge";
import { cn } from "@/lib/utils";

import { shortDate } from "../format";
import type { ScenarioFixture, TeamRef } from "../types";

/**
 * "Pick the winners" list: each remaining fixture is a two-button toggle group (aria-pressed).
 * Tapping the picked side again clears the pick. For historical replays the real winner gets a
 * small "actual" tick so the owner can compare.
 */
export function FixturePicker({
  fixtures,
  teamsById,
  picks,
  onPick,
  disabled = false,
  className,
}: {
  fixtures: ScenarioFixture[];
  teamsById: Map<number, TeamRef>;
  picks: Map<number, number>;
  onPick: (matchId: number, winnerId: number | null) => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <ul className={cn("divide-y divide-border", className)}>
      {fixtures.map((f) => {
        const picked = picks.get(f.match_id) ?? null;
        const sides = [f.team1_id, f.team2_id];
        const names = sides.map((id) => teamsById.get(id)?.short_code ?? String(id));
        return (
          <li key={f.match_id} className="flex items-center gap-2 px-3 py-2 md:px-4">
            <div className="w-14 shrink-0 text-[11px] leading-4 text-muted-foreground">
              <div className="num font-semibold text-foreground">{f.match_number ? `M${f.match_number}` : "–"}</div>
              <div className="num">{shortDate(f.date)}</div>
            </div>
            <div role="group" aria-label={`Match ${f.match_number ?? ""}: ${names[0]} v ${names[1]}. Pick a winner`} className="grid flex-1 grid-cols-2 gap-1.5">
              {sides.map((id) => {
                const team = teamsById.get(id);
                const code = team?.short_code ?? String(id);
                const on = picked === id;
                const actual = f.actual_winner_id === id;
                return (
                  <button
                    key={id}
                    type="button"
                    disabled={disabled}
                    aria-pressed={on}
                    onClick={() => onPick(f.match_id, on ? null : id)}
                    className={cn(
                      "relative flex h-11 min-w-0 items-center gap-2 rounded-[10px] border px-2 text-sm font-medium outline-none transition-colors duration-120",
                      "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:opacity-50",
                      on ? "border-primary bg-primary/12 text-foreground" : "border-border bg-surface-2/60 text-muted-foreground hover:bg-surface-2 hover:text-foreground",
                      picked !== null && !on && "opacity-60",
                    )}
                  >
                    <TeamBadge team={code} />
                    {on && <span className="truncate">wins</span>}
                    {on && <Check aria-hidden className="ml-auto size-4 shrink-0 text-gold-text" />}
                    {actual && (
                      <span className={cn("text-overline ml-auto shrink-0 text-[10px] text-faint", on && "sr-only")} title="Actual result">
                        actual
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
