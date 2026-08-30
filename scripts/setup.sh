#!/usr/bin/env bash
# One-shot local development bootstrap for AnatoVision.
#
# Sets up both frontend and backend for local (non-Docker) development:
# creates the backend virtualenv, installs dependencies, and copies
# .env.example -> .env / .env.local where missing. Safe to re-run.
#
# Usage: ./scripts/setup.sh   (or `make setup` from the repo root)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Setting up backend"
cd "$ROOT_DIR/backend"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt -r requirements-dev.txt
deactivate

if [ ! -f .env ]; then
  cp .env.example .env
  echo "    created backend/.env from .env.example"
fi

echo "==> Setting up frontend"
cd "$ROOT_DIR/frontend"
npm install

if [ ! -f .env.local ]; then
  cp .env.example .env.local
  echo "    created frontend/.env.local from .env.example"
fi

cat <<'EOF'

==> Done.

Start the backend:
  cd backend && source venv/bin/activate && uvicorn app.main:app --reload

Start the frontend (separate terminal):
  cd frontend && npm run dev

...or run the whole stack with Docker instead:
  docker compose up
EOF
