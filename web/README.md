# Predict-11 web

Next.js (App Router, TypeScript strict) + Tailwind CSS v4 + shadcn/ui (base-nova, neutral) + TanStack Query,
with a typed API client generated from the FastAPI backend's OpenAPI spec.

## Commands

```bash
pnpm install          # install deps
pnpm dev              # dev server on http://localhost:3000  (or `make web` from the repo root)
pnpm build && pnpm start
pnpm lint             # ESLint (next/core-web-vitals + typescript)
pnpm typecheck        # tsc --noEmit
pnpm test             # Vitest + Testing Library (jsdom); `pnpm test:watch` for watch mode
pnpm gen:api          # regenerate src/lib/api/schema.ts from $NEXT_PUBLIC_API_URL/openapi.json
```

`pnpm gen:api` needs the backend running (`make api` from the repo root). Commit the regenerated
`schema.ts` alongside backend API changes.

## Config

| Env var | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | FastAPI base URL (inlined at build time; also used by `gen:api`) |

## Layout

```
src/
  app/                    routes: / (Fixtures), /builder, /review, /accuracy
  components/
    shell/                top bar, freshness badge, side/bottom nav, theme toggle, empty state
    player/               PlayerCard, RangeBar, TeamBadge, RoleChip
    pitch/                PitchView (WK/BAT/AR/BOWL rows on a stylised field)
    builder/              BuilderDemo (mock lock/exclude state)
    ui/                   shadcn/ui primitives (add more with `pnpm dlx shadcn@latest add <name>`)
  lib/
    api/                  schema.ts (generated), client.ts (openapi-fetch), queries.ts (TanStack hooks)
    tokens.ts             IPL team colours + role colours
    range.ts              floor–median–ceiling range-bar maths
    mock.ts               mock XI used until the players endpoint exists
```

Dark mode follows the system preference by default (`next-themes`, class strategy); the top-bar
button cycles system → light → dark.
