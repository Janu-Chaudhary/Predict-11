import createClient from "openapi-fetch";

import { API_URL } from "@/lib/env";

import type { paths } from "./schema";

/** Typed client for the Predict-11 API. Regenerate `schema.ts` with `pnpm gen:api`. */
export const api = createClient<paths>({ baseUrl: API_URL });

export type HealthStatus = {
  status: string;
  version: string;
  db: string;
};

/**
 * The backend currently declares /health as a free-form object, so narrow it here.
 * Once the backend adds a response model this can lean on the generated type directly.
 */
export function parseHealth(data: Record<string, unknown>): HealthStatus {
  const str = (v: unknown, fallback = "unknown") => (typeof v === "string" ? v : fallback);
  return { status: str(data.status), version: str(data.version), db: str(data.db) };
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthStatus> {
  const { data, error } = await api.GET("/api/v1/health", { signal });
  if (error || !data) throw new Error("Health check failed");
  return parseHealth(data);
}
