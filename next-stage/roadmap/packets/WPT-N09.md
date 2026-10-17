# WPT-N09 — Завершить третье выбранное оформление

## Для владельца
Добавить именно третью выбранную владельцем тему, когда её отличающийся референс восстановлен.

Сейчас у нас нет достоверного отдельного третьего изображения; выдавать повтор второго за выполнение нельзя.

Третье оформление войдёт в тот же реестр и пройдёт те же проверки; после этого визуальное требование можно закрыть.

## Входы и результат

**Для начала:**
- WPT-N06 / O-THEMES: Третья тема подключается к реализованному общему реестру.
- WPT-INPUT-T3 / O-REF: Без выбранного референса нельзя честно реализовать именно третье оформление.

**Для завершения:**
- WPT-N08 / O-INTEGRATED: Окончательная приёмка темы проверяет её в собранном приложении, а не только в изолированной палитре.

**Выход:** Third distinct owner-selected theme integrated and checked

## Точное чтение
Из корня ЭТОГО архива:
- visuals/SELECTIONS.json
- design/DESIGN.md#d7
- roadmap/packets/WPT-N06.md

В действующем репозитории:
- web/themes.js
- web/style.css
- new owner-supplied actual third reference

## Владение изменениями
- third-theme tokens/assets
- theme registry one entry
- theme tests and release receipt

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Obtain the actual selected image/name from owner context or user input; record its stable reference and checksum.
2. Implement a distinct matched theme, not an invented palette or duplicated label.
3. Verify controls, semantic colors, readable Task/Plan/Algorithms/filters and saved selection against assembled N08 output.
4. Update reference/acceptance receipt and run only theme-affected regression; do not rerun whole implementation campaign.

## Приёмка
- **WPT-N09/A01:** Настоящий третий выбранный референс получен и соответствует реализации.
- **WPT-N09/A02:** Все три отличающиеся темы выбираются, сохраняют выбор и одинаково передают смысл состояний.
- **WPT-N09/A03:** Оформление осмотрено в настоящем браузере; макет или отсутствие изображения не выдаются за приёмку владельцем.
- **WPT-N09/A04:** Итоговый отчёт обновляет это открытое требование и затронутые свидетельства, не переписывая историю.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Chat may prepare CSS from actual reference after it exists
Условие эскалации: missing selected third reference; do not block other packets.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.

При отсутствии референса — AWAITING_REFERENCE. Не создавать дубликат темы и не объявлять весь этап завершённым.
