import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import type { Metadata } from "next";

import { RUNS_STALE_MS, fetchRuns, labKeys } from "@/features/lab/api";
import { LabView } from "@/features/lab/lab-view";
import { parseLabState } from "@/features/lab/state";

export const metadata: Metadata = {
  title: "Model Lab",
  description: "How the fantasy-points model was trained, what it sees, and how good it is: learning curves, calibration, SHAP and every prediction.",
};

export default async function LabPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const state = parseLabState(await searchParams);
  // Prefetch the (small) run list so the first paint knows whether a run exists; the telemetry
  // itself is fetched by the client. A failed prefetch is not dehydrated: the client retries.
  const qc = new QueryClient();
  await qc.prefetchQuery({ queryKey: labKeys.runs(), queryFn: () => fetchRuns(AbortSignal.timeout(4_000)), staleTime: RUNS_STALE_MS, retry: false });
  return (
    <HydrationBoundary state={dehydrate(qc)}>
      <LabView state={state} />
    </HydrationBoundary>
  );
}
