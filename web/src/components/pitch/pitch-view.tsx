import type { Player } from "@/lib/mock";
import { ROLES, ROLE_THEME, getTeam } from "@/lib/tokens";
import { cn } from "@/lib/utils";

import type { PlayerStatus } from "@/components/player/player-card";
import { Lock } from "lucide-react";

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
 * Stylised field with one row per role (§4.3). Radius 16, pitch green is the only fill;
 * tokens carry team colour, C (gold) / VC (gradient ring) roundels and a lock glyph.
 * Tapping a token (onSelect) opens the player sheet in the builder.
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
      className={cn("relative isolate overflow-hidden rounded-2xl bg-pitch px-2 py-5 text-white", className)}
    >
      {/* Field markings: mown stripes, 30-yard circle, pitch strip. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[repeating-linear-gradient(180deg,transparent_0_44px,var(--pitch-stripe)_44px_88px)] opacity-60" />
        <div className="absolute top-1/2 left-1/2 aspect-square w-[78%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/20" />
        <div className="absolute top-1/2 left-1/2 h-[34%] w-[9%] -translate-x-1/2 -translate-y-1/2 rounded-sm bg-[#d9c79a]/40" />
        <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-black/15 to-transparent" />
      </div>

      <ol className="flex flex-col gap-4">
        {ROLES.map((role) => {
          const row = players.filter((p) => p.role === role);
          return (
            <li key={role}>
              <h3 className="text-overline mb-1.5 text-center text-white/85">
                {ROW_LABEL[role]} <span className="num">({row.length})</span>
              </h3>
              <ul className="flex flex-wrap justify-center gap-x-0.5 gap-y-2 sm:gap-x-1">
                {row.map((p) => {
                  const status = statuses[p.id] ?? null;
                  const team = getTeam(p.team);
                  const selected = selectedId === p.id;
                  return (
                    <li key={p.id} className="w-[4.5rem] sm:w-24">
                      <button
                        type="button"
                        onClick={() => onSelect?.(p.id)}
                        aria-pressed={selected}
                        aria-label={`${p.name}, ${team.name}, ${ROLE_THEME[p.role].label}, ${p.credits} credits, median ${p.projection.median} points${status ? `, ${status}` : ""}${p.captain ? ", captain" : ""}${p.viceCaptain ? ", vice-captain" : ""}`}
                        className={cn(
                          "group flex min-h-11 w-full flex-col items-center gap-1 rounded-lg p-1 outline-none focus-visible:ring-2 focus-visible:ring-primary",
                          status === "excluded" && "opacity-45",
                        )}
                      >
                        <span className="relative">
                          <span
                            className={cn(
                              "font-condensed flex size-11 items-center justify-center rounded-full text-sm font-bold ring-2 ring-white/60 transition-transform duration-200 ease-emphasized group-hover:scale-105 motion-reduce:transition-none sm:size-12",
                              selected && "ring-[3px] ring-white",
                              status === "locked" && "ring-primary",
                            )}
                            style={{ backgroundColor: team.primary, color: team.onPrimary }}
                          >
                            {initials(p.name)}
                          </span>
                          {p.captain && (
                            <span aria-hidden className="font-condensed absolute -top-1 -right-1.5 flex size-5 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">
                              C
                            </span>
                          )}
                          {p.viceCaptain && (
                            <span aria-hidden className="bg-brand-gradient absolute -top-1 -right-2 flex size-5 items-center justify-center rounded-full p-[1.5px]">
                              <span className="font-condensed flex size-full items-center justify-center rounded-full bg-black/80 text-[11px] font-bold text-white">VC</span>
                            </span>
                          )}
                          {status === "locked" && (
                            <span aria-hidden className="absolute -bottom-0.5 -left-1 flex size-[18px] items-center justify-center rounded-full bg-primary text-primary-foreground">
                              <Lock className="size-3" strokeWidth={2.25} />
                            </span>
                          )}
                        </span>
                        <span className="w-full truncate rounded bg-black/55 px-1 text-center text-[11px] leading-4 font-medium">
                          {p.name.split(" ").slice(-1)[0]}
                        </span>
                        <span aria-hidden className="num text-[11px] leading-none text-white/90">
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
