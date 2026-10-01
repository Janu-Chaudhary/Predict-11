// Generate typed API schema from the running FastAPI backend.
// Usage: pnpm gen:api   (backend must be running; see `make api`)
import { execFileSync } from "node:child_process";

const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const url = `${base}/openapi.json`;
console.log(`Generating src/lib/api/schema.ts from ${url}`);
execFileSync("openapi-typescript", [url, "-o", "src/lib/api/schema.ts"], { stdio: "inherit" });
