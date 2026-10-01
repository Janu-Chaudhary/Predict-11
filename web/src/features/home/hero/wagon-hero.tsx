"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

import styles from "../home.module.css";
import { FIELD, rayTiming, wagonRays } from "../lib/wagon-geometry";
import type { HomeMatch, Wagon } from "../types";
import { HeroCaption, LegendDot } from "./hero-caption";

/**
 * Hero A "Wagon-Wheel Bloom" (§7.1): the last match's top innings as scoring rays that draw
 * in ball order from the striker's end (stroke-dashoffset via the Web Animations API, ≈2.7 s),
 * boundary dots landing as each ray arrives, then still. Paths are computed during render, so
 * the geometry is server-rendered; the client only animates. Reduced motion → static wheel.
 */
export function WagonHero({ wagon, match, note }: { wagon: Wagon; match: HomeMatch | null; note: string }) {
  const reduce = useReducedMotion();
  const rays = useMemo(() => wagonRays(wagon.shots, wagon.left_handed), [wagon]);
  const gRef = useRef<SVGGElement>(null);
  const [armed, setArmed] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const g = gRef.current;
    if (!g) return;
    const paths = Array.from(g.querySelectorAll<SVGPathElement>("path[data-ray]"));
    const anims: Animation[] = [];
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tips = (on: boolean) => g.querySelectorAll<SVGCircleElement>("circle").forEach((c) => (c.style.opacity = on ? "1" : "0"));
    const raf = requestAnimationFrame(() => {
      setArmed(true);
      if (reduce || typeof paths[0]?.animate !== "function") {
        tips(true);
        setDone(true);
        return;
      }
      tips(false);
      let last = 0;
      paths.forEach((p, i) => {
        const runs = Number(p.dataset.runs);
        const L = p.getTotalLength();
        const { delay, duration } = rayTiming(i, runs);
        last = Math.max(last, delay + duration);
        const a = p.animate(
          [
            { strokeDasharray: `${L}`, strokeDashoffset: `${L}` },
            { strokeDasharray: `${L}`, strokeDashoffset: "0" },
          ],
          { duration, delay, easing: "cubic-bezier(0.2,0,0,1)", fill: "backwards" },
        );
        anims.push(a);
        const tip = g.querySelector<SVGCircleElement>(`circle[data-for="${p.dataset.ray}"]`);
        a.finished.then(() => tip && (tip.style.opacity = "1")).catch(() => {});
      });
      timer = setTimeout(() => setDone(true), last + 50);
    });
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(timer);
      anims.forEach((a) => a.cancel());
    };
  }, [rays, reduce]);

  const fours = wagon.shots.filter((s) => s.runs === 4).length;
  const sixes = wagon.shots.filter((s) => s.runs === 6).length;
  const score = `${wagon.runs}${wagon.not_out ? "*" : ""}${wagon.balls !== null ? ` (${wagon.balls})` : ""}`;
  const where = match ? (match.title === "Final" ? "Final" : match.title) : "Last match";
  const [legX, offX] = wagon.left_handed ? [150, -150] : [-150, 150];

  return (
    <figure className="m-0 mx-auto w-full max-w-[560px]" data-hero="A" data-hero-done={done || undefined}>
      <svg
        className={cn(styles.wheel, "block aspect-square w-full overflow-visible")}
        data-armed={armed}
        viewBox="-200 -200 400 400"
        role="img"
        aria-labelledby="wagon-title wagon-desc"
      >
        <title id="wagon-title">Wagon wheel: last match&apos;s top innings</title>
        <desc id="wagon-desc">
          {`${wagon.batter}, ${wagon.runs}${wagon.not_out ? " not out" : ""}${wagon.balls !== null ? ` off ${wagon.balls} balls` : ""}: ${wagon.shots.length} scoring shots including ${sixes} sixes and ${fours} fours.`}
        </desc>
        <ellipse className={styles.field} cx="0" cy="0" rx={FIELD.rx} ry={FIELD.ry} />
        <ellipse className={styles.ring} cx="0" cy="0" rx="98" ry="92" />
        <rect className={styles.strip} x="-7" y="-26" width="14" height="52" rx="2" />
        <text className={styles.side} x={legX} y="-150" textAnchor="middle">
          LEG
        </text>
        <text className={styles.side} x={offX} y="-150" textAnchor="middle">
          OFF
        </text>
        <g ref={gRef}>
          {rays.map((r, i) => (
            <path
              key={r.key}
              data-ray={i}
              data-runs={wagon.shots[i].runs}
              d={r.d}
              className={cn(styles.ray, styles[r.tone])}
              tabIndex={-1}
            >
              <title>{r.title}</title>
            </path>
          ))}
          {rays.map((r, i) =>
            r.tip ? (
              <circle
                key={`t-${r.key}`}
                data-for={i}
                cx={r.tip.x}
                cy={r.tip.y}
                r={2.5}
                className={cn(styles.tip, r.tone === "r6" ? styles.tip6 : styles.tip4)}
              />
            ) : null,
          )}
        </g>
      </svg>
      <HeroCaption
        lead={
          <>
            Last match · {where} ·{" "}
            <b className="font-semibold text-foreground num">
              {wagon.batter} {score}
            </b>
          </>
        }
        legend={
          <>
            <LegendDot line colour="var(--faint)">1–3</LegendDot>
            <LegendDot line colour="var(--brand)">4</LegendDot>
            <LegendDot line colour="var(--primary)">6</LegendDot>
          </>
        }
        note={`${note} Source: ${wagon.source}.`}
      />
    </figure>
  );
}
