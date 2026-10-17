# Пакет WPT-N00

> Сгенерировано из `ROADMAP.plan.json`, SHA-256 содержимого `a79bf83233f50ee1620ff7af4c1fc37b2ae07531db2a374d9528e5d99c657bc1`.
> Это представление плана, не самостоятельный источник статусов. Менять JSON и затем выполнять `python tools/roadmap.py render`.

Источники этого пакета читаются от `../next-stage` относительно каталога `roadmap/`; пути репозитория — от корня проекта. Назначения в этом документе нет; сначала координация с текущим владельцем работ.

## WPT-N00 — Проверить рабочую базу и сохранить историю

**Для владельца:**

Установить, какую работающую версию Waypoint мы сейчас меняем, и сохранить её перед обновлением.
Первая версия уже реализована. Новый этап нельзя накатывать поверх неё из старого архива или начинать заново.
Получим проверенный исходный код, текущую карту и безопасную копию данных; дальнейшие изменения будут адресными.

**Для исполнителя:**

1. Read actual repository/worktree status, current package environment and runtime schema; compare affected files with inspected commit.
2. Confirm previous C01–C07 source/evidence without redoing their implementation. Preserve uncommitted changes and resolve an actual overlapping owner before edits.
3. Export installed plan and back up SQLite using the existing mechanism; keep private paths/tokens out of deliverable.
4. Prepare a stage candidate with tools/prepare_stage_merge.py. Inspect identifiers/base/request before importing by existing API, never replace the current plan with the stage fragment.
5. If the old early-start episode can be located, retain exact node IDs, relevant plan version and sanitized chronology. Otherwise record INCIDENT_NOT_RECONSTRUCTED; this does not stop the independently reproducible dependency regression.

Required reading (this archive):
sources/BASELINE.json
design/IMPLEMENTATION.md#i4
design/IMPLEMENTATION.md#i5

Actual repository reading:
waypoint/reports/RETURN_TO_CHAT_RU.md
waypoint/waypoint/domain.py
waypoint/waypoint/store.py
roadmap/ROADMAP.plan.json

**Предшественники:** нет дополнительных прямых зависимостей.

**Предпосылки начала:**

Нет дополнительных условий этой фазы.

**Предпосылки завершения:**

Нет дополнительных условий этой фазы.

Доступность требует свидетельства для нужного результата и рабочей базы; отметка завершения сама по себе её не подтверждает.

**Объявленные результаты:**

- `O-BASE` (rev 1): Verified current workspace, current plan export and recoverable private backup

**Условия приёмки**

- `A01` — Записаны фактическая база кода, состояние рабочей копии, схема данных и версия карты; сброса изменений не было.
- `A02` — Резервная копия и экспорт читаются; приватные ссылки сохранены локально; старые события и идентификаторы не изменены.
- `A03` — Кандидат объединяет прежние и новые блоки без конфликтов ID; импорт не объявлен состоявшимся до подтверждения.
- `A04` — Codex не перезапускался, модельные вызовы ради замеров не создавались; старый эпизод объясняется только доступными фактами.

**Описание проверок — фактические исходы хранятся в журнале**

- `T01` **Записаны фактическая база кода, состояние рабочей копии, схема данных и версия карты; сброса изменений не было..**
- `T02` **Резервная копия и экспорт читаются; приватные ссылки сохранены локально; старые события и идентификаторы не изменены..**
- `T03` **Кандидат объединяет прежние и новые блоки без конфликтов ID; импорт не объявлен состоявшимся до подтверждения..**
- `T04` **Codex не перезапускался, модельные вызовы ради замеров не создавались; старый эпизод объясняется только доступными фактами..**

## Возврат

Использовать `../waypoint/reports/RETURN_TO_CHAT_RU.md` и дополнить полями из `RETURN_FIELDS.md`. Вернуть actual/expected diff, текущий plan_version, изменённые пути, реальную базу, пройденные/непройденные проверки и безопасное следующее действие. Не копировать приватные тексты, auth или всю рабочую БД в отчёт.
