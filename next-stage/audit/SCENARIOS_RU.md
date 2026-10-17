# Сценарии: ожидаемое и наблюдаемое

Статусы относятся к конкретному свойству. Исторические отчёты переиспользованы, а не объявлены новым запуском. Все ссылки — в репозитории Waypoint; точные пути/строки перечислены в соседних JSON.

| ID | Сценарий | Итог | Что установлено и почему ограничено | Доказательство |
|---|---|---|---|---|
| A01 | Профиль/import-export | Подтверждено | Настоящие Store/schema/round-trip; старые поля сохранены | N01-migration, N07-roadmap, IMPLEMENTED_TESTS |
| A02 | Прерванная миграция | Подтверждено | Rollback и reopen на временной SQLite, реальная история на backup | test_stage2_store_api, N01-migration, N08-recovery |
| A03 | Общие inherited prerequisites | Подтверждено для requires | Packet/frontier/state согласованы; order отдельно расходится (F02) | test_dependencies, IMPLEMENTED_TESTS |
| A04 | Частичная связь/фазы | Частично | Вычисление phase/subtree пройдено; обозначение partial на карте отсутствует | CONTRACT-F02 |
| A05 | Done не доказывает вход | Подтверждено | Доступность определяется receipt, не свободным статусом | test_dependencies, N08 missing→available ledger |
| A06 | Stale/conflict/workspace | Подтверждено вычисление | Fingerprint/workspace/conflict работают; метаданные override расходятся (F03) | test_dependencies, CONTRACT_REPRODUCTION |
| A07 | Ранний старт/позднее подтверждение | Подтверждено после исправления | Настоящий HTTP/Chromium, синтетические события; отдельный реальный период N08 виден в ledger | COMPLETION_REGRESSIONS, WF07 |
| A08 | Причина старого инцидента | Не реконструирована | Нет полной исходной версии/начал; честное ограничение, не диагноз | WF08, INCIDENT_NOT_RECONSTRUCTED |
| A09 | Задание для владельца/исполнителя | Подтверждено | Одна authored intent, отдельный assignment; браузер установленного сервиса | N08-live-browser, COMPLETION_UI |
| A10 | Одно событие в Карте/Плане | Подтверждено | Уникальное фактическое событие установлено и отображено в обоих видах | N08-live-browser |
| A11 | Родитель/потомки/старый план | Подтверждено в своей области | HTTP fixture и браузер; текущие наблюдения над старой структурой подписаны | N08-browser, stage2-ui-synthetic |
| A12 | Поздний ответ другого проекта | Frontend подтверждён | Chromium с controlled mocked responses; обычное переключение проектов ещё проверено HTTP | stage2-ui-synthetic, N08-browser |
| A13 | Стоимость/граница каталога | Подтверждено для метаданных | Не читает тела переписок; давность connected не соответствует D3 (F04) | test_stage2_store_api, CONTRACT_REPRODUCTION |
| A14 | Редкая запись за >1000 | Подтверждено поздним тестом | 1200 команд в том же scope, настоящие HTTP/Store | COMPLETION_REGRESSIONS |
| A15 | Полный порядок/дедуп/коррекции | Подтверждено на сервере | Ties, deep, identity/link и facets; DOM correction отдельно не проходит F01 | IMPLEMENTED_TESTS, CONTRACT_REPRODUCTION |
| A16 | Связанный с query cursor | Подтверждено | 422 при другой области/фильтре; UI открывает новое окно | test_stage2_store_api, N08-browser |
| A17 | Автономное окно чтения | Частично | Append/selection/hidden-counter пройдены; correction-out не проходит; anchor/perquery не реализованы | COMPLETION_REGRESSIONS, F01/F05 |
| A18 | Сохранение скрытого/неизвестного | Подтверждено | Отбор не меняет ingest; Other есть; encrypted reasoning не реконструирован | COMPLETION_REGRESSIONS, N08-native |
| A19 | Алгоритм в нескольких блоках | Подтверждено после исправления | Исходные четыре ALG-ID, псевдонимы удалены из нового head с историей | N05-reconciled-inventory, N08-live-browser |
| A20 | Код/тест/измерение/stale | Подтверждено | Раздельные состояния, точные текущие pins, старая ALG-READ история | test_algorithm_evidence, WORKFLOW_FINDINGS |
| A21 | Сопоставимость оптимизации | Подтверждено в contract tests | Несовместимые условия не сравниваются; замеры без выдуманного baseline | test_algorithm_evidence, N08-performance |
| A22 | Безопасность ссылок/кода | Подтверждено | Hostile strings — текст; нет arbitrary file/eval endpoint | N08-browser, source inspection |
| A23 | Две известные темы | Подтверждено | Реальный Chromium, сохранение выбора, семантические цвета | N08-offline, stage2-ui-synthetic, COMPLETION_UI |
| A24 | Третья тема | Ожидает референс | Отдельного подтверждённого изображения нет | visuals/SELECTIONS, N09 |
| A25 | Шаблон другого проекта | Подтверждено | Schema/Store, собственные ID, политика UNSELECTED | test_authoring_next_stage |
| A26 | Поведение/публикация скилов | Требует уточнения применения | Предложения проверены как текст/patch; глобально не установлены; фактическая дисциплина scopes была нарушена | WF01–03, skills/conformance |
| A27 | Совместный live продукт | Частичная приёмка | Настоящий Codex и основной browser path пройдены; найденные отрицательные случаи требуют FIX | N08-native, N08-live-browser, CONTRACT_REPRODUCTION |
| A28 | Восстановление/затраты | Подтверждено в измеренном объёме | Реальные перезапуски/backup + синтетические 100/300; нет универсального SLA | N08-restart, N08-recovery, N08-performance |
| C01/R00 | Ядро, версии, merge и базовая приёмка | Подтверждено в исходном объёме | Исходные 36, локальные 62 и новые scoped проверки — разные наборы | R00, local-unit-results, N01-migration |
| C02/C05 | Источник, binding и восстановление | Механизмы подтверждены; применение частично | Native ID/text/recovery пройдены, области детей не объявлялись | live-target, N08-native, WF01 |
| C03/C06 | Карта, вложенность и reader | Частично | Навигация/append/выделение прошли; новый filtered correction и anchors неполны | rich-browser-results, N08-browser, F01/F05 |
| C04/C07 | CLI, переносимость и передача | Основной путь подтверждён | Есть реальный guarded import и private Git; версия некоторых старых evidence путей потеряна | CLI_IMPORT, plan-update, WF06 |
