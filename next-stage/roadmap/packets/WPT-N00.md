# WPT-N00 — Проверить рабочую базу и сохранить историю

## Для владельца
Установить, какую работающую версию Waypoint мы сейчас меняем, и сохранить её перед обновлением.

Первая версия уже реализована. Новый этап нельзя накатывать поверх неё из старого архива или начинать заново.

Получим проверенный исходный код, текущую карту и безопасную копию данных; дальнейшие изменения будут адресными.

## Входы и результат

**Для начала:**
Нет дополнительного входного ребра; собственные критерии обязательны.

**Для завершения:**
Нет дополнительного входного ребра; собственные критерии обязательны.

**Выход:** Verified current workspace, current plan export and recoverable private backup

## Точное чтение
Из корня ЭТОГО архива:
- sources/BASELINE.json
- design/IMPLEMENTATION.md#i4
- design/IMPLEMENTATION.md#i5

В действующем репозитории:
- waypoint/reports/RETURN_TO_CHAT_RU.md
- waypoint/waypoint/domain.py
- waypoint/waypoint/store.py
- roadmap/ROADMAP.plan.json

## Владение изменениями
- private rollout receipts and disposable test workspace only

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Read actual repository/worktree status, current package environment and runtime schema; compare affected files with inspected commit.
2. Confirm previous C01–C07 source/evidence without redoing their implementation. Preserve uncommitted changes and resolve an actual overlapping owner before edits.
3. Export installed plan and back up SQLite using the existing mechanism; keep private paths/tokens out of deliverable.
4. Prepare a stage candidate with tools/prepare_stage_merge.py. Inspect identifiers/base/request before importing by existing API, never replace the current plan with the stage fragment.
5. If the old early-start episode can be located, retain exact node IDs, relevant plan version and sanitized chronology. Otherwise record INCIDENT_NOT_RECONSTRUCTED; this does not stop the independently reproducible dependency regression.

## Приёмка
- **WPT-N00/A01:** Записаны фактическая база кода, состояние рабочей копии, схема данных и версия карты; сброса изменений не было.
- **WPT-N00/A02:** Резервная копия и экспорт читаются; приватные ссылки сохранены локально; старые события и идентификаторы не изменены.
- **WPT-N00/A03:** Кандидат объединяет прежние и новые блоки без конфликтов ID; импорт не объявлен состоявшимся до подтверждения.
- **WPT-N00/A04:** Codex не перезапускался, модельные вызовы ради замеров не создавались; старый эпизод объясняется только доступными фактами.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Нет обязательной поставки из чата; Codex выполняет этот же пакет.
Условие эскалации: actual base conflict or unavailable authorized workspace.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.
