# WPT-N06 — Сохранить оформления и расширить выбор тем

## Для владельца
Заменить переключатель двух цветов на реестр оформлений, сохранив выбранные варианты и место для третьего.

Владелец выбрал три оформления, но доступные вложения позволяют однозначно восстановить только два отличающихся.

Терракота и Обсидиан останутся; третья тема будет добавлена по настоящему референсу, а не подменена дублем.

## Входы и результат

**Для начала:**
- WPT-N00 / O-BASE: Для правки реестра тем нужны актуальные UI-файлы и сохранённые референсы; новый профиль описаний не является её блокером.

**Для завершения:**
Нет дополнительного входного ребра; собственные критерии обязательны.

**Выход:** Working extensible theme host and two preserved concrete themes

## Точное чтение
Из корня ЭТОГО архива:
- design/DESIGN.md#d7
- visuals/SELECTIONS.json
- design/IMPLEMENTATION.md#i3

В действующем репозитории:
- waypoint/waypoint/web/app.js
- waypoint/waypoint/web/style.css
- waypoint/waypoint/web/index.html

## Владение изменениями
- web/themes.js (new)
- style.css theme token sections
- theme selector integration
- theme regression fixtures

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Create stable theme registry and persist selected ID, with safe recovery from obsolete ID.
2. Preserve supplied references for Terracotta/Obsidian. Separate theme accent from semantic test/error color.
3. Retain the third selection requirement in metadata as awaiting reference; do not list duplicate Obsidian as a finished third.
4. Validate same controls, contrasts/readability and long chat/inspector layout in both concrete themes.

## Приёмка
- **WPT-N06/A01:** Реестр расширяемый; двоичный переключатель двух тем заменён.
- **WPT-N06/A02:** Оба известных оформления соответствуют сохранённым референсам; выбор переживает перезагрузку.
- **WPT-N06/A03:** Смысл ошибок и результатов тестов не зависит только от декоративного цвета.
- **WPT-N06/A04:** Третье оформление остаётся ожидающим референса; оно не блокирует другую работу и не объявляется готовым дублем.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Sol can prepare token/selector module from exact assets
Условие эскалации: third reference affects N09 only.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.
