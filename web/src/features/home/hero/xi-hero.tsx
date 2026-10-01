"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { NumberRoll } from "@/components/loaders/number-roll";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { useResolvedTheme } from "@/hooks/use-resolved-theme";
import { ROLE_THEME, TIER_CLASS, teamChartColour, tierFor } from "@/lib/tokens";
import { cn } from "@/lib/utils";

import styles from "../home.module.css";
import { initials, layoutXI, pickRows, type XILayout, type XY } from "../lib/xi-layout";
import type { HomeMatch, XI, XIPlayer } from "../types";
import { HeroCaption } from "./hero-caption";

const fmt = (n: number) => Math.round(n).toLocaleString("en-IN");

/**
 * Hero B "XI Assembles" (§7.1): 22 tokens start on two team benches; the 11 picks fly onto
 * WK/BAT/AR/BOWL rows (Web Animations arc with a slight overshoot, 110 ms stagger), the count
 * and points roll, then C (gold) and VC (gradient ring) pop on. ≈2.6 s, then still. The
 * stage has a fixed aspect ratio so there is no layout shift. Reduced motion → final frame
 * with a 120 ms fade.
 */
export function XIHero({ xi, match, note }: { xi: XI; match: HomeMatch | null; note: string }) {
  const reduce = useReducedMotion();
  const theme = useResolvedTheme();
  const stageRef = useRef<HTMLDivElement>(null);
  const tokRefs = useRef(new Map<string, HTMLDivElement>());
  const [layout, setLayout] = useState<XILayout | null>(null);
  const [landed, setLanded] = useState<XIPlayer[]>([]);
  const [total, setTotal] = useState(0);
  const [rowsOn, setRowsOn] = useState(false);
  const [done, setDone] = useState(false);

  const teams = xi.teams.slice(0, 2);
  const picks = useMemo(() => pickRows(xi.players).flat(), [xi]);
  const finalTotal = xi.total;

  // Measure the stage (and re-measure on resize).
  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const measure = () => setLayout(layoutXI(xi.players, teams, stage.clientWidth, stage.clientHeight));
    const ro = new ResizeObserver(measure);
    ro.observe(stage);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [xi]);

  const firstLayout = layout !== null;
  useEffect(() => {
    if (!layout) return;
    const stage = stageRef.current;
    const timers: ReturnType<typeof setTimeout>[] = [];
    const anims: Animation[] = [];
    const at = (ms: number, fn: () => void) => timers.push(setTimeout(fn, ms));
    const el = (p: XIPlayer) => tokRefs.current.get(p.id);
    const place = (e: HTMLElement | undefined, xy: XY | undefined) => {
      if (e && xy) e.style.transform = `translate(${xy[0]}px, ${xy[1]}px)`;
    };
    const set = (e: HTMLElement | undefined, attr: string, v: boolean) => e?.setAttribute(attr, String(v));
    const badge = (p: XIPlayer) => el(p)?.querySelector<HTMLElement>("[data-cv]") ?? null;

    const showFinal = () => {
      for (const p of xi.players) {
        const e = el(p);
        set(e, "data-bench", !p.picked);
        set(e, "data-dim", !p.picked);
        set(e, "data-on", p.picked);
        place(e, p.picked ? layout.pitch.get(p.id) : layout.bench.get(p.id));
        badge(p)?.setAttribute("data-show", "true");
      }
      setRowsOn(true);
      setLanded(picks);
      setTotal(finalTotal);
      setDone(true);
    };

    if (done || reduce || typeof stage?.animate !== "function") {
      // already played (resize) or reduced motion: jump to the final frame
      const raf = requestAnimationFrame(() => {
        showFinal();
        if (!done && stage?.animate) anims.push(stage.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 120 }));
      });
      return () => {
        cancelAnimationFrame(raf);
        anims.forEach((a) => a.cancel());
      };
    }

    // Reset to benches.
    xi.players.forEach((p, i) => {
      const e = el(p);
      set(e, "data-bench", true);
      set(e, "data-dim", false);
      set(e, "data-on", false);
      place(e, layout.bench.get(p.id));
      badge(p)?.setAttribute("data-show", "false");
      if (e) anims.push(e.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 240, delay: i * 18, easing: "ease-out", fill: "backwards" }));
    });
    at(500, () => {
      setRowsOn(true);
      xi.players.filter((p) => !p.picked).forEach((p) => set(el(p), "data-dim", true));
    });
    const STAGGER = 110;
    const DUR = 560;
    const START = 650;
    const got: XIPlayer[] = [];
    picks.forEach((p, i) => {
      const e = el(p);
      const from = layout.bench.get(p.id);
      const to = layout.pitch.get(p.id);
      if (!e || !from || !to) return;
      at(START + i * STAGGER, () => {
        set(e, "data-bench", false);
        // arc toward the field centre on the way in; spring-ish overshoot (bounce ≈ .15)
        const mid: XY = [(from[0] + to[0]) / 2, Math.min(from[1], to[1]) - 30];
        const a = e.animate(
          [
            { transform: `translate(${from[0]}px, ${from[1]}px)` },
            { transform: `translate(${mid[0]}px, ${mid[1]}px)`, offset: 0.45 },
            { transform: `translate(${to[0]}px, ${to[1]}px)` },
          ],
          { duration: DUR, easing: "cubic-bezier(0.34, 1.25, 0.64, 1)" },
        );
        place(e, to);
        anims.push(a);
        a.finished
          .then(() => {
            set(e, "data-on", true);
            got.push(p);
            setLanded([...got]);
            setTotal(got.reduce((s, q) => s + q.points, 0));
          })
          .catch(() => {});
      });
    });
    const end = START + (picks.length - 1) * STAGGER + DUR + 250;
    at(end, () => {
      picks
        .filter((p) => p.captain)
        .forEach((p, i) => {
          const b = badge(p);
          if (!b) return;
          anims.push(
            b.animate(
              [
                { transform: "scale(.6)", opacity: 0 },
                { transform: "scale(1.12)", opacity: 1, offset: 0.7 },
                { transform: "scale(1)", opacity: 1 },
              ],
              { duration: 220, delay: i * 120, easing: "cubic-bezier(0.2,0,0,1)", fill: "backwards" },
            ),
          );
          b.setAttribute("data-show", "true");
        });
    });
    at(end + 380, () => setTotal(finalTotal));
    at(end + 760, () => setDone(true));
    return () => {
      timers.forEach(clearTimeout);
      anims.forEach((a) => a.cancel());
    };
    // Re-run only for a new XI / layout size / motion preference; `done` is read, not tracked.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout, reduce, xi]);

  const split = teams.map((t) => `${t} ${landed.filter((p) => p.team === t).length}`).join(" · ");
  const cap = picks.find((p) => p.captain === "C");
  const vc = picks.find((p) => p.captain === "VC");
  const aria = `Best fantasy XI for ${match ? `${match.title} ${match.season}` : "the match"}: ${picks
    .map((p) => `${p.short_name} (${p.role}${p.captain ? `, ${p.captain === "C" ? "captain" : "vice-captain"}` : ""})`)
    .join(", ")}. ${fmt(finalTotal)} points.`;

  return (
    <figure className="m-0 mx-auto w-full max-w-[720px]" data-hero="B" data-hero-done={done || undefined}>
      <div ref={stageRef} className={styles.stage} role="img" aria-label={aria}>
        {layout && (
          <div
            className={styles.pitchField}
            style={{ left: layout.field.left, top: layout.field.top, width: layout.field.width, height: layout.field.height }}
          />
        )}
        {layout?.rowLabels.map((r) => (
          <div
            key={r.role}
            className={styles.rowLabel}
            data-show={rowsOn}
            style={{ left: r.left, top: r.top, ["--c" as string]: ROLE_THEME[r.role].hex }}
          >
            {r.role}
          </div>
        ))}
        {layout?.benchLabels.map((b) => (
          <div key={b.team} className={cn(styles.benchLabel, "text-overline text-muted-foreground")} style={{ left: b.left, top: b.top }}>
            <i
              aria-hidden
              className="mr-1.5 inline-block size-2 rounded-full"
              style={{ background: teamChartColour(b.team, theme) }}
            />
            {b.team} XI
          </div>
        ))}
        {firstLayout &&
          xi.players.map((p) => {
            const tier = TIER_CLASS[tierFor(p.points)];
            return (
              <div
                key={p.id}
                ref={(n) => {
                  if (n) tokRefs.current.set(p.id, n);
                  else tokRefs.current.delete(p.id);
                }}
                className={styles.tok}
                data-bench="true"
                title={`${p.name} · ${p.team} · ${p.role} · ${p.points} pts`}
              >
                <div className={styles.tokIn}>
                  <div className={styles.av} style={{ ["--c" as string]: teamChartColour(p.team, theme) }}>
                    {initials(p.short_name)}
                    {p.captain && (
                      <span data-cv className={cn(styles.cv, p.captain === "C" ? styles.cvC : styles.cvVC)}>
                        {p.captain}
                      </span>
                    )}
                  </div>
                  <div className={styles.nm}>{p.short_name}</div>
                  <div className={cn(styles.pt, tier.bg, tier.text)}>{Math.round(p.points)}</div>
                </div>
              </div>
            );
          })}
      </div>
      <div className="mt-3 flex items-center gap-3 rounded-xl border border-border bg-card px-3.5 py-2.5" aria-live="polite">
        <div>
          <div className="text-overline text-muted-foreground">Players</div>
          <div className="font-display text-xl leading-6 font-bold [font-stretch:75%] num">{landed.length}/11</div>
        </div>
        <div className="text-xs text-muted-foreground num">{split}</div>
        <div className="ml-auto text-right">
          <div className="text-overline text-muted-foreground">Best XI · fantasy pts</div>
          <NumberRoll value={total} format={fmt} label={`${fmt(total)} points`} className="font-display text-[40px] font-bold [font-stretch:75%]" />
        </div>
      </div>
      <HeroCaption
        lead={
          <>
            {match ? `${match.title} · ${match.team1.short_code} v ${match.team2.short_code}` : "Best XI"} · actual points
            {cap ? ` · C ${cap.short_name}` : ""}
            {vc ? ` · VC ${vc.short_name}` : ""} (C ×2, VC ×1.5)
          </>
        }
        note={`${note} Picked in hindsight from persisted points, not a prediction.`}
      />
    </figure>
  );
}
