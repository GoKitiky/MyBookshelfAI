#!/usr/bin/env bash
# One-command setup helpers for MyBookshelfAI (local dev or Docker).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  echo "Usage: $0 {local|docker}" >&2
  echo "  local  — pip install, npm ci, then make dev (API + Vite)" >&2
  echo "  docker — ensure .env exists, then docker compose up --build" >&2
  exit 1
}

ensure_env_file() {
  if [[ ! -f .env ]] && [[ -f .env.example ]]; then
    cp .env.example .env
    echo "Created .env from .env.example (edit if you use env-based overrides)."
  fi
}

case "${1:-}" in
  local)
    command -v python3 >/dev/null || {
      echo "error: python3 not found" >&2
      exit 1
    }
    command -v npm >/dev/null || {
      echo "error: npm not found" >&2
      exit 1
    }
    ensure_env_file
    pip install -r requirements.txt
    (cd frontend && npm ci)
    exec make dev
    ;;
  docker)
    command -v docker >/dev/null || {
      echo "error: docker not found" >&2
      exit 1
    }
    ensure_env_file
    exec docker compose up --build
    ;;
  *)
    usage
    ;;
esac
