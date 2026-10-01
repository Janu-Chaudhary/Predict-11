import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";

/** Server-side prefetch budget: past this the page streams and the client query takes over. */
const SERVER_BUDGET_MS = 6_000;

/**
 * Server component: prefetch TanStack queries on the server and hand them to the client cache.
 * The first paint has data (no skeleton flash, and no browser→API CORS hop for it). Failed or
 * slow prefetches are simply not dehydrated, so the client query retries and shows its own
 * error/skeleton state.
 */
export async function Prefetched({
  queries,
  children,
}: {
  queries: { queryKey: readonly unknown[]; queryFn: (signal: AbortSignal) => Promise<unknown>; staleTime?: number }[];
  children: ReactNode;
}) {
  const qc = new QueryClient();
  await Promise.all(
    queries.map((q) =>
      qc.prefetchQuery({
        queryKey: q.queryKey,
        queryFn: () => q.queryFn(AbortSignal.timeout(SERVER_BUDGET_MS)),
        staleTime: q.staleTime,
        retry: false,
      }),
    ),
  );
  return <HydrationBoundary state={dehydrate(qc)}>{children}</HydrationBoundary>;
}

/** `?season=2025` → 2025; anything outside 2008…2026 (or missing) → null. */
export function parseSeason(raw: string | string[] | undefined): number | null {
  const v = Array.isArray(raw) ? raw[0] : raw;
  if (!v || !/^\d{4}$/.test(v)) return null;
  const n = Number(v);
  return n >= 2008 && n <= 2026 ? n : null;
}
