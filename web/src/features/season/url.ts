/**
 * Shallow URL sync for filter state (shareable links without a server round trip). Next.js
 * integrates `history.replaceState` with its router, so `useSearchParams` stays in sync.
 */
export function replaceQuery(patch: Record<string, string | null>) {
  if (typeof window === "undefined") return;
  const u = new URL(window.location.href);
  for (const [k, v] of Object.entries(patch)) {
    if (v === null) u.searchParams.delete(k);
    else u.searchParams.set(k, v);
  }
  window.history.replaceState(null, "", u);
}
