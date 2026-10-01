/** Maths for the floor–median–ceiling projection range bar. */

export type PointsRange = {
  floor: number;
  median: number;
  ceiling: number;
};

export type RangeGeometry = {
  /** Left edge of the band, % of the track. */
  start: number;
  /** Width of the band, % of the track. */
  width: number;
  /** Median marker position, % of the track. */
  marker: number;
};

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** Order the three values so floor ≤ median ≤ ceiling even if the model output is noisy. */
export function normalizeRange({ floor, median, ceiling }: PointsRange): PointsRange {
  const [a, b, c] = [floor, median, ceiling].sort((x, y) => x - y);
  return { floor: a, median: b, ceiling: c };
}

/**
 * Map a points range onto a track spanning [scaleMin, scaleMax].
 * Values outside the scale are clamped to the track edges. A degenerate scale
 * (max ≤ min) collapses everything to 0 rather than producing NaN.
 */
export function rangeGeometry(range: PointsRange, scaleMin = 0, scaleMax = 120): RangeGeometry {
  const span = scaleMax - scaleMin;
  if (!(span > 0)) return { start: 0, width: 0, marker: 0 };
  const r = normalizeRange(range);
  const pct = (v: number) => clamp(((v - scaleMin) / span) * 100, 0, 100);
  const start = pct(r.floor);
  const end = pct(r.ceiling);
  return { start, width: end - start, marker: pct(r.median) };
}
