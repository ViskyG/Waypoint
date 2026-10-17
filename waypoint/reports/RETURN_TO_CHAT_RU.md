# Waypoint — результат локальной интеграции

Выполнены WPT-R00, C05, C06 и C07 поверх существующих C01–C04. Локальный сервис и observer выбранного действующего Codex оставлены работающими. Режим MIXED. Это проверка конкретной установленной версии на этой машине, без обещания совместимости со всеми клиентами.

## Среда и исходная база

Дата: 17 октября 2026, Asia/Tbilisi. Новая распакованная рабочая копия в `/home/visky/My Projects/Waypoint`; более нового кода в ней не было. Git-репозиторий не предоставлен, integration commit отсутствует. Исходный архив: `waypoint-roadmap-package-2026-10-16.zip`, SHA-256 `6c5c77322e79d56df988a5954830353d2493c6400750f87d040e62a054f40da6`. R00 проверил 75 файлов исходной поставки, 36 исходных тестов, 5 HTTP/restart сценариев и 135 проверок карты. Receipt: [R00.json](../evidence/R00.json).

Linux x86_64 6.8.0-138-generic; Python 3.10.12, SQLite 3.37.2; установленный Codex 0.160.1, VS Code chatgpt extension 26.930.61225; Chromium 143.0.7499.4. Точные зависимости закреплены в `requirements-local-lock.txt`. Виртуальное окружение находится в проекте. Три субагента выполняли отдельные части реализации/приёмки с непересекающимся владением; тестовые inference-turns и агенты ради статистики не запускались.

Интегратор владел Store/API/CLI, миграцией и передачей. Ветка адаптера владела adapters/collector и своими тестами. Браузерная ветка владела web и browser fixtures; C06.3 начат после принятия индекса C05.3. Настройки Codex, hooks/auth, глобальные скилы и другие проекты не изменялись. Waypoint не запускал и не останавливал настоящих агентов.

## Реализованный результат

- **C05.1:** project-local binding сверяет `CODEX_THREAD_ID` с `session_meta.payload.id`; родительский `WP_AGENT` не наследуется. Focus сохраняет committed source generation/revision; старые, исторические и пограничные items не получают новый focus. Настоящая multi-node+edge привязка подтверждена.
- **C05.2:** индекс известных history roots и dirty items, bounded revision/hash cache, диагностируемые gap/conflict, coalescing 200ms и немедленный terminal flush. Размеры batches ограничены count/bytes; cursor подтверждается после durable commit, крупная hydration имеет финальный барьер. Fork provenance восстанавливает собственного исполнителя по явному `thread_settings_applied.thread_id`, не по времени или тексту.
- **C05.3:** транзакционная миграция schema 1→2 с `item_targets`; исправления links и identities обновляют индекс в той же транзакции. Сначала выбираются associations, затем тексты; потомки разбиваются по 350 IDs. Порядок `first_seq`, `before`, `has_more` сохранён, добавлен совместимый `cursor`. Проверены rollback, старый schema, reopen и rebuild.
- **C06:** постоянные окна чтения и обновление инспектора без прыжка, сохранение выделения до его снятия, отдельные direct/deep окна, keyed DOM, навигация через три уровня/back/camera, ghost/off-map, обе темы и 235px чат. Исторические lifecycle сведения явно подписаны. Карточка содержит до 24 сообщений, свежий инспектор — 100, окно прошлых страниц — до 200.
- **C07:** объединённая сборка, настоящее Codex-подключение, реальные перезапуски только Waypoint, browser→HTTP→Store→native projections, версионируемая правка карты, переносимый профиль и локальная передача.

Основные изменённые исходники: `waypoint/adapters/{codex,ipc,patches}.py`, `collector.py`, `store.py`, `cli.py`, `web/{app.js,style.css}`. Изменены точные contracts/schema generation; добавлены focused Python и browser tests, live verification/timing/package tools, локальная инструкция и dependency lock. API routes и архитектура сохранены; новый административный интерфейс управления агентами не создавался. Полный состав и hashes — manifests поставки.

## Реальные результаты и проверки

| Проверка | Источник и уровень | Получено |
|---|---|---|
| Финальные объединённые Python-контракты | `python -m pytest -q --junitxml=evidence/local-unit-results.xml`; synthetic peers + реальные SQLite/локальные sockets | **62 passed**, 1 предупреждение deprecated alias в зависимости; после синхронизации schema ещё 2 schema-теста PASS |
| HTTP, capabilities, long-poll, outbox/restart | `tools/verify_http.py`; настоящий loopback, отдельная fictional fixture | **5 PASS**, это не доказательство Codex |
| Native owner IPC, разрешённые операции | `tools/verify_live.py`; действующий owner/socket | Только initialize/discovery/history/follow, управляющих RPC **0**; собственная подписка закрыта |
| Исходные native сообщения/команды | Независимый snapshot и локальное сравнение с продуктовой БД | **83 terminal команды, 12 agent messages, 1 user message**: ID/тип/текст точно равны; pending/unequal **0** |
| Прочие native operations | Тот же настоящий IPC | 36 subagent operations, 5 file changes, 1 MCP item совпали по ID/типу; текст непроанализированных форматов не объявлен проверенным |
| Persisted native текст и subagent metadata | Только выбранные rollout-файлы, собственные native provenance boundaries | 52 agent / 15 user сообщений точно равны; 3 subagent metadata точно равны; pending/unequal **0** |
| Настоящее дерево и состояния | Независимая проверка выбранного семейства | **8/8 IDs, 7/7 parent links, 8/8 native cursor identity и lifecycle**; 5 idle / 3 running в выборке. Это не 8 отдельных одновременно подтверждённых live IPC owners |
| Перезапуск и восстановление | Только свои service/observer процессы; существующий Codex продолжал работу | Версия, статусы и items сохранены либо явно исправлены; receipt после сбоя продвинулся 155→287 и далее; hydration завершена; normalization v3; duplicate native keys **0** |
| Настоящий браузер с рабочей картой и Codex projections | `tools/verify_live_browser.py`; Chromium→HTTP текущего сервиса | **6 PASS**: 8 actors, 3 native текста точно равны в DOM, статус обновился в открытом inspector, две версии плана, JS ошибок 0 |
| UX/прокрутка/выделение/вложенность | `tests/browser_check.py`, `browser_details_check.py`; настоящий Chromium и HTTP, **SYNTHETIC** данные | **41+4 PASS**, мышь/колесо/клавиатура, 3 уровня, back/camera, старое окно/хвост/revision, обе темы |
| Насыщенная карта | `tests/rich_browser_check.py`; SYNTHETIC данные, Browser→API→реальный индекс | 100/300 узлов, 4,040/10,240 items, по 60 append; подробные timings/DOM/RSS/heap сохранены |
| Две карты и stale edits | `roadmap/tools/roadmap.py validate`; реальные domain/Store/HTTP contracts | **135 PASS**, round-trip, packet, x_roadmap, disjoint/conflict/delete и deterministic views; реальное локальное изменение описано ниже |

Ссылки: [C05_ADAPTER.md](C05_ADAPTER.md), [C05_LIVE.md](C05_LIVE.md), [C06_BROWSER.md](C06_BROWSER.md), [live-target.json](../evidence/live-target.json), [live-recovery.json](../evidence/live-recovery.json), [live-browser.json](../evidence/live-browser.json), [rich-browser-results.json](../evidence/rich-browser-results.json).

Измерена реальная часть **callback→normalization/coalescing→durable receipt**: n=3 (две initial hydration, один естественный incremental update), медиана 86.1ms, максимум 236.0ms. Часы `time.monotonic`, без дополнительных model turns. [Метод и выборка](../evidence/live-ingest-timing.json). Это **не** задержка provider-emission→browser.

На rich fixtures indexed deep query median 4.35/4.72ms (n=5), state 32.0/63.4ms (n=5), append→inspector 93.6/232.8ms (n=60). Два горячих узла по 500 сообщений не монтируются целиком. При 300 узлах `/state` всё ещё около 1.48MB: бюджет ограничен текущей реализацией, обещания SLA/FPS отсутствуют.

## Найденные ошибки и сохранённая история

Первая реальная проверка перезапуска обнаружила повторное использование ID IPC-события при новой временной метке. Store правильно отклонял конфликт. Исправлена идентичность новой локальной observation; exact prepared retry и persisted source keys остались идемпотентными. [Неуспешная выборка](../evidence/live-target-restart-failure.json) сохранена.

Затем три fork-файла показали два `session_meta`: свой и скопированный родительский. Времена copied rows переписаны источником, поэтому они не использованы как эвристика. Добавлена явная native boundary; normalization v3 повторно обработал только выбранные источники. [Неуспешная attribution-выборка](../evidence/live-target-fork-attribution-failure.json) сохранена.

Три уже ошибочные проекции сообщений исправлены append-only событиями `item.identity_corrected`. Старые события остаются в ledger, сохраняется first receipt order, прежние associations записаны в audit; index и projection меняются атомарно. Противоречащий direct IPC не переопределяется молча. [Сводка коррекции](../evidence/identity-correction.json). Полная приватная БД и список private native keys в передаваемый архив не включены.

## Карта и состояние работ

`project_id=waypoint`. Первый head: **v-dbf4fffa0d9949cc**. Выполнено настоящее изменение относительно актуального экспорта: `x_roadmap.local_delivery`, без изменения 20 node IDs, 21 edge IDs, parent/assignment/acceptance/tests. Новый head: **v-55e4a40332434c53**, ordinal 2; request_id **waypoint-local-integration-20261017-r2**. Повтор идентичного запроса вернул тот же receipt.

[Receipt правки](../evidence/plan-update.json), [актуальный экспорт](../../roadmap/working-export-20261017.json). Он стал новым `ROADMAP.plan.json`; Markdown/packets/waves/preview пересобраны из него. Первоначальный baseline и manifests сохранены в history. Старый `INITIAL_IMPORT` не применялся поверх head. Выполнение и результаты тестов записаны отдельными runtime events; исходные C01–C04 и вся история сохранены. Все выполненные этапы, включая C07.4 и C07, закрыты в runtime после проверки архива; ID и предыдущие события сохранены.

## Пределы результата и публикация

- Подтверждён конкретный private IPC профиль. Он не является официальным стабильным публичным API. Отдельный live IPC owner каждого потомка не доказан; их реальные собственные rollout lifecycle и genealogy проверены отдельно, исторические сведения подписаны.
- Полная задержка provider→browser, многочасовой soak, другие ОС/браузеры/версии, человеческая оценка эргономики и полный accessibility audit не выполнены. Bounded rich stream длится 21/29s, heap снят без принудительного GC.
- Зашифрованные/пустые reasoning records не восстанавливаются. 100 таких items в IPC-выборке исключены как не содержащие provider-visible текста.
- Per-executor binding доступен и проверен локально; глобальный launcher/hook не устанавливался. Явный `--agent` остаётся ручным интерфейсом, ответственность за его проверку у интегратора. Unproven fork provenance остаётся quarantined.
- Скилы-предложения и authoring profile сохранены; текущий исходный `build-implementation-roadmap` 2.0.0 прочитан, точечное предложение совместимо. Глобальные скилы **не опубликованы и не установлены**. Их публикация требует отдельного разрешения владельца, как и указано в переданном scope.
- Создан локальный пакет. Library/Drive/Git, внешний registry/inbox и Runner bindings **не изменялись**; проверенный канал защищённой публикации здесь не предоставлен. Пользовательское принятие результата ещё не заявлено.

## Запуск, состояние и передача

[LOCAL_RUN_RU.md](../LOCAL_RUN_RU.md) содержит запуск, получение приватной ссылки, binding, импорт/export и остановку/удаление только собственных процессов. Сервис слушает `http://127.0.0.1:8769`; для входа используйте локальную команду `url`. Ключи в отчёт не включены. Состояние `../.runtime/data/` имеет 0700, БД — 0600. Автозапуск ОС не создавался. Текущие собственные Process HUD handles: service `2c732e58af3345cf9c1b454caf56780e`, observer `3d9ba3ddf29e4deea14bb82acff6d027`; состояние HUD хранится только в `../.runtime/hud/`. Завершённые записи своих предыдущих запусков сняты, чужие записи не затрагивались.

Локальный архив результата: `../../Waypoint-local-2026-10-17.zip`; его SHA-256 записывается рядом в `Waypoint-local-2026-10-17.zip.sha256`. Проверка состава/CRC/hashes выполняется `tools/package_local.py`, затем `tools/verify_package.py` и `roadmap/tools/verify_delivery.py`. Архив исключает .runtime, venv, токены, рабочую SQLite, private correction inventory, IPC snapshots и исходные тексты текущих диалогов. Возвращаемые screenshots содержат только synthetic fixtures. Старые исходные материалы из предоставленного пакета сохранены как происхождение проекта; публичной публикации не было.
