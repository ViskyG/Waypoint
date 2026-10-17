# Пакет WPT-N01

> Сгенерировано из `ROADMAP.plan.json`, SHA-256 содержимого `87287d0180f84c02a643d1ef214349a004101ab2455f24095e9787df7e935bfe`.
> Это представление плана, не самостоятельный источник статусов. Менять JSON и затем выполнять `python tools/roadmap.py render`.

Источники этого пакета читаются от `../next-stage` относительно каталога `roadmap/`; пути репозитория — от корня проекта. Назначения в этом документе нет; сначала координация с текущим владельцем работ.

## WPT-N01 — Ввести общий формат описаний и свидетельств

**Для владельца:**

Разделить понятное человеку описание работы и техническое задание, сохранив их связь в одной карте.
Сейчас одна техническая строка одновременно служит инструкцией агенту и объяснением владельцу.
У блока появится ясная суть, у результатов — проверяемые ссылки; старые задания, история и идентификаторы сохранятся.

**Для исполнителя:**

1. Implement the versioned x_observability profile and validators from supplied schemas and contracts; preserve unknown fields.
2. Keep assignment executor-facing; add authored intent and output declarations, typed relations and algorithm definitions. No runtime model summaries.
3. Prepare additive migration of known actual DB schema and rebuildable projections, without manufacturing test or dependency success.
4. Introduce capability reporting only for implemented features and stable response basis. Generate schemas from actual code, not drifting hand-edited copies.
5. Build deterministic synthetic fixtures shared by downstream packets; lock field semantics, not incidental helper names.

Required reading (this archive):
design/CONTRACTS.md#c1
design/CONTRACTS.md#c2
design/CONTRACTS.md#c3
design/CONTRACTS.md#c6
design/IMPLEMENTATION.md#i4

Actual repository reading:
waypoint/waypoint/domain.py
waypoint/waypoint/store.py
waypoint/tools/generate_contracts.py
waypoint/schemas/plan.schema.json

**Предшественники:** WPT-N00.

**Предпосылки начала:**

- `WPT-NEXT-E-01` — WPT-N00 / O-BASE (rev 1; workspace=consumer): Нужны актуальные исходники, известная схема данных и безопасный экспорт для совместимой миграции.

**Предпосылки завершения:**

Нет дополнительных условий этой фазы.

Доступность требует свидетельства для нужного результата и рабочей базы; отметка завершения сама по себе её не подтверждает.

**Объявленные результаты:**

- `O-PROFILE` (rev 1): Implemented compatible profile, migration seams and shared tested contract fixtures

**Алгоритмы:** `ALG-MERGE`.

**Условия приёмки**

- `A01` — Импорт и экспорт сохраняют неизвестные расширения, прежние задания, идентификаторы и свидетельства.
- `A02` — Старые карты открываются; отсутствие человеческого описания видно явно, а не заполняется выдуманным текстом.
- `A03` — Ошибочные ссылки новых результатов и алгоритмов дают конкретную диагностику; условия не исполняются как произвольный код.
- `A04` — Прерванная миграция откатывается; повтор, открытие базы и восстановление проекций сохраняют принятые события.
- `A05` — Программа различает умение хранить новые поля и реально поддерживаемые возможности.

**Описание проверок — фактические исходы хранятся в журнале**

- `T01` **Импорт и экспорт сохраняют неизвестные расширения, прежние задания, идентификаторы и свидетельства..**
- `T02` **Старые карты открываются; отсутствие человеческого описания видно явно, а не заполняется выдуманным текстом..**
- `T03` **Ошибочные ссылки новых результатов и алгоритмов дают конкретную диагностику; условия не исполняются как произвольный код..**
- `T04` **Прерванная миграция откатывается; повтор, открытие базы и восстановление проекций сохраняют принятые события..**
- `T05` **Программа различает умение хранить новые поля и реально поддерживаемые возможности..**

## Возврат

Использовать `../waypoint/reports/RETURN_TO_CHAT_RU.md` и дополнить полями из `RETURN_FIELDS.md`. Вернуть actual/expected diff, текущий plan_version, изменённые пути, реальную базу, пройденные/непройденные проверки и безопасное следующее действие. Не копировать приватные тексты, auth или всю рабочую БД в отчёт.
