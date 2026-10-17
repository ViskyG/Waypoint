# WPT-N02 — Показывать настоящие причины ожидания

## Для владельца
Связать этапы теми результатами, которые действительно нужны следующей работе, и объяснять состояние этих связей.

Стрелка должна означать необходимый входной результат, а не только удобный порядок написания кода.

План, блок и инструкция исполнителю будут одинаково показывать прямые и унаследованные предпосылки; ранняя активность останется видимой.

## Входы и результат

**Для начала:**
- WPT-N01 / O-PROFILE: Нужны согласованные поля профиля, совместимые схемы и фикстуры, а не предположения разных исполнителей.

**Для завершения:**
Нет дополнительного входного ребра; собственные критерии обязательны.

**Выход:** Shared prerequisite resolver and provenance-bearing dependency projection

## Точное чтение
Из корня ЭТОГО архива:
- design/CONTRACTS.md#c2
- design/CONTRACTS.md#c3
- design/CONTRACTS.md#c4
- design/DESIGN.md#d4
- reference/contract_model.py

В действующем репозитории:
- waypoint/waypoint/server.py
- waypoint/waypoint/domain.py
- waypoint/waypoint/store.py
- roadmap/tools/roadmap.py

## Владение изменениями
- waypoint/waypoint/dependencies.py (new)
- waypoint/waypoint/store.py (dependency evidence seam)
- waypoint/waypoint/server.py (packet seam)
- roadmap/tools/roadmap.py (shared resolver call)
- dependency regression tests

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Implement one shared effective-requirement resolver and fingerprint/evidence evaluator; wire all consumers to it.
2. Return start and finish prerequisites separately, provenance and true endpoints for collapsed partial edges.
3. Classify hard blocker/order/inheritance; validate expanded graph including hidden cycles. Preserve legacy link visibility without pretending known availability.
4. Store dependency observations and discrepancies with workspace/predicate provenance; never derive availability solely from status text.
5. Reproduce direct-only /packet omission with nested synthetic regression. Investigate owner incident only from actual retained evidence.

## Приёмка
- **WPT-N02/A01:** Задание API, расчёт доступных работ и данные интерфейса показывают одинаковые предпосылки при одинаковых входах.
- **WPT-N02/A02:** Зависимость от поддерева предка учитывается; связь только с одним узлом и рекомендуемый порядок не создают лишних блокеров.
- **WPT-N02/A03:** Изменение нужного результата делает старое свидетельство неприменимым; перестановка блоков — нет. Чужая рабочая база не считается подходящей.
- **WPT-N02/A04:** Циклы после наследования и зависимость от самого себя выявляются; вход в подблок не требует заранее завершить его родителя.
- **WPT-N02/A05:** Реальная ранняя активность сохраняется и отображается; позднее свидетельство не подменяет достоверную историю.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Bounded pure resolver preparation in Pro is optional
Условие эскалации: conflicting input semantics that change agreed scope.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.
