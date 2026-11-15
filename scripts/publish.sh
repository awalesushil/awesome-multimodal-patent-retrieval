#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

git checkout -q main
git pull -q --ff-only

uv run scripts/apply.py
uv run scripts/render.py

if ! git diff --quiet data README.md; then
  git add data README.md
  git commit -q -m "Publish reviewed candidates"
  git push -q origin main
fi
