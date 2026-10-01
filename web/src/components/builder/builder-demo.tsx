"use client";

import { useMemo, useState } from "react";

import { PitchView } from "@/components/pitch/pitch-view";
import { PlayerCard, type PlayerStatus } from "@/components/player/player-card";
import { MOCK_XI } from "@/lib/mock";

const CREDIT_CAP = 100;

export function BuilderDemo() {
  const [statuses, setStatuses] = useState<Record<string, PlayerStatus>>({});
  const [selectedId, setSelectedId] = useState<string | null>(MOCK_XI[0].id);

  const toggle = (id: string, s: Exclude<PlayerStatus, null>) =>
    setStatuses((prev) => ({ ...prev, [id]: prev[id] === s ? null : s }));

  const used = useMemo(() => MOCK_XI.reduce((sum, p) => sum + p.credits, 0), []);
  const selected = MOCK_XI.find((p) => p.id === selectedId) ?? null;

  return (
    <div className="flex flex-col gap-4">
      <div
        className="sticky top-14 z-30 -mx-4 flex items-center justify-between border-b bg-background/95 px-4 py-2 text-sm backdrop-blur md:static md:mx-0 md:rounded-lg md:border"
        aria-label="Team summary"
        role="group"
      >
        <span>
          <span className="font-semibold tabular-nums">{(CREDIT_CAP - used).toFixed(1)}</span>{" "}
          <span className="text-muted-foreground">credits left</span>
        </span>
        <span className="text-muted-foreground">11/11 · roles valid</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <PitchView players={MOCK_XI} statuses={statuses} selectedId={selectedId} onSelect={setSelectedId} />
        <aside aria-label="Selected player" className="lg:sticky lg:top-20 lg:self-start">
          {selected ? (
            <PlayerCard
              player={selected}
              status={statuses[selected.id] ?? null}
              onToggleLock={(id) => toggle(id, "locked")}
              onToggleExclude={(id) => toggle(id, "excluded")}
            />
          ) : (
            <p className="text-sm text-muted-foreground">Tap a player on the pitch to see their card.</p>
          )}
        </aside>
      </div>

      <section aria-labelledby="all-players" className="flex flex-col gap-3">
        <h2 id="all-players" className="text-sm font-semibold">
          All players <span className="font-normal text-muted-foreground">(mock data)</span>
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {MOCK_XI.map((p) => (
            <PlayerCard
              key={p.id}
              player={p}
              status={statuses[p.id] ?? null}
              onToggleLock={(id) => toggle(id, "locked")}
              onToggleExclude={(id) => toggle(id, "excluded")}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
