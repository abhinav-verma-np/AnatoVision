# AnatoVision

**A free, open educational platform for learning human anatomy through
medical imaging** — X-ray, CT, MRI, Ultrasound, PET/SPECT, Angiography,
Mammography, and Fluoroscopy — built on open educational datasets.



> AnatoVision is **not** a diagnostic tool. It's built for medical,
> nursing, and radiology students, anatomy learners, and healthcare
> educators — anyone who wants to understand what a structure looks like
> across imaging modalities, not to read a real patient's scan.

---

## Status: Phase 1 - Foundation

This repository currently contains the **project foundation only**: the
monorepo skeleton, the locked application shell (UI, no content yet), and
a working frontend ↔ backend connection. No anatomy content, viewers, or
quizzes exist yet — see [Roadmap](#roadmap).

## Principles

- **Free forever.** No login, no signup, no accounts, no payment system.
- **No tracking** beyond optional, essential anonymous analytics later.
- **Local-first for personal data.** Bookmarks, quiz progress, and
  preferences live in the browser's `localStorage` - never an account.
- **Open datasets only** (TCIA, NIH Chest X-ray, Open Anatomy, Visible
  Human Project, MedPix, Radiopaedia where licensing permits). See
  [`datasets/README.md`](./datasets/README.md).

## Architecture

```
anatovision/
├── frontend/     Next.js (App Router) + TypeScript + Tailwind CSS
├── backend/      FastAPI + Python
├── datasets/     Dataset manifests & licensing notes
├── docs/         Architecture notes
├── docker/       Reserved for shared/infra-level Docker assets
├── scripts/      Cross-cutting dev scripts (setup, etc.)
├── .github/      CI workflow, issue/PR templates
└── docker-compose.yml
```

**Frontend:** Next.js, React, TypeScript, Tailwind CSS. Future imaging
phases will add Framer Motion, Three.js / React Three Fiber, and
Cornerstone.js — not installed yet, since Phase 1 doesn't use them (see
[`docs/architecture.md`](./docs/architecture.md) for why).

**Backend:** FastAPI, Python, PostgreSQL, Redis. Postgres and Redis run
via Docker Compose from Phase 1 on, but no client library is wired into
the app yet — nothing in this phase persists data.

For the full reasoning behind these choices, read
[`docs/architecture.md`](./docs/architecture.md).

## Folder-by-folder

| Path | Purpose |
| --- | --- |
| `frontend/app/` | Next.js routes only (currently the root page + layout) |
| `frontend/components/layout/` | The locked three-column shell: `TopNav`, `Sidebar`, `Workspace`, `InfoPanel` |
| `frontend/components/ui/` | Small reusable UI primitives, no business logic |
| `frontend/features/` | Self-contained feature modules (`connection-status/` is the first) |
| `frontend/hooks/`, `lib/`, `services/` | Shared hooks, framework-agnostic helpers, API-call wrappers |
| `backend/app/api/` | Route handlers (`/health`, `/api/status`) |
| `backend/app/core/` | App-wide settings (`config.py`) |
| `backend/app/models/`, `schemas/`, `services/`, `utils/` | Reserved structure for future ORM models, response schemas, business logic, helpers |
| `datasets/` | Dataset sourcing/licensing notes — no raw data committed |

## Setup

### Option A — Docker (recommended, one command)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (docs at `/docs`)

### Option B — Local (no Docker)

Requires Node.js 20+ and Python 3.12+.

```bash
./scripts/setup.sh
```

Then, in two terminals:

```bash
# Terminal 1 — backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

Visit http://localhost:3000. The top navigation shows a live
**Online / Offline** badge, and the workspace shows a detailed connection
card — both are calling the real `/api/status` endpoint, not a mock.

## Development workflow

All commands are available via the root `Makefile`, or run directly.

| | Command |
| --- | --- |
| Bootstrap everything | `make setup` |
| Frontend dev server | `make frontend-dev` (`cd frontend && npm run dev`) |
| Frontend production build | `make frontend-build` |
| Frontend lint | `make frontend-lint` |
| Backend dev server | `make backend-run` |
| Backend tests | `make backend-test` |
| Backend lint | `make backend-lint` (`ruff check .`) |
| Start full stack (Docker) | `make docker-start` |
| Stop full stack | `make docker-stop` |
| Rebuild from scratch | `make docker-rebuild` |

CI (`.github/workflows/ci.yml`) runs install → lint → test for both apps
on every push and pull request to `main`.

## Environment variables

See `.env.example` (root), `frontend/.env.example`, and
`backend/.env.example`. No secrets are committed anywhere in this repo.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Frontend | Base URL the browser calls the backend at |
| `DATABASE_URL` | Backend | Postgres connection string (plumbed, unused until a persistence feature exists) |
| `REDIS_URL` | Backend | Redis connection string (same status as above) |
| `APP_ENV` | Backend | `development` / `production` |
| `CORS_ORIGINS` | Backend | Origins allowed to call the API — needed for the frontend connection test to work in-browser |

## Roadmap

Foundation is Phase 1. Planned, in rough order:

1. ~~Foundation & project setup~~ ✅ (this phase)
2. Anatomy Explorer
3. X-ray Viewer
4. CT Viewer
5. MRI Viewer
6. Ultrasound Viewer
7. PET/SPECT
8. Angiography
9. Cross-sectional Anatomy
10. 3D Anatomy
11. Quiz System
12. Flashcards
13. Study Notes
14. Bookmarks (local browser only)
15. Search

Each phase is scoped and built independently — see the project
constitution for the AI/contributor behavior rules that govern how
changes are made to this repo (no UI redesign, no auth, no scope creep).

## License

Source code is licensed under the [MIT License](./LICENSE).

Medical imaging datasets are **not** covered by this license — each has
its own license and usage terms. See [`datasets/README.md`](./datasets/README.md).
