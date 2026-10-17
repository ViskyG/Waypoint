# WPT-N04 — Отфильтровать сообщения без потери истории

## Для владельца
Позволить выбирать типы сообщений в каждом окне, не теряя старые подходящие записи и место чтения.

В потоке смешаны пояснения, инструменты и другие события; владельцу не всегда нужно видеть их одновременно.

Выбранный фильтр работает по всей истории, новые подходящие сообщения отмечаются отдельно, скрытые продолжают сохраняться.

## Входы и результат

**Для начала:**
- WPT-N01 / O-PROFILE: Нужны согласованные поля профиля, совместимые схемы и фикстуры, а не предположения разных исполнителей.

**Для завершения:**
Нет дополнительного входного ребра; собственные критерии обязательны.

**Выход:** Filter-before-pagination Store/API and independent live reader controls

## Точное чтение
Из корня ЭТОГО архива:
- design/DESIGN.md#d5
- design/CONTRACTS.md#c5
- design/IMPLEMENTATION.md#i3

В действующем репозитории:
- waypoint/waypoint/store.py
- waypoint/waypoint/server.py
- waypoint/waypoint/web/app.js
- waypoint/waypoint/adapters/codex.py

## Владение изменениями
- waypoint/waypoint/store.py (typed paging seam)
- waypoint/waypoint/server.py (compatible query arguments)
- waypoint/waypoint/web/filters.js (new)
- reader integration anchors in app.js
- filter/query/browser fixtures

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Implement deterministic native-type classification and error flag; preserve native identity and unknown types.
2. Apply filter in indexed selection before limit/body loading, including deep multi-target deduplication.
3. Implement query-bound opaque cursor with stable tie-breaking; preserve legacy before semantics when unused.
4. Add per-reader multiselect and error facet; use independent query windows, visible-new counters and saved anchors.
5. Ensure ingestion remains unfiltered and an item corrected out of a selected category invalidates its previous reader.

## Приёмка
- **WPT-N04/A01:** Нужное старое сообщение находится даже за тысячей неподходящих; «ничего», «все» и «прочее» различаются.
- **WPT-N04/A02:** Старый курсор при смене фильтра, области или проекта отклоняется либо явно заменяется новым окном.
- **WPT-N04/A03:** Сообщение, связанное с несколькими потомками, видно один раз; исправления типа и привязки обновляют индексы атомарно.
- **WPT-N04/A04:** Составная команда с результатом остаётся одним событием; недоступные рассуждения и результаты тестов не выдумываются.
- **WPT-N04/A05:** Новые сообщения не сбрасывают выделение и место чтения; скрытые типы не увеличивают счётчик видимых новых сообщений.
- **WPT-N04/A06:** Существующие клиенты CLI/API без фильтра сохраняют прежнее поведение.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Chat may supply isolated UI/classifier tests against fixed contracts
Условие эскалации: unknown native types map Other rather than blocking all work.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.
