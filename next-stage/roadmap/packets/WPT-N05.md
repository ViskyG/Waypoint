# WPT-N05 — Сделать алгоритмы видимыми и проверяемыми

## Для владельца
Показать важную собственную логику проекта вместе с её кодом, проверками и измерениями оптимизации.

Выбор технологии не объясняет, как выполняется сложное преобразование и на чём основано заявление об ускорении.

По отметке блока откроется список его алгоритмов; в проекте — общий реестр с версиями, проверяемостью и честной историей улучшений.

## Входы и результат

**Для начала:**
- WPT-N01 / O-PROFILE: Нужны согласованные поля профиля, совместимые схемы и фикстуры, а не предположения разных исполнителей.

**Для завершения:**
Нет дополнительного входного ребра; собственные критерии обязательны.

**Выход:** Curated algorithm catalogue, block badges and revision-aware evidence views

## Точное чтение
Из корня ЭТОГО архива:
- design/DESIGN.md#d6
- design/CONTRACTS.md#c6
- design/CONTRACTS.md#c4
- contracts/examples/algorithm-observations.json

В действующем репозитории:
- waypoint/waypoint/domain.py
- waypoint/waypoint/store.py
- waypoint/waypoint/server.py
- waypoint/waypoint/web/app.js

## Владение изменениями
- observability/read_models.py algorithm sections
- store.py algorithm evidence projection
- server.py read-only algorithm routes
- web/algorithm_panel.js (new)
- algorithm validity/comparison/browser tests

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Validate one project-level definition per meaningful mechanism and many-to-many block references.
2. Add badge/right inspector and project Algorithms view; distinguish direct/descendant refs and deduplicate.
3. Link exact existing implementation path/symbol/revision or null planned state; never maintain a mutable code copy in the plan.
4. Record immutable correctness/measurement observations with actual basis and mark changed-code evidence stale.
5. Compare only compatible benchmark inputs/methods/units; show uncertainty/regressions and never infer speedup from a prose claim.
6. Populate the small real Waypoint inventory from inspected functions and known tests; no fictitious measurement runs.

## Приёмка
- **WPT-N05/A01:** У общего алгоритма одна идентичность в нескольких блоках и в проектном реестре.
- **WPT-N05/A02:** Пометка блока открывает справа связанные алгоритмы; реестр не заполняется одними названиями технологий.
- **WPT-N05/A03:** Планируемая логика, наличие кода, проверка и измерение показаны раздельно.
- **WPT-N05/A04:** Новая реализация делает прежние свидетельства устаревшими; неуспешная проверка корректности не превращается в успешную оптимизацию.
- **WPT-N05/A05:** Несовместимые данные, единицы и методы помечаются несопоставимыми; у измерения указаны выборка и среда.
- **WPT-N05/A06:** Код и ссылки безопасно отображаются; карточка не запускает команды и не читает произвольные локальные файлы.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Optional Pro preparation of schemas/UI logic, not an implementation gate
Условие эскалации: new request for automatic execution of untrusted code is out of scope.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.
