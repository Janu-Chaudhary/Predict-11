import type { BallKind, Worm } from "../types";

/** Port of docs/design/hero-ball-field.html: one particle per ball + team-coloured "dust". */

export type Margins = { l: number; r: number; t: number; b: number };
export type Scale = { W: number; H: number; M: Margins; yMax: number; overs: number };

export function makeScale(W: number, H: number, yMax: number, overs = 20): Scale {
  return { W, H, yMax, overs, M: { l: 34, r: W < 500 ? 12 : 20, t: 16, b: 26 } };
}
export const sx = (s: Scale, x: number) => s.M.l + (x / s.overs) * (s.W - s.M.l - s.M.r);
export const sy = (s: Scale, y: number) => s.H - s.M.b - (y / s.yMax) * (s.H - s.M.t - s.M.b);

export type Pt = { x: number; y: number };

/** Worm polyline in data units, starting at (0, 0). */
export function wormPoints(worm: Worm): Pt[][] {
  return worm.innings.map((inn) => [{ x: 0, y: 0 }, ...inn.balls.map((b) => ({ x: b.x, y: b.runs }))]);
}

/** Point a fraction `f` (0..1) along a polyline, by vertex index. */
export function pointOn(pts: Pt[], f: number): Pt {
  const i = f * (pts.length - 1);
  const a = pts[Math.floor(i)];
  const b = pts[Math.min(pts.length - 1, Math.floor(i) + 1)];
  const t = i % 1;
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

/** Palette index: 0/1 = innings dust (team colours), 2 = dot/1–3, 3 = four, 4 = six, 5 = wicket. */
export const PAL_SIZE = 6;
export function paletteIndex(kind: BallKind): number {
  return kind === "wicket" ? 5 : kind === "six" ? 4 : kind === "four" ? 3 : 2;
}

export type Particles = {
  n: number;
  real: number;
  px: Float32Array;
  py: Float32Array;
  tx: Float32Array;
  ty: Float32Array;
  ox: Float32Array;
  oy: Float32Array;
  vx: Float32Array;
  vy: Float32Array;
  rad: Float32Array;
  col: Uint8Array;
  delay: Float32Array;
};

/** Deterministic Park–Miller PRNG so server/client and tests agree. */
export function prng(seed = 7) {
  let s = seed;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

export function buildParticles(worm: Worm, s: Scale, dust = s.W < 500 ? 420 : 900): Particles {
  const inns = wormPoints(worm);
  const real = worm.innings.reduce((n, i) => n + i.balls.length, 0);
  const n = real + dust;
  const p: Particles = {
    n,
    real,
    px: new Float32Array(n),
    py: new Float32Array(n),
    tx: new Float32Array(n),
    ty: new Float32Array(n),
    ox: new Float32Array(n),
    oy: new Float32Array(n),
    vx: new Float32Array(n),
    vy: new Float32Array(n),
    rad: new Float32Array(n),
    col: new Uint8Array(n),
    delay: new Float32Array(n),
  };
  const rnd = prng(7);
  let i = 0;
  // dust first so the real balls draw on top
  for (let d = 0; d < dust; d++, i++) {
    const k = inns.length > 1 ? d % 2 : 0;
    const pt = pointOn(inns[k], rnd());
    const jitter = (rnd() - 0.5) * 5;
    p.tx[i] = sx(s, pt.x) + jitter * 0.4;
    p.ty[i] = sy(s, pt.y) + jitter;
    p.col[i] = k;
    p.rad[i] = 0.7 + rnd() * 0.9;
  }
  for (const inn of worm.innings) {
    for (const b of inn.balls) {
      p.tx[i] = sx(s, b.x);
      p.ty[i] = sy(s, b.runs);
      p.col[i] = paletteIndex(b.kind);
      p.rad[i] = b.kind === "wicket" ? 3.2 : b.kind === "dot" || b.kind === "run" ? 1.5 : 2.4;
      i++;
    }
  }
  const span = s.W - s.M.l - s.M.r;
  for (let j = 0; j < n; j++) {
    // start as floodlight dust: spread across the canvas, denser near the top (the lights)
    p.ox[j] = rnd() * s.W;
    p.oy[j] = Math.pow(rnd(), 1.6) * s.H;
    p.vx[j] = (rnd() - 0.5) * 10;
    p.vy[j] = (rnd() - 0.7) * 8;
    // converge left to right, so the worm grows with the overs
    p.delay[j] = ((p.tx[j] - s.M.l) / span) * 0.55 + rnd() * 0.25;
    p.px[j] = p.ox[j];
    p.py[j] = p.oy[j];
  }
  return p;
}

/** Timeline (ms): 0–1100 drift · 900–3000 converge · 2600–3400 line stroke · 3200 labels · stop at 3700. */
export const TIMELINE = { axesIn: 600, convergeStart: 900, converge: 2100, lineStart: 2600, line: 800, labels: 3200, end: 3700 };

export const easeOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

/** Advance particles to time `t` (ms since start). Returns the convergence progress 0..1. */
export function stepParticles(p: Particles, t: number, dt = 1 / 60): number {
  const conv = (t - TIMELINE.convergeStart) / TIMELINE.converge;
  for (let i = 0; i < p.n; i++) {
    p.ox[i] += p.vx[i] * dt;
    p.oy[i] += p.vy[i] * dt;
    const local = easeOut((conv - p.delay[i] * 0.5) / 0.5);
    p.px[i] = p.ox[i] + (p.tx[i] - p.ox[i]) * local;
    p.py[i] = p.oy[i] + (p.ty[i] - p.oy[i]) * local;
  }
  return easeOut(conv);
}

export function settle(p: Particles) {
  p.px.set(p.tx);
  p.py.set(p.ty);
}

/** y-axis gridlines every 50 runs below yMax. */
export function yTicks(yMax: number): number[] {
  const out: number[] = [];
  for (let y = 0; y < yMax - 10; y += 50) out.push(y);
  return out;
}
