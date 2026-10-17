# Локальный Waypoint

Все команды запускаются из `waypoint/`. Состояние этой установки находится в `../.runtime/data/` (0700); ключи и переписка не входят в поставку.

```bash
.venv/bin/python -m waypoint --data ../.runtime/data serve --port 8769
```

Для приватной ссылки в другом терминале:

```bash
.venv/bin/python -m waypoint --data ../.runtime/data url
```

Скопируйте её в браузер локально. Ключ из fragment удаляется после загрузки. Не помещайте его в отчёт. Waypoint не запускает агентов и не управляет Codex.

Существующий выбранный thread наблюдается отдельным foreground-процессом:

```bash
.venv/bin/python -m waypoint --data ../.runtime/data --project waypoint observe \
  --thread REAL_DISTINCT_THREAD_ID --ipc /absolute/owned/ipc.sock \
  --rollouts /absolute/codex/sessions
```

Используйте подтверждённый `session_meta.payload.id`, а не общий `session_id`. Чтобы привязать редкие сигналы текущего исполнителя, в его окружении выполните `wp --project waypoint bind --rollout /path/to/its/rollout.jsonl --output /private/binding.json`, затем передавайте `--binding /private/binding.json`. Проверяются native ID текущего caller и metadata. `WP_AGENT` не наследуется. Явный `--agent` остаётся ручным интерфейсом; его корректность отвечает вызывающий интегратор.

`Ctrl+C` завершает только собственный foreground-сервис или observer. Остановка сервиса сохраняет БД, экспорт и outbox; повторный запуск использует тот же каталог. Не удаляйте БД ради конфликта версии. Для удаления установки остановите только эти процессы, сохраните приватный backup при необходимости и удалите эту рабочую папку; глобальных служб, hooks и настроек Codex установка не создаёт.

Дорожная карта меняется через текущий `plan-export`, правку snapshot и `plan-import --merge` с его `base_version` и новым стабильным `request_id`. После неизвестного результата повторяйте идентичное тело/ID. Текущий экспорт и производные представления сохраняются в `roadmap/`; runtime статусы и сообщения остаются в ledger.

Проверки: `.venv/bin/python -m pytest -q`; `.venv/bin/python tools/verify_http.py`; из `roadmap/`: `../waypoint/.venv/bin/python tools/roadmap.py validate`. Для браузера см. `tests/browser_check.py --help` и `tools/verify_live.py --help`. Синтетические fixtures не доказывают подключение к Codex. Подробности фактического запуска и ограничений — `reports/RETURN_TO_CHAT_RU.md`.
