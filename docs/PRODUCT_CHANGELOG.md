# Журнал изменений продукта HumanOS (код и UX)

Это **не** то же самое, что релизы **текстов протоколов** (`docs/RELEASES.md` и `data/protocol_releases/`).

Записи добавляет скрипт `scripts/record_product_release.sh` перед или после коммита.

## Как откатить

- Один коммит: `git revert <SHA>` или `git reset --hard <SHA>` (осторожно).
- По тегу: `git checkout <tag>` — смотреть код; для возврата на ветку: `git checkout main` (или ваша ветка).

## 2026-03-27T18:32:32Z
- **Commit:** `195d843` (`195d843e1264261912da9c73b040f5f63df688e9`)
- **Branch:** `main`
- UX протокола: отдельный ряд «Далее», прерывание с подтверждением, подсказки перед оценкой, воронка protocol_step_shown / protocol_next_clicked / protocol_abandon_menu
- **Предлагаемый тег:** `product/ux-protocol-2026-03-27`

Откат этого коммита: `git revert 195d843e1264261912da9c73b040f5f63df688e9`

