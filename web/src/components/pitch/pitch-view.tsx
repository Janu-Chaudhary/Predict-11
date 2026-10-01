import type { Player } from "@/lib/mock";
import { ROLES, ROLE_THEME, TEAMS } from "@/lib/tokens";
import { cn } from "@/lib/utils";

import type { PlayerStatus } from "@/components/player/player-card";

const ROW_LABEL = { WK: "Wicket-keepers", BAT: "Batters", AR: "All-rounders", BOWL: "Bowlers" } as const;

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/**
 * Stylised field with one row per role. Skeleton for the pitch-view team builder:
 * tapping a player (onSelect) will later open the bottom-sheet card.
 */
export function PitchView({
  players,
  statuses = {},
  selectedId,
  onSelect,
  className,
}: {
  players: Player[];
  statuses?: Record<string, PlayerStatus>;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  className?: string;
}) {
  return (
    <section
      aria-label="Pitch view"
      className={cn(
        "relative isolate overflow-hidden rounded-2xl bg-pitch px-2 py-4 text-white shadow-inner",
        className,
      )}
    >
      {/* Field markings: mown stripes, 30-yard circle, pitch strip. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[repeating-linear-gradient(180deg,transparent_0_44px,rgb(255_255_255/0.05)_44px_88px)]" />
        <div className="absolute top-1/2 left-1/2 aspect-square w-[78%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/25" />
        <div className="absolute top-1/2 left-1/2 h-[34%] w-[9%] -translate-x-1/2 -translate-y-1/2 rounded-sm bg-[#d9c79a]/45" />
      </div>

      <ol className="flex flex-col gap-4">
        {ROLES.map((role) => {
          const row = players.filter((p) => p.role === role);
          return (
            <li key={role}>
              <h3 className="mb-1.5 text-center text-[10px] font-semibold tracking-widest text-white/80 uppercase">
                {ROW_LABEL[role]} <span className="tabular-nums">({row.length})</span>
              </h3>
              <ul className="flex flex-wrap justify-center gap-x-0.5 gap-y-2 sm:gap-x-1">
                {row.map((p) => {
                  const status = statuses[p.id] ?? null;
                  const team = TEAMS[p.team];
                  const selected = selectedId === p.id;
                  return (
                    <li key={p.id} className="w-[4.25rem] sm:w-24">
                      <button
                        type="button"
                        onClick={() => onSelect?.(p.id)}
                        aria-pressed={selected}
                        aria-label={`${p.name}, ${team.name}, ${ROLE_THEME[p.role].label}, ${p.credits} credits, median ${p.projection.median} points${status ? `, ${status}` : ""}${p.captain ? ", captain" : ""}${p.viceCaptain ? ", vice-captain" : ""}`}
                        className={cn(
                          "group flex w-full flex-col items-center gap-1 rounded-lg p-1 outline-none focus-visible:ring-2 focus-visible:ring-white",
                          status === "excluded" && "opacity-50",
                        )}
                      >
                        <span className="relative">
                          <span
                            className={cn(
                              "flex size-11 items-center justify-center rounded-full text-xs font-bold ring-2 ring-white/70 transition-transform group-hover:scale-105 sm:size-12",
                              selected && "ring-4 ring-white",
                              status === "locked" && "ring-amber-300",
                            )}
                            style={{ backgroundColor: team.primary, color: team.onPrimary }}
                          >
                            {initials(p.name)}
                          </span>
                          {(p.captain || p.viceCaptain) && (
                            <span
                              aria-hidden
                              className="absolute -top-1 -right-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-white px-0.5 text-[9px] font-bold text-black"
                            >
                              {p.captain ? "C" : "VC"}
                            </span>
                          )}
                        </span>
                        <span className="w-full truncate rounded bg-black/55 px-1 text-center text-[10px] leading-4 font-medium">
                          {p.name.split(" ").slice(-1)[0]}
                        </span>
                        <span aria-hidden className="text-[10px] leading-none text-white/85 tabular-nums">
                          {p.projection.median} pts
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
