#!/usr/bin/env bash
# Синхронизация с GitHub: fetch, rebase на origin/<ветка>, push.
# Использование: ./scripts/sync-github.sh [ветка]  (из корня репозитория)
# Переменные: REMOTE (по умолчанию origin)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REMOTE="${REMOTE:-origin}"
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"
git fetch "$REMOTE"
git pull --rebase "$REMOTE" "$BRANCH"
git push -u "$REMOTE" "$BRANCH"
