# WPT-N07 — Согласовать карты и скилы с новым форматом

## Для владельца
Сделать будущие дорожные карты сразу пригодными для понятного отображения в Waypoint.

Новые вкладки бесполезны, если карты по-прежнему содержат только инструкции агенту и необъяснимые стрелки.

Автор карты заполняет смысл работы и реальные входные результаты один раз; план, карта и задания используют эти данные без повторной отчётности.

## Входы и результат

**Для начала:**
- WPT-N01 / O-PROFILE: Нужны согласованные поля профиля, совместимые схемы и фикстуры, а не предположения разных исполнителей.

**Для завершения:**
Нет дополнительного входного ребра; собственные критерии обязательны.

**Выход:** Updated transferable authoring/profile and validated bounded skill candidates

## Точное чтение
Из корня ЭТОГО архива:
- skills/README_RU.md
- skills/EDITS.json
- design/CONTRACTS.md#c7
- design/CONTRACTS.md#c1

В действующем репозитории:
- roadmap/AUTHORING_PROFILE.md
- roadmap/templates/PROJECT.plan.json
- roadmap/tools/roadmap.py
- waypoint/skills/waypoint-map/SKILL.md
- waypoint/skills/waypoint-observe/SKILL.md
- ViskyG/agent-skills selected canonical files

## Владение изменениями
- roadmap authoring profile/template/generator
- waypoint/skills/waypoint-map/
- waypoint/skills/waypoint-observe/
- three bounded canonical skill amendments and paired translations

Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.

## Исполнение
1. Update authoring/template/rendering to emit readable intent, evidenced blockers and relevant algorithm refs; one JSON source.
2. Apply/reconcile exact skill edits from this package, preserving optional capsule meaning and resource policy.
3. Prepare canonical candidates on a verified base, follow actual registry/navigation validation when publishing, and preserve unrelated instructions.
4. Keep missing full legacy translations marked missing rather than pretending delta fragments translate entire skills.
5. Test a second project, profile round-trip and simulated workflow cases; gate installation of new instructions on actual runtime capabilities.

## Приёмка
- **WPT-N07/A01:** Шаблон нового проекта не копирует идентификаторы Waypoint и его ресурсные разрешения.
- **WPT-N07/A02:** Текст, задания и план формируются из одного графа; статусы не переносятся вручную.
- **WPT-N07/A03:** Весь проект можно выполнить без ChatGPT-капсул; обязательного ожидания чата не появляется.
- **WPT-N07/A04:** Правки затрагивают только проверенные участки скилов, сохраняя остальные инструкции.
- **WPT-N07/A05:** Публикация, проверка исходников и установка сообщаются отдельно; отсутствие записи GitHub не маскируется успехом.

Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.

## Маршрут и продолжение
Предпочтительный исполнитель: CODEX.
Pro/Sol may prepare these same candidates; Codex can complete them directly
Условие эскалации: concurrent canonical skill edits require fresh bounded reconciliation.
После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.
