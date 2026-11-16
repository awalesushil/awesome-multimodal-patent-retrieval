#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

scripts/publish.sh

open_reviews=$(gh pr list --state open --json headRefName --jq '[.[] | select(.headRefName | startswith("candidates/"))] | length')
if [[ "$open_reviews" != "0" ]]; then
  echo "A candidates PR is still open; skipping discovery this week."
  exit 0
fi

today=$(date +%F)
branch="candidates/$today"
git checkout -q -b "$branch"

uv run scripts/discover.py > candidates.md
uv run scripts/verify.py >> candidates.md || true

if git diff --quiet data; then
  git checkout -q main
  git branch -q -D "$branch"
  exit 0
fi

git add data
git commit -q -m "Weekly candidates $today"
git push -q -u origin "$branch"

pr=(gh pr create --base main --head "$branch" --title "Weekly candidates $today" --body-file candidates.md)
if [[ -n "${GITHUB_APP_ID:-}" ]]; then
  GH_TOKEN=$(scripts/github_app_token.sh) "${pr[@]}"
else
  "${pr[@]}"
fi
git checkout -q main
