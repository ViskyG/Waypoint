# Точечная интеграция со стандартным скилом — кандидат, не применено

**Цель:** будущие дорожные карты, создаваемые по стандартному workflow, являются непосредственным входом Waypoint. Не заводить ещё один параллельный скил построения плана.

Прочитан текущий оригинал `ViskyG/agent-skills/skills/chatgpt/build-implementation-roadmap/SKILL.md`, version 2.0.0, blob `ae1d3cdb1246ef35a519ad14ed6c3d3e82b5aaf3`. Он уже требует один граф, bounded packets и производные Runner waves, но не задаёт `waypoint.plan/1`. Прочитанный `skills/waypoint-map/SKILL.md` в поставленном проекте — draft-candidate; он не зарегистрирован/не установлен.

## Предлагаемое ограниченное изменение

В существующем `build-implementation-roadmap` добавить секцию после «One graph, two usable execution forms» и уточнение deliverable. Остальное поведение, роль Udot, бюджет и границы установки не менять. Согласованный пункт для англоязычного оригинала:

> For roadmaps produced by this workflow, author the structured work definition directly in the accepted project-bound `waypoint.plan/1` contract. The Waypoint viewer need not be installed or running when a map is prepared; use the schema from the accepted source package. The structured graph is the shared authoring source for human views, packet contexts and Runner grouping; never maintain a second manually translated Waypoint plan. Preserve the design's stable work IDs, explicit nesting and dependency edges, assignments, acceptance and planned tests. Keep source provenance and execution metadata in a compatible namespaced extension, and ensure essential packet instructions appear in fields the current reader actually exposes. Obtain the active base_version before updating an existing map. Verify a disposable native import/export/packet round-trip with the actual implementation and regenerate human views from the same graph. This does not install Waypoint, launch an executor or change runtime status.

Русский смысл: карта сразу создаётся в установленном формате Waypoint; текст, packets и waves — её представления; перед обновлением нужен действующий base_version; проверка — настоящий importer/packet, а не только красивый JSON.

## Что сделать при отдельной согласованной публикации

Прочитать актуальные AGENTS.md → skill-navigation → create-and-revise-skills. Сверить фактическую ревизию оригинала; не применять этот текст слепо поверх изменившегося скила. Сохранить английский оригинал и синхронный перевод, зарегистрировать проектные waypoint-map/waypoint-observe в правильной категории если это входит в согласованный scope. Обновить единый навигатор и его русский индекс, выполнить штатные validators, проверить readback опубликованной версии. Глобальная инструкция/установка проверяется отдельно.

Этот файл является предложением изменения в пакете проекта. В настоящем шаге канонический GitHub-репозиторий, глобальные инструкции и расписания не менялись. Отсутствие глобальной публикации не препятствует локальному использованию приложенной карты и профиля.
