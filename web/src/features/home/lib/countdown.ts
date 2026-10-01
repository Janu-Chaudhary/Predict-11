export type Countdown = { days: number; hours: number; minutes: number; seconds: number; total: number };

/** Split the time until `start` into whole units; clamps at zero. */
export function countdown(startMs: number, nowMs: number): Countdown {
  const total = Math.max(0, Math.floor((startMs - nowMs) / 1000));
  return {
    days: Math.floor(total / 86_400),
    hours: Math.floor(total / 3600) % 24,
    minutes: Math.floor(total / 60) % 60,
    seconds: total % 60,
    total,
  };
}

export const pad2 = (n: number) => String(n).padStart(2, "0");
