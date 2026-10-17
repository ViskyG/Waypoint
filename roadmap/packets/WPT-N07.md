# Пакет WPT-N07

> Сгенерировано из `ROADMAP.plan.json`, SHA-256 содержимого `e5d0d46fac7e8da66d8531ccc42ff3ce0359457f5e7d398229dae3a30b9ace21`.
> Это представление плана, не самостоятельный источник статусов. Менять JSON и затем выполнять `python tools/roadmap.py render`.

Источники этого пакета читаются от `../next-stage` относительно каталога `roadmap/`; пути репозитория — от корня проекта. Назначения в этом документе нет; сначала координация с текущим владельцем работ.

## WPT-N07 — Согласовать карты и скилы с новым форматом

**Для владельца:**

Сделать будущие дорожные карты сразу пригодными для понятного отображения в Waypoint.
Новые вкладки бесполезны, если карты по-прежнему содержат только инструкции агенту и необъяснимые стрелки.
Автор карты заполняет смысл работы и реальные входные результаты один раз; план, карта и задания используют эти данные без повторной отчётности.

**Для исполнителя:**

1. Update authoring/template/rendering to emit readable intent, evidenced blockers and relevant algorithm refs; one JSON source.
2. Apply/reconcile exact skill edits from this package, preserving optional capsule meaning and resource policy.
3. Prepare canonical candidates on a verified base, follow actual registry/navigation validation when publishing, and preserve unrelated instructions.
4. Keep missing full legacy translations marked missing rather than pretending delta fragments translate entire skills.
5. Test a second project, profile round-trip and simulated workflow cases; gate installation of new instructions on actual runtime capabilities.

Required reading (this archive):
skills/README_RU.md
skills/EDITS.json
design/CONTRACTS.md#c7
design/CONTRACTS.md#c1

Actual repository reading:
roadmap/AUTHORING_PROFILE.md
roadmap/templates/PROJECT.plan.json
roadmap/tools/roadmap.py
waypoint/skills/waypoint-map/SKILL.md
waypoint/skills/waypoint-observe/SKILL.md
ViskyG/agent-skills selected canonical files

**Предшественники:** WPT-N01.

**Предпосылки начала:**

- `WPT-NEXT-E-07` — WPT-N01 / O-PROFILE (rev 1; workspace=consumer): Нужны согласованные поля профиля, совместимые схемы и фикстуры, а не предположения разных исполнителей.

**Предпосылки завершения:**

Нет дополнительных условий этой фазы.

Доступность требует свидетельства для нужного результата и рабочей базы; отметка завершения сама по себе её не подтверждает.

**Объявленные результаты:**

- `O-AUTHORING` (rev 1): Updated transferable authoring/profile and validated bounded skill candidates

**Условия приёмки**

- `A01` — Шаблон нового проекта не копирует идентификаторы Waypoint и его ресурсные разрешения.
- `A02` — Текст, задания и план формируются из одного графа; статусы не переносятся вручную.
- `A03` — Весь проект можно выполнить без ChatGPT-капсул; обязательного ожидания чата не появляется.
- `A04` — Правки затрагивают только проверенные участки скилов, сохраняя остальные инструкции.
- `A05` — Публикация, проверка исходников и установка сообщаются отдельно; отсутствие записи GitHub не маскируется успехом.

**Описание проверок — фактические исходы хранятся в журнале**

- `T01` **Шаблон нового проекта не копирует идентификаторы Waypoint и его ресурсные разрешения..**
- `T02` **Текст, задания и план формируются из одного графа; статусы не переносятся вручную..**
- `T03` **Весь проект можно выполнить без ChatGPT-капсул; обязательного ожидания чата не появляется..**
- `T04` **Правки затрагивают только проверенные участки скилов, сохраняя остальные инструкции..**
- `T05` **Публикация, проверка исходников и установка сообщаются отдельно; отсутствие записи GitHub не маскируется успехом..**

## Возврат

Использовать `../waypoint/reports/RETURN_TO_CHAT_RU.md` и дополнить полями из `RETURN_FIELDS.md`. Вернуть actual/expected diff, текущий plan_version, изменённые пути, реальную базу, пройденные/непройденные проверки и безопасное следующее действие. Не копировать приватные тексты, auth или всю рабочую БД в отчёт.
