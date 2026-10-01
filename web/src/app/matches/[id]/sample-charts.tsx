"use client";

import { ManhattanChart } from "@/components/charts/manhattan-chart";
import { WormChart } from "@/components/charts/worm-chart";
import { SAMPLE_MANHATTAN, SAMPLE_WORM } from "@/lib/sample";

export function SampleMatchCharts() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <WormChart home={SAMPLE_WORM.home} away={SAMPLE_WORM.away} summary="Sample worm: CSK finished on 196 for 5, MI on 189 for 8; CSK led from over 12." />
      <ManhattanChart team="CSK" overs={SAMPLE_MANHATTAN} parRunRate={9} summary="Sample Manhattan for CSK: biggest over was the 18th with 15 runs; five wickets fell." />
    </div>
  );
}
