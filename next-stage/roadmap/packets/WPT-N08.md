# WPT-N08 — Проверить обновление целиком на рабочем Waypoint

## Для владельца
Соединить изменения и проверить обычный путь владельца от проекта до сообщения, зависимости и алгоритма.

Отдельно корректные поля и интерфейсы ещё не доказывают, что всё работает вместе на сохранённой истории.

Рабочая карта обновится без потери событий и идентификаторов; появится проверенный результат с точным списком оставшегося.

## Входы и результат

**Для начала:**
- WPT-N02 / O-DEPS: Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- WPT-N03 / O-UX: Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- WPT-N04 / O-FILTERS: Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- WPT-N05 / O-ALGORITHMS: Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- WPT-N06 / O-THEMES: Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.
- WPT-N07 / O-AUTHORING: Нужен готовый результат этой ветки для сквозной проверки единой функциональной версии.

**Для завершения:**
Нет дополнительного входного ребра; собственные критерии обязательны.

**Выход:** Target-verified functional update and explicit remaining requirements receipt

## Точное чтение
Из корня ЭТОГО архива:
- design/ACCEPTANCE.md
- design/IMPLEMENTATION.md#i6
- design/CONTRACTS.md#c4
- reports/RETURN_TO_CHAT_RU.md

В действующем репозитории:
- all changed modules and actual installed service bindings
- waypoint/tools/verify_http.py
- waypoint/tests/browser_check.py
- actual latest plan export

## Владение изменениями
- shared-file integration after contribution review
- bounded end-to-end fixtures/tests
- migration and rollout receipts
- sanitized final package/report

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Merge contributions with one owner per shared file; refresh contracts and schema generation.
2. Run affected local suites, real browser→service tests and isolated schema/plan migrations; no old-archive replacement.
3. Observe ordinary current Codex events to ensure no regressions in IDs/source-health/ingestion while viewing filters and Plan; no artificial model turns for counts.
4. Run multi-project stale-response and parent/child discrepancy cases, rich filtered history and revision-aware algorithm evidence.
5. Roll out only Waypoint within allowed scope, verify backup/recovery and no loss of newly accepted events.
6. Produce functional acceptance receipt and explicitly keep N09/open incident diagnosis distinct from accepted fixes.

## Приёмка
- **WPT-N08/A01:** Одно живое событие статуса обновляет карту и план без второго сообщения агента.
- **WPT-N08/A02:** Проверен настоящий путь браузер → HTTP → сервис; отдельные модульные тесты не выданы за эту проверку.
- **WPT-N08/A03:** Миграция, повтор и восстановление сохраняют ID, статусы, историю и неизвестные поля.
- **WPT-N08/A04:** Не добавлены команды управления агентом, модельный heartbeat, скрытие работы или широкая перезапись.
- **WPT-N08/A05:** Представительные фильтрованные наборы измерены с указанной выборкой; универсальная скорость и FPS не обещаются.
- **WPT-N08/A06:** В отчёте разделены код, интеграция, целевые проверки, публикация и установка; при открытом N09 все три темы не объявляются принятыми.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Нет обязательной поставки из чата; Codex выполняет этот же пакет.
Условие эскалации: target capability or actual data conflict; preserve independent artifacts.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.
