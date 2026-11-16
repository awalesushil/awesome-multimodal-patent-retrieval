#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

: "${GITHUB_APP_ID:?set GITHUB_APP_ID}"
: "${GITHUB_APP_KEY_FILE:?set GITHUB_APP_KEY_FILE}"

base64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }

now=$(date +%s)
header=$(printf '{"alg":"RS256","typ":"JWT"}' | base64url)
payload=$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' "$((now - 60))" "$((now + 540))" "$GITHUB_APP_ID" | base64url)
signature=$(printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -sign "$GITHUB_APP_KEY_FILE" | base64url)
jwt="$header.$payload.$signature"

repo=$(git remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')
api() { curl -fsS -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" "$@"; }

installation=$(api "https://api.github.com/repos/$repo/installation" | jq -r .id)
api -X POST "https://api.github.com/app/installations/$installation/access_tokens" | jq -r .token
