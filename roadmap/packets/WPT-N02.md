# Пакет WPT-N02

> Сгенерировано из `ROADMAP.plan.json`, SHA-256 содержимого `2f7ac1cd86633cfa6cef618e6ed2a46c9d1c85fa8c36f4ceb4a3f5ab398f1baf`.
> Это представление плана, не самостоятельный источник статусов. Менять JSON и затем выполнять `python tools/roadmap.py render`.

Источники этого пакета читаются от `../next-stage` относительно каталога `roadmap/`; пути репозитория — от корня проекта. Назначения в этом документе нет; сначала координация с текущим владельцем работ.

## WPT-N02 — Показывать настоящие причины ожидания

**Для владельца:**

Связать этапы теми результатами, которые действительно нужны следующей работе, и объяснять состояние этих связей.
Стрелка должна означать необходимый входной результат, а не только удобный порядок написания кода.
План, блок и инструкция исполнителю будут одинаково показывать прямые и унаследованные предпосылки; ранняя активность останется видимой.

**Для исполнителя:**

1. Implement one shared effective-requirement resolver and fingerprint/evidence evaluator; wire all consumers to it.
2. Return start and finish prerequisites separately, provenance and true endpoints for collapsed partial edges.
3. Classify hard blocker/order/inheritance; validate expanded graph including hidden cycles. Preserve legacy link visibility without pretending known availability.
4. Store dependency observations and discrepancies with workspace/predicate provenance; never derive availability solely from status text.
5. Reproduce direct-only /packet omission with nested synthetic regression. Investigate owner incident only from actual retained evidence.

Required reading (this archive):
design/CONTRACTS.md#c2
design/CONTRACTS.md#c3
design/CONTRACTS.md#c4
design/DESIGN.md#d4
reference/contract_model.py

Actual repository reading:
waypoint/waypoint/server.py
waypoint/waypoint/domain.py
waypoint/waypoint/store.py
roadmap/tools/roadmap.py

**Предшественники:** WPT-N01.

**Предпосылки начала:**

- `WPT-NEXT-E-02` — WPT-N01 / O-PROFILE (rev 1; workspace=consumer): Нужны согласованные поля профиля, совместимые схемы и фикстуры, а не предположения разных исполнителей.

**Предпосылки завершения:**

Нет дополнительных условий этой фазы.

Доступность требует свидетельства для нужного результата и рабочей базы; отметка завершения сама по себе её не подтверждает.

**Объявленные результаты:**

- `O-DEPS` (rev 1): Shared prerequisite resolver and provenance-bearing dependency projection

**Алгоритмы:** `ALG-DEPS`.

**Условия приёмки**

- `A01` — Задание API, расчёт доступных работ и данные интерфейса показывают одинаковые предпосылки при одинаковых входах.
- `A02` — Зависимость от поддерева предка учитывается; связь только с одним узлом и рекомендуемый порядок не создают лишних блокеров.
- `A03` — Изменение нужного результата делает старое свидетельство неприменимым; перестановка блоков — нет. Чужая рабочая база не считается подходящей.
- `A04` — Циклы после наследования и зависимость от самого себя выявляются; вход в подблок не требует заранее завершить его родителя.
- `A05` — Реальная ранняя активность сохраняется и отображается; позднее свидетельство не подменяет достоверную историю.

**Описание проверок — фактические исходы хранятся в журнале**

- `T01` **Задание API, расчёт доступных работ и данные интерфейса показывают одинаковые предпосылки при одинаковых входах..**
- `T02` **Зависимость от поддерева предка учитывается; связь только с одним узлом и рекомендуемый порядок не создают лишних блокеров..**
- `T03` **Изменение нужного результата делает старое свидетельство неприменимым; перестановка блоков — нет. Чужая рабочая база не считается подходящей..**
- `T04` **Циклы после наследования и зависимость от самого себя выявляются; вход в подблок не требует заранее завершить его родителя..**
- `T05` **Реальная ранняя активность сохраняется и отображается; позднее свидетельство не подменяет достоверную историю..**

## Возврат

Использовать `../waypoint/reports/RETURN_TO_CHAT_RU.md` и дополнить полями из `RETURN_FIELDS.md`. Вернуть actual/expected diff, текущий plan_version, изменённые пути, реальную базу, пройденные/непройденные проверки и безопасное следующее действие. Не копировать приватные тексты, auth или всю рабочую БД в отчёт.
