#!/usr/bin/env bash
# Запись «релиза» продукта (код + UX + аналитика) в PRODUCT_CHANGELOG.md и подсказки по git-тегу/откату.
# Не коммитит и не пушит — только дописывает журнал и печатает команды.
#
# Использование (из корня репозитория):
#   ./scripts/record_product_release.sh "Краткое описание изменений"
#   PRODUCT_RELEASE_TAG=v2026.03.27-ux ./scripts/record_product_release.sh "…"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MSG="${1:-}"
if [[ -z "${MSG// }" ]]; then
  echo "usage: $0 <message>" >&2
  exit 1
fi

SHA_FULL="$(git rev-parse HEAD)"
SHA_SHORT="$(git rev-parse --short HEAD)"
BR="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")"
DATE_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
FILE="$ROOT/docs/PRODUCT_CHANGELOG.md"
TAG="${PRODUCT_RELEASE_TAG:-}"

mkdir -p "$(dirname "$FILE")"
if [[ ! -f "$FILE" ]]; then
  cat >"$FILE" <<'HDR'
# Журнал изменений продукта HumanOS (код и UX)

Это **не** то же самое, что релизы **текстов протоколов** (`docs/RELEASES.md` и `data/protocol_releases/`).

Записи добавляет скрипт `scripts/record_product_release.sh` перед или после коммита.

## Как откатить

- Один коммит: `git revert <SHA>` или `git reset --hard <SHA>` (осторожно).
- По тегу: `git checkout <tag>` — смотреть код; для возврата на ветку: `git checkout main` (или ваша ветка).

HDR
fi

{
  echo "## ${DATE_UTC}"
  echo "- **Commit:** \`${SHA_SHORT}\` (\`${SHA_FULL}\`)"
  echo "- **Branch:** \`${BR}\`"
  echo "- ${MSG}"
  if [[ -n "$TAG" ]]; then
    echo "- **Предлагаемый тег:** \`${TAG}\`"
  fi
  echo ""
  echo "Откат этого коммита: \`git revert ${SHA_FULL}\`"
  echo ""
} >>"$FILE"

echo "Записано в $FILE"
echo ""
if [[ -n "$TAG" ]]; then
  echo "Создать аннотированный тег (выполните вручную после коммита):"
  echo "  git tag -a \"${TAG}\" -m \"${MSG}\" ${SHA_FULL}"
  echo "  git push origin \"${TAG}\""
  echo ""
fi
echo "Текущий HEAD зафиксирован как ${SHA_SHORT}. Если вы ещё не закоммитили изменения, запустите скрипт снова после коммита или поправьте запись вручную."
