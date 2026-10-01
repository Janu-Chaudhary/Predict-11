import type { Role, XIPlayer } from "../types";

/** Port of docs/design/hero-xi-assembles.html layout(): two benches + a WK/BAT/AR/BOWL pitch. */

export const XI_ROLES: Role[] = ["WK", "BAT", "AR", "BOWL"];
export type XY = [number, number];

export type XILayout = {
  wide: boolean;
  field: { left: number; top: number; width: number; height: number };
  bench: Map<string, XY>;
  pitch: Map<string, XY>;
  rowLabels: { role: Role; left: number; top: number }[];
  benchLabels: { team: string; left: string; top: number }[];
};

export function benches(players: XIPlayer[], teams: string[]): Record<string, XIPlayer[]> {
  const out: Record<string, XIPlayer[]> = Object.fromEntries(teams.map((t) => [t, []]));
  [...players]
    .sort((a, b) => XI_ROLES.indexOf(a.role) - XI_ROLES.indexOf(b.role) || a.short_name.localeCompare(b.short_name))
    .forEach((p) => (out[p.team] ??= []).push(p));
  return out;
}

/** Picked XI by role row, best first within a row. */
export function pickRows(players: XIPlayer[]): XIPlayer[][] {
  const picks = players.filter((p) => p.picked);
  return XI_ROLES.map((r) => picks.filter((p) => p.role === r).sort((a, b) => b.points - a.points));
}

export function layoutXI(players: XIPlayer[], teams: string[], W: number, H: number): XILayout {
  const wide = W >= 540;
  const bench = new Map<string, XY>();
  const pitch = new Map<string, XY>();
  const benchLabels: XILayout["benchLabels"] = [];
  const byTeam = benches(players, teams);
  let fx: number, fy: number, fw: number, fh: number;
  if (wide) {
    const bw = 70;
    fx = bw + 8;
    fy = 0;
    fw = W - 2 * (bw + 8);
    fh = H;
    teams.forEach((t, side) => {
      const cx = side ? W - bw / 2 : bw / 2;
      benchLabels.push({ team: t, left: `${cx}px`, top: H * 0.5 - 3 * 40 - 20 });
      const top = H * 0.5 - 3 * 40 + 20;
      byTeam[t].forEach((p, i) => bench.set(p.id, [cx + (i % 2 ? 16 : -16), top + Math.floor(i / 2) * 40]));
    });
  } else {
    fx = 0;
    fy = 56;
    fw = W;
    fh = H - 112;
    teams.forEach((t, side) => {
      const y = side ? H - 18 : 18;
      const n = byTeam[t].length;
      const step = Math.min(28, (W - 20) / Math.max(n, 1));
      benchLabels.push({ team: t, left: "50%", top: side ? H - 50 : 36 });
      byTeam[t].forEach((p, i) => bench.set(p.id, [W / 2 + (i - (n - 1) / 2) * step, y]));
    });
  }
  const ys = wide ? [0.15, 0.37, 0.6, 0.82] : [0.13, 0.36, 0.6, 0.83];
  const rowLabels: XILayout["rowLabels"] = [];
  pickRows(players).forEach((row, ri) => {
    const y = fy + fh * ys[ri];
    // usable width of the oval at this height
    const dy = (y - (fy + fh / 2)) / (fh / 2);
    const half = (fw / 2) * Math.sqrt(Math.max(0, 1 - dy * dy)) * 0.92;
    const n = Math.max(row.length, 1);
    const slot = wide ? Math.min(104, (2 * half) / n) : Math.min(80, (W - 44) / n);
    const shift = 18;
    row.forEach((p, i) => pitch.set(p.id, [fx + fw / 2 + (i - (row.length - 1) / 2) * slot + shift, y]));
    const firstX = fx + fw / 2 - ((row.length - 1) / 2) * slot + shift;
    rowLabels.push({ role: XI_ROLES[ri], left: Math.max(2, firstX - 22 - 44), top: y - 2 });
  });
  return { wide, field: { left: fx, top: fy, width: fw, height: fh }, bench, pitch, rowLabels, benchLabels };
}

export function initials(s: string): string {
  return s
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}
