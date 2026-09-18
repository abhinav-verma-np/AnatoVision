# Architecture — Phase 1 Foundation

This document explains what exists after Phase 1 and why, for contributors
picking up Phase 2+.

## Monorepo layout

```
anatovision/
├── frontend/     Next.js (App Router) + TypeScript + Tailwind CSS
├── backend/      FastAPI + Python
├── datasets/     Dataset manifests & licensing notes (no code yet)
├── docs/         This file, and future architecture notes
├── docker/       Reserved for shared/infra-level Docker assets
├── scripts/      Cross-cutting dev scripts (setup, etc.)
└── .github/      CI workflow, issue/PR templates
```

Frontend and backend are independently deployable, versioned, and tested —
each has its own `package.json` / `requirements.txt`, lint config, and
Dockerfile. `docker-compose.yml` at the root is the only thing that
couples them together, for local development and simple deployments.

## Frontend

- **App Router**, not Pages Router — this is the current Next.js paradigm
  and matches the tech stack lock.
- **Folder-by-role**, not folder-by-feature, for Phase 1 since there's
  only one feature (the connection test) to place:
  - `app/` — routes only (currently just the root page + layout)
  - `components/layout/` — the locked three-column shell (`TopNav`,
    `Sidebar`, `Workspace`, `InfoPanel`, `AppShell`)
  - `components/ui/` — small, dumb, reusable primitives (`StatusDot`,
    icons) with no business logic
  - `features/` — self-contained feature modules; `connection-status/` is
    the first one. Future features (quiz, bookmarks, anatomy explorer)
    each get their own folder here rather than sprawling into `components/`
  - `hooks/`, `lib/`, `services/` — shared logic, framework-agnostic where
    possible (`lib/api.ts`), API-call wrappers (`services/`), and
    stateful React hooks (`hooks/`)
- **One `useApiStatus()` poll**, shared via props from `AppShell` down to
  both the nav badge and the workspace card, instead of two independent
  pollers. Small thing, but it's the pattern future features should
  follow: lift shared server state up, don't duplicate fetches.
- **Tailwind v4, CSS-first config** (`app/globals.css`): every color,
  radius, and font is a named token (`--color-panel`, `--radius-panel`,
  etc.) rather than a raw hex value scattered through components. Restyling
  later means changing tokens, not hunting through JSX.
- **No global state library.** Not needed yet — React state + one shared
  hook covers Phase 1. Revisit if Phase 2's Anatomy Explorer needs
  cross-page state.

## Backend

- **`app/api/`** — route handlers only, thin. `health.py` and `status.py`
  are intentionally different: `/health` is a bare liveness check for
  container orchestration, `/api/status` is the richer "is this app
  correctly configured and reachable from the browser" check the frontend
  actually polls.
- **`app/core/config.py`** — a single `Settings` object (pydantic-settings)
  is the only place environment variables are read. Nothing else in the
  app should call `os.environ` directly.
- **`app/models/`, `app/services/`** exist but are empty on purpose —
  they're reserved locations for Phase 2+ (ORM models, business logic)
  so those phases don't need to restructure the tree, per the constitution's
  "never restructure without approval" rule.

## Why DB/Redis clients aren't wired up yet

`docker-compose.yml` runs Postgres and Redis containers, and `DATABASE_URL`
/ `REDIS_URL` are read into `Settings`, but no code actually opens a
connection. Phase 1 has no feature that needs persistence — adding
SQLAlchemy/asyncpg or redis-py now would be an unused dependency. The
containers exist so later phases (Quiz progress, Bookmarks sync, cached
DICOM metadata) can plug in without infra changes; the client libraries get
added in whichever phase first needs them.

## Why Framer Motion / Three.js / R3F / Cornerstone.js aren't installed yet

They're in the constitution's locked tech stack for **future** phases
(3D Anatomy, DICOM/imaging viewers). Installing them now, with nothing in
Phase 1 that uses them, would violate the "no unnecessary dependencies"
rule. They should be added in the phase that first builds a viewer or 3D
view, not before.

## CORS

`CORS_ORIGINS` (backend) isn't in the constitution's original required env
var list (`NEXT_PUBLIC_API_URL`, `DATABASE_URL`, `REDIS_URL`, `APP_ENV`),
but was added because without it, the frontend's connection test fails on
a browser CORS rejection rather than reflecting whether the backend is
actually reachable — that would make requirement #4 (a working, honest
connection test) impossible to satisfy correctly. Documented here instead
of silently added.
