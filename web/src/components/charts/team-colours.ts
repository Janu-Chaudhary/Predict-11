"use client";

import { useMemo } from "react";

import type { ChartConfig } from "@/components/ui/chart";
import { useResolvedTheme } from "@/hooks/use-resolved-theme";
import { pickMatchColours, teamChartColour } from "@/lib/tokens";

/**
 * Two-team series colours with the clash rule applied for the active theme, plus a shadcn
 * ChartConfig (`--color-home`, `--color-away`) with both themes resolved.
 */
export function useMatchSeries(home: string, away: string) {
  const theme = useResolvedTheme();
  return useMemo(() => {
    const dark = pickMatchColours(home, away, "dark");
    const light = pickMatchColours(home, away, "light");
    const current = theme === "dark" ? dark : light;
    const config = {
      home: { label: home, theme: { dark: dark.home.color, light: light.home.color } },
      away: { label: away, theme: { dark: dark.away.color, light: light.away.color } },
    } satisfies ChartConfig;
    // A dash on the away series whenever it had to move in either theme (stable across toggles).
    const awayDashed = dark.away.dashed || light.away.dashed;
    return { config, current, awayDashed };
  }, [home, away, theme]);
}

export function useTeamColour(team: string) {
  const theme = useResolvedTheme();
  return teamChartColour(team, theme);
}
