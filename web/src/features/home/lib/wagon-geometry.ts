import type { Shot } from "../types";

/** Field frame of the wheel (SVG viewBox -200 -200 400 400): oval rope, striker just below centre. */
export const FIELD = { rx: 190, ry: 180, origin: { x: 0, y: 20 } } as const;

export type Ray = {
  key: string;
  d: string;
  tip: { x: number; y: number } | null;
  tone: "r1" | "r4" | "r6";
  title: string;
};

/**
 * Port of docs/design/hero-wagon-wheel-real.html. Direction frame (calibrated against the
 * commentary): 270° = straight back past the bowler, 0° = square leg for a right-hander,
 * 90° = behind the keeper, 180° = point. Drawn from behind the striker: bowler at the top,
 * leg side on the left for a right-hander; mirrored for a left-hander.
 */
export function wagonRays(shots: Shot[], leftHanded = false): Ray[] {
  const { rx: RX, ry: RY, origin } = FIELD;
  return shots.map((s, i) => {
    const t = (s.direction * Math.PI) / 180;
    const ux = (leftHanded ? 1 : -1) * Math.cos(t);
    const uy = Math.sin(t);
    // distance from the striker to the rope along (ux, uy)
    const A = (ux / RX) ** 2 + (uy / RY) ** 2;
    const B = 2 * ((origin.x * ux) / RX ** 2 + (origin.y * uy) / RY ** 2);
    const C = (origin.x / RX) ** 2 + (origin.y / RY) ** 2 - 1;
    const edge = (-B + Math.sqrt(B * B - 4 * A * C)) / (2 * A) - 6;
    const len = s.runs === 6 ? edge + 4 : s.runs === 4 ? edge - 2 : Math.max(24, (edge * Math.min(s.distance_pct, 96)) / 100);
    const x = origin.x + ux * len;
    const y = origin.y + uy * len;
    const bend = s.runs === 6 ? 18 : 6;
    const cx = (origin.x + x) / 2 - uy * bend;
    const cy = (origin.y + y) / 2 + ux * bend;
    const f = (n: number) => Math.round(n * 100) / 100;
    return {
      key: `${s.label}-${i}`,
      d: `M${origin.x},${origin.y} Q${f(cx)},${f(cy)} ${f(x)},${f(y)}`,
      tip: s.runs >= 4 ? { x: f(x), y: f(y) } : null,
      tone: s.runs === 6 ? "r6" : s.runs === 4 ? "r4" : "r1",
      title: `${s.label} · ${s.bowler} → ${s.zone_name} · ${s.runs}`,
    };
  });
}

/** Animation schedule: rays draw in ball order (≈70 ms stagger, 360 ms singles, 520 ms boundaries). */
export function rayTiming(i: number, runs: number) {
  return { delay: 300 + i * 70, duration: runs >= 4 ? 520 : 360 };
}
