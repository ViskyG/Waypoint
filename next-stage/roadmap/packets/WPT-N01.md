# WPT-N01 — Ввести общий формат описаний и свидетельств

## Для владельца
Разделить понятное человеку описание работы и техническое задание, сохранив их связь в одной карте.

Сейчас одна техническая строка одновременно служит инструкцией агенту и объяснением владельцу.

У блока появится ясная суть, у результатов — проверяемые ссылки; старые задания, история и идентификаторы сохранятся.

## Входы и результат

**Для начала:**
- WPT-N00 / O-BASE: Нужны актуальные исходники, известная схема данных и безопасный экспорт для совместимой миграции.

**Для завершения:**
Нет дополнительного входного ребра; собственные критерии обязательны.

**Выход:** Implemented compatible profile, migration seams and shared tested contract fixtures

## Точное чтение
Из корня ЭТОГО архива:
- design/CONTRACTS.md#c1
- design/CONTRACTS.md#c2
- design/CONTRACTS.md#c3
- design/CONTRACTS.md#c6
- design/IMPLEMENTATION.md#i4

В действующем репозитории:
- waypoint/waypoint/domain.py
- waypoint/waypoint/store.py
- waypoint/tools/generate_contracts.py
- waypoint/schemas/plan.schema.json

## Владение изменениями
- waypoint/waypoint/observability.py (new)
- waypoint/waypoint/domain.py (profile seam)
- waypoint/waypoint/store.py (migration owner)
- waypoint/tools/generate_contracts.py
- waypoint/schemas/
- new profile/migration tests

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Implement the versioned x_observability profile and validators from supplied schemas and contracts; preserve unknown fields.
2. Keep assignment executor-facing; add authored intent and output declarations, typed relations and algorithm definitions. No runtime model summaries.
3. Prepare additive migration of known actual DB schema and rebuildable projections, without manufacturing test or dependency success.
4. Introduce capability reporting only for implemented features and stable response basis. Generate schemas from actual code, not drifting hand-edited copies.
5. Build deterministic synthetic fixtures shared by downstream packets; lock field semantics, not incidental helper names.

## Приёмка
- **WPT-N01/A01:** Импорт и экспорт сохраняют неизвестные расширения, прежние задания, идентификаторы и свидетельства.
- **WPT-N01/A02:** Старые карты открываются; отсутствие человеческого описания видно явно, а не заполняется выдуманным текстом.
- **WPT-N01/A03:** Ошибочные ссылки новых результатов и алгоритмов дают конкретную диагностику; условия не исполняются как произвольный код.
- **WPT-N01/A04:** Прерванная миграция откатывается; повтор, открытие базы и восстановление проекций сохраняют принятые события.
- **WPT-N01/A05:** Программа различает умение хранить новые поля и реально поддерживаемые возможности.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Chat may prepare schemas/tests from exact sources; Codex can complete without it
Условие эскалации: unknown newer schema or conflicting central contract.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.
