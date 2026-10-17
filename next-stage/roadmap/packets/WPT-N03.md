# WPT-N03 — Добавить каталог, план и понятное задание

## Для владельца
Дать владельцу общий список проектов и полный читаемый план каждого проекта, связанный с картой.

Карта полезна для наблюдения, но не заменяет краткого объяснения всего проекта и каждой отдельной работы.

Можно открыть проект, прочитать план со статусами, перейти к блоку и понять его смысл, не разбирая инструкцию Codex.

## Входы и результат

**Для начала:**
- WPT-N01 / O-PROFILE: Нужны согласованные поля профиля, совместимые схемы и фикстуры, а не предположения разных исполнителей.

**Для завершения:**
- WPT-N02 / O-DEPS: Окончательное отображение блокеров должно читать общий вычисленный результат, а не второй UI-алгоритм.

**Выход:** Integrated catalogue, Plan and reader-first Task views on the common read model

## Точное чтение
Из корня ЭТОГО архива:
- design/DESIGN.md#d2
- design/DESIGN.md#d3
- design/CONTRACTS.md#c4
- design/IMPLEMENTATION.md#i2

В действующем репозитории:
- waypoint/waypoint/server.py
- waypoint/waypoint/store.py
- waypoint/waypoint/web/app.js
- waypoint/waypoint/web/index.html
- waypoint/waypoint/web/style.css

## Владение изменениями
- waypoint/waypoint/read_models.py (new)
- waypoint/waypoint/web/projects.js (new)
- waypoint/waypoint/web/plan.js (new)
- web/app.js/index.html/style.css (single shell owner)
- catalogue/task/plan browser tests

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Add metadata-only project catalogue using registered projects, not directory crawling.
2. Create Map/Plan/Algorithms navigation and human/executor Task subtabs; keep assignment and acceptance available.
3. Use one node view/status projection for Map and Plan; show parent reported state plus derived descendant activity without overwriting either.
4. Guard caches, cameras, outline position and requests by service/project/version/generation; handle late cross-project replies.
5. Backfill context-rich intent for current human-visible blocks against fresh plan version. Complete dependency display only after O-DEPS is integrated.

## Приёмка
- **WPT-N03/A01:** Краткая суть совпадает в плане и задании блока; команды для исполнителя находятся в отдельной подвкладке.
- **WPT-N03/A02:** Одно событие блока обновляет карту и план без дополнительной записи агента.
- **WPT-N03/A03:** Каталог содержит краткие данные и назначение проектов, не загружает полные переписки.
- **WPT-N03/A04:** Запоздалый ответ другого проекта не меняет открытый проект; возврат сохраняет положение просмотра.
- **WPT-N03/A05:** У ожидающего родителя видна работа потомков; родитель и дети не учитываются как лишние завершённые задачи.
- **WPT-N03/A06:** Для старой структуры явно подписаны текущие наблюдения; историческое воспроизведение не имитируется.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Pro/Sol UI preparation allowed under isolated ownership, not a required delivery
Условие эскалации: actual unresolved user meaning in a node description.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.
