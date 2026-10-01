"use client";

import { useEffect, useRef, useState } from "react";

import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { useResolvedTheme } from "@/hooks/use-resolved-theme";
import { pickMatchColours } from "@/lib/tokens";

import styles from "../home.module.css";
import {
  PAL_SIZE,
  TIMELINE,
  buildParticles,
  easeOut,
  makeScale,
  settle,
  stepParticles,
  sx,
  sy,
  wormPoints,
  yTicks,
  type Particles,
  type Scale,
} from "../lib/worm-geometry";
import type { Worm } from "../types";
import { HeroCaption, LegendDot } from "./hero-caption";

type Colours = {
  team: [string, string];
  dashed: [boolean, boolean];
  faint: string;
  fg: string;
  brand: string;
  gold: string;
  neg: string;
  border: string;
  page: string;
  mono: string;
};

function readColours(el: HTMLElement, team: [string, string], dashed: [boolean, boolean]): Colours {
  const cs = getComputedStyle(el);
  const v = (n: string) => cs.getPropertyValue(n).trim();
  return {
    team,
    dashed,
    faint: v("--faint"),
    fg: v("--foreground"),
    brand: v("--brand"),
    gold: v("--primary"),
    neg: v("--negative"),
    border: v("--border"),
    page: v("--background"),
    mono: v("--font-geist-mono") || "ui-monospace, monospace",
  };
}

/**
 * Hero C "Ball Field" (§7.1): every delivery of the match is a particle (dots faint, 4s violet,
 * 6s gold, wickets red) that drifts in like floodlight dust and settles onto the worm, then the
 * lines stroke in and everything stops (no idle loop). Canvas 2D + typed arrays, DPR ≤ 2,
 * paused when hidden or off-screen. Reduced motion → the settled final frame only.
 */
export function WormHero({ worm, note }: { worm: Worm; note: string }) {
  const reduce = useReducedMotion();
  const theme = useResolvedTheme();
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [labels, setLabels] = useState<{ show: boolean; pos: { left: number; top: number }[] }>({ show: false, pos: [] });
  const [done, setDone] = useState(false);

  const inns = worm.innings.slice(0, 2);
  const homeCode = inns[0]?.team.short_code ?? "";
  const awayCode = inns[1]?.team.short_code ?? homeCode;
  const pick = pickMatchColours(homeCode, awayCode, theme);
  const c0 = pick.home.color;
  const c1 = pick.away.color;
  // the second innings is always dashed: a shape cue in addition to colour (§2.3)
  const series = { team: [c0, c1] as [string, string], dashed: [false, true] as [boolean, boolean] };

  useEffect(() => {
    const wrap = wrapRef.current;
    const cv = canvasRef.current;
    if (!wrap || !cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    const team: [string, string] = [c0, c1];
    const dashed: [boolean, boolean] = [false, true];
    let C = readColours(wrap, team, dashed);
    const pts = wormPoints(worm);
    let s: Scale;
    let P: Particles;
    let raf = 0;
    let t0 = 0;
    let finished = false;
    let visible = true;
    let labelsShown = false;

    const size = () => {
      const r = wrap.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      cv.width = Math.round(r.width * dpr);
      cv.height = Math.round(r.height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      s = makeScale(r.width, r.height, worm.y_max);
      P = buildParticles(worm, s);
    };

    const placeLabels = () => {
      const ends = pts.map((p) => p[p.length - 1]);
      const hi = ends.length > 1 && ends[1].y > ends[0].y ? 1 : 0;
      const pos = ends.map((e, k) => {
        const above = k === hi || ends.length === 1;
        const top = above ? sy(s, e.y) - 24 : Math.min(s.H - s.M.b - 20, sy(s, e.y) + Math.max(30, s.H * 0.3));
        return { left: sx(s, e.x) - (above ? 10 : 4), top: Math.max(s.M.t + 8, top) };
      });
      setLabels({ show: true, pos });
    };

    const drawAxes = (alpha: number) => {
      const { M, W, H } = s;
      ctx.fillStyle = C.fg;
      ctx.globalAlpha = alpha * 0.04;
      ctx.fillRect(sx(s, 0), M.t, sx(s, 6) - sx(s, 0), H - M.t - M.b);
      ctx.fillRect(sx(s, 16), M.t, sx(s, 20) - sx(s, 16), H - M.t - M.b);
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = C.border;
      ctx.lineWidth = 1;
      ctx.font = `500 11px ${C.mono}`;
      ctx.fillStyle = C.faint;
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      for (const y of yTicks(worm.y_max)) {
        const yy = Math.round(sy(s, y)) + 0.5;
        ctx.beginPath();
        ctx.moveTo(M.l, yy);
        ctx.lineTo(W - M.r, yy);
        ctx.stroke();
        ctx.fillText(String(y), M.l - 6, sy(s, y));
      }
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      for (const o of [0, 6, 10, 16, 20]) ctx.fillText(String(o), sx(s, o), H - M.b + 8);
      ctx.textAlign = "left";
      ctx.fillText("PP", sx(s, 0) + 4, M.t + 4);
      ctx.textBaseline = "bottom";
      ctx.fillText("DEATH", sx(s, 16) + 4, H - M.b - 4);
      ctx.globalAlpha = 1;
    };

    const drawLines = (prog: number) => {
      pts.forEach((line, k) => {
        const n = Math.max(1, Math.floor(prog * (line.length - 1)));
        ctx.strokeStyle = C.team[k];
        ctx.lineWidth = 2;
        ctx.lineJoin = "round";
        ctx.setLineDash(C.dashed[k] ? [6, 4] : []); // shape cue in addition to colour
        ctx.beginPath();
        ctx.moveTo(sx(s, 0), sy(s, 0));
        for (let i = 1; i <= n; i++) ctx.lineTo(sx(s, line[i].x), sy(s, line[i].y));
        ctx.stroke();
        ctx.setLineDash([]);
        const upto = line[n].x;
        for (const b of worm.innings[k].balls) {
          if (b.kind !== "wicket" || b.x > upto) continue;
          ctx.beginPath();
          ctx.arc(sx(s, b.x), sy(s, b.runs), 4.5, 0, 7);
          ctx.fillStyle = C.page;
          ctx.fill();
          ctx.beginPath();
          ctx.arc(sx(s, b.x), sy(s, b.runs), 3, 0, 7);
          ctx.fillStyle = C.team[k];
          ctx.fill();
        }
      });
    };

    const drawParticles = (alphaReal: number, alphaDust: number) => {
      const pal = [C.team[0], C.team[1], C.faint, C.brand, C.gold, C.neg];
      for (let c = 0; c < PAL_SIZE; c++) {
        ctx.fillStyle = pal[c];
        ctx.globalAlpha = c < 2 ? alphaDust : c === 2 ? alphaReal * 0.7 : alphaReal;
        ctx.beginPath();
        for (let i = 0; i < P.n; i++) {
          if (P.col[i] !== c) continue;
          ctx.moveTo(P.px[i] + P.rad[i], P.py[i]);
          ctx.arc(P.px[i], P.py[i], P.rad[i], 0, 6.2832);
        }
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    };

    const drawFinal = () => {
      ctx.clearRect(0, 0, s.W, s.H);
      drawAxes(1);
      settle(P);
      drawParticles(1, 0.35);
      drawLines(1);
      placeLabels();
      finished = true;
      setDone(true);
    };

    const frame = (now: number) => {
      if (!t0) t0 = now;
      const t = now - t0;
      ctx.clearRect(0, 0, s.W, s.H);
      drawAxes(easeOut((t - TIMELINE.axesIn) / 900));
      const conv = stepParticles(P, t);
      const fadeIn = easeOut(t / 600);
      drawParticles(fadeIn * (0.55 + 0.45 * conv), fadeIn * (0.6 - 0.25 * conv));
      if (t > TIMELINE.lineStart) drawLines(easeOut((t - TIMELINE.lineStart) / TIMELINE.line));
      if (t > TIMELINE.labels && !labelsShown) {
        labelsShown = true;
        placeLabels();
      }
      if (t < TIMELINE.end) raf = requestAnimationFrame(frame);
      else drawFinal();
    };

    const start = () => {
      cancelAnimationFrame(raf);
      size();
      if (reduce) return drawFinal();
      t0 = 0;
      raf = requestAnimationFrame(frame);
    };

    // Pause when the tab is hidden or the hero scrolls away; resume where it was.
    const resume = () => {
      if (!finished && visible && !document.hidden) {
        t0 = 0;
        raf = requestAnimationFrame(frame);
      }
    };
    const onVis = () => (document.hidden ? cancelAnimationFrame(raf) : resume());
    document.addEventListener("visibilitychange", onVis);
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      if (visible) resume();
      else cancelAnimationFrame(raf);
    });
    io.observe(wrap);
    let rt: ReturnType<typeof setTimeout> | undefined;
    let lastW = wrap.clientWidth;
    const ro = new ResizeObserver(() => {
      if (Math.abs(wrap.clientWidth - lastW) < 2) return;
      lastW = wrap.clientWidth;
      clearTimeout(rt);
      rt = setTimeout(() => {
        cancelAnimationFrame(raf);
        size();
        drawFinal();
      }, 120);
    });
    ro.observe(wrap);

    // Wait for fonts so the canvas axis labels use Geist Mono.
    let cancelled = false;
    (document.fonts?.ready ?? Promise.resolve()).then(() => {
      if (cancelled) return;
      C = readColours(wrap, team, dashed);
      start();
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      clearTimeout(rt);
      io.disconnect();
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [worm, reduce, c0, c1]);

  const m = worm.match;
  const winner = m.winner_id;
  const aria = `Worm chart, ${m.title} ${m.season}. ${inns
    .map((i) => `${i.team.name} ${i.runs} for ${i.wickets} in ${i.overs} overs`)
    .join("; ")}. ${m.result}.`;

  return (
    <figure className="m-0 w-full" data-hero="C" data-hero-done={done || undefined}>
      <div ref={wrapRef} className="relative aspect-[358/300] w-full sm:aspect-[16/10]">
        <canvas ref={canvasRef} role="img" aria-label={aria} className="absolute inset-0 block size-full" />
        {inns.map((inn, k) => (
          <div
            key={inn.innings}
            className={styles.wormLabel}
            data-show={labels.show}
            data-dashed={series.dashed[k]}
            style={{ left: labels.pos[k]?.left ?? 0, top: labels.pos[k]?.top ?? 0, ["--c" as string]: series.team[k] }}
            aria-hidden
          >
            <b className="block font-display text-[22px] leading-6 font-bold [font-stretch:75%] num">
              {inn.team.short_code} {inn.runs}/{inn.wickets}
            </b>
            <span className="text-xs text-muted-foreground">
              {inn.overs} ov{inn.team.id === winner ? ` · ${m.result.replace(/^\S+ /, "")}` : ""}
            </span>
          </div>
        ))}
      </div>
      <HeroCaption
        lead={
          <>
            {m.title === "Final" ? `IPL ${m.season} Final` : `${m.title} · IPL ${m.season}`} ·{" "}
            <b className="font-semibold text-foreground num">{worm.ball_count}</b> balls, one particle each
          </>
        }
        legend={
          <>
            <LegendDot colour="var(--faint)">dot / 1–3</LegendDot>
            <LegendDot colour="var(--brand)">4</LegendDot>
            <LegendDot colour="var(--primary)">6</LegendDot>
            <LegendDot colour="var(--negative)">W</LegendDot>
          </>
        }
        note={note}
      />
    </figure>
  );
}
