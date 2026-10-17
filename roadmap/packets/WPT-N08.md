# Пакет WPT-N08

> Сгенерировано из `ROADMAP.plan.json`, SHA-256 содержимого `2f7ac1cd86633cfa6cef618e6ed2a46c9d1c85fa8c36f4ceb4a3f5ab398f1baf`.
> Это представление плана, не самостоятельный источник статусов. Менять JSON и затем выполнять `python tools/roadmap.py render`.

Источники этого пакета читаются от `../next-stage` относительно каталога `roadmap/`; пути репозитория — от корня проекта. Назначения в этом документе нет; сначала координация с текущим владельцем работ.

## WPT-N08 — Проверить обновление целиком на рабочем Waypoint

**Для владельца:**

Соединить изменения и проверить обычный путь владельца от проекта до сообщения, зависимости и алгоритма.
Отдельно корректные поля и интерфейсы ещё не доказывают, что всё работает вместе на сохранённой истории.
Рабочая карта обновится без потери событий и идентификаторов; появится проверенный результат с точным списком оставшегося.

**Для исполнителя:**

1. Merge contributions with one owner per shared file; refresh contracts and schema generation.
2. Run affected local suites, real browser→service tests and isolated schema/plan migrations; no old-archive replacement.
3. Observe ordinary current Codex events to ensure no regressions in IDs/source-health/ingestion while viewing filters and Plan; no artificial model turns for counts.
4. Run multi-project stale-response and parent/child discrepancy cases, rich filtered history and revision-aware algorithm evidence.
5. Roll out only Waypoint within allowed scope, verify backup/recovery and no loss of newly accepted events.
6. Produce functional acceptance receipt and explicitly keep N09/open incident diagnosis distinct from accepted fixes.

Required reading (this archive):
design/ACCEPTANCE.md
design/IMPLEMENTATION.md#i6
design/CONTRACTS.md#c4
reports/RETURN_TO_CHAT_RU.md

Actual repository reading:
all changed modules and actual installed service bindings
waypoint/tools/verify_http.py
waypoint/tests/browser_check.py
actual latest plan export

**Предшественники:** WPT-N02, WPT-N03, WPT-N04, WPT-N05, WPT-N06, WPT-N07.

**Предпосылки начала:**

- `WPT-NEXT-E-09` — WPT-N02 / O-DEPS (rev 1; workspace=consumer): Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- `WPT-NEXT-E-10` — WPT-N03 / O-UX (rev 1; workspace=consumer): Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- `WPT-NEXT-E-11` — WPT-N04 / O-FILTERS (rev 1; workspace=consumer): Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- `WPT-NEXT-E-12` — WPT-N05 / O-ALGORITHMS (rev 1; workspace=consumer): Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- `WPT-NEXT-E-13` — WPT-N06 / O-THEMES (rev 1; workspace=consumer): Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- `WPT-NEXT-E-14` — WPT-N07 / O-AUTHORING (rev 1; workspace=consumer): Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.

**Предпосылки завершения:**

Нет дополнительных условий этой фазы.

Доступность требует свидетельства для нужного результата и рабочей базы; отметка завершения сама по себе её не подтверждает.

**Объявленные результаты:**

- `O-INTEGRATED` (rev 1): Target-verified functional update and explicit remaining requirements receipt

**Условия приёмки**

- `A01` — Одно живое событие статуса обновляет карту и план без второго сообщения агента.
- `A02` — Проверен настоящий путь браузер → HTTP → сервис; отдельные модульные тесты не выданы за эту проверку.
- `A03` — Миграция, повтор и восстановление сохраняют ID, статусы, историю и неизвестные поля.
- `A04` — Не добавлены команды управления агентом, модельный heartbeat, скрытие работы или широкая перезапись.
- `A05` — Представительные фильтрованные наборы измерены с указанной выборкой; универсальная скорость и FPS не обещаются.
- `A06` — В отчёте разделены код, интеграция, целевые проверки, публикация и установка; при открытом N09 все три темы не объявляются принятыми.

**Описание проверок — фактические исходы хранятся в журнале**

- `T01` **Одно живое событие статуса обновляет карту и план без второго сообщения агента..**
- `T02` **Проверен настоящий путь браузер → HTTP → сервис; отдельные модульные тесты не выданы за эту проверку..**
- `T03` **Миграция, повтор и восстановление сохраняют ID, статусы, историю и неизвестные поля..**
- `T04` **Не добавлены команды управления агентом, модельный heartbeat, скрытие работы или широкая перезапись..**
- `T05` **Представительные фильтрованные наборы измерены с указанной выборкой; универсальная скорость и FPS не обещаются..**
- `T06` **В отчёте разделены код, интеграция, целевые проверки, публикация и установка; при открытом N09 все три темы не объявляются принятыми..**

## Возврат

Использовать `../waypoint/reports/RETURN_TO_CHAT_RU.md` и дополнить полями из `RETURN_FIELDS.md`. Вернуть actual/expected diff, текущий plan_version, изменённые пути, реальную базу, пройденные/непройденные проверки и безопасное следующее действие. Не копировать приватные тексты, auth или всю рабочую БД в отчёт.
