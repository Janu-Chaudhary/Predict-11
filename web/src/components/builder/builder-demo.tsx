"use client";

import { RefreshCw } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { NumberRoll } from "@/components/loaders/number-roll";
import { StumpsLoader } from "@/components/loaders/stumps-loader";
import { PitchView } from "@/components/pitch/pitch-view";
import { PlayerCard, type PlayerStatus } from "@/components/player/player-card";
import { SectionHeader } from "@/components/shell/page-header";
import { Button } from "@/components/ui/button";
import { useLoaderVisibility, INLINE_LOADER_TIMING } from "@/hooks/use-loader-visibility";
import { MOCK_XI } from "@/lib/mock";

const CREDIT_CAP = 100;

export function BuilderDemo() {
  const [statuses, setStatuses] = useState<Record<string, PlayerStatus>>({});
  const [selectedId, setSelectedId] = useState<string | null>(MOCK_XI[0].id);
  const [pending, setPending] = useState(false);
  const [projected, setProjected] = useState(() => MOCK_XI.reduce((s, p) => s + p.projection.median, 0));
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { visible: showLoader } = useLoaderVisibility(pending, INLINE_LOADER_TIMING);

  const toggle = (id: string, s: Exclude<PlayerStatus, null>) =>
    setStatuses((prev) => ({ ...prev, [id]: prev[id] === s ? null : s }));

  const used = useMemo(() => MOCK_XI.reduce((sum, p) => sum + p.credits, 0), []);
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const p of MOCK_XI) c[p.team] = (c[p.team] ?? 0) + 1;
    return c;
  }, []);
  const selected = MOCK_XI.find((p) => p.id === selectedId) ?? null;

  // Demo only: simulates a server re-optimise so the inline loader + digit roll can be seen.
  const reoptimise = () => {
    if (timer.current) clearTimeout(timer.current);
    setPending(true);
    timer.current = setTimeout(() => {
      setProjected((p) => Math.max(300, p + Math.round((Math.random() - 0.4) * 30)));
      setPending(false);
    }, 1200);
  };

  return (
    <div className="flex flex-col gap-4">
      <div
        role="group"
        aria-label="Team summary"
        aria-busy={pending}
        className="glass sticky top-14 z-30 -mx-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border px-4 py-2.5 text-[13px] md:mx-0 md:rounded-xl md:border"
      >
        <div className="num flex flex-wrap items-center gap-x-2">
          <b className="font-semibold">11/11</b>
          <span className="text-faint">·</span>
          <span>
            <b className="font-semibold">{used.toFixed(1)}</b>
            <span className="text-muted-foreground">/{CREDIT_CAP} cr</span>
          </span>
          <span className="text-faint">·</span>
          <span className="text-muted-foreground">
            {Object.entries(counts)
              .map(([t, n]) => `${t} ${n}`)
              .join(" ")}
          </span>
          <span className="text-faint">·</span>
          <span className="text-muted-foreground">roles ✓</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="num">
            <span className="text-muted-foreground">Proj </span>
            {pending && <span className="text-muted-foreground">≈</span>}
            <NumberRoll value={projected} className="font-semibold" label={`Projected ${projected} points`} />
          </span>
          <Button variant="outline" onClick={reoptimise} disabled={pending} className="h-9 rounded-[10px]">
            {showLoader ? <StumpsLoader size={22} label={null} /> : <RefreshCw aria-hidden />}
            {pending ? "Re-optimising…" : "Re-optimise"}
          </Button>
        </div>
        <span className="sr-only" aria-live="polite">
          {pending ? "Re-optimising" : `XI updated, projected ${projected}`}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <PitchView players={MOCK_XI} statuses={statuses} selectedId={selectedId} onSelect={setSelectedId} />
        <aside aria-label="Selected player" className="lg:sticky lg:top-32 lg:self-start">
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

      <section aria-labelledby="all-players" className="flex flex-col gap-1">
        <SectionHeader id="all-players" title="All players · sample data" />
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
