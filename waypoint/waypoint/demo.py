"""Deterministic fictional project, kept visibly separate from real provider data."""
from __future__ import annotations
import copy
from .domain import now


def fixture():
    def node(title, assignment, x, y, parent=None, count=3):
        return {"title": title, "assignment": assignment, "parent": parent,
                "acceptance": {"A-1": {"text": "Результат соответствует заданию; отклонения описаны."}, "A-2": {"text": "Проверены пограничные случаи и совместимость."}},
                "tests": {f"T-{i}": {"label": label} for i, label in enumerate(["Основной сценарий", "Пограничный случай", "Совместимость", "Повторный запуск"][:count], 1)},
                "layout": {"x": x, "y": y}, "source_refs": [{"label": "Исходное задание", "uri": "waypoint://demo/routes"}]}
    nodes = {
        "W-01": node("Контракты маршрутов", "Описать формат пути, ограничения и правила совместимости. Результат должен быть понятен разработчику модели движения и интерфейса.", 60, 230),
        "W-02": node("Поиск маршрута", "Реализовать поиск по графу с учётом веса рёбер и ограничений. Разделить независимые части, не меняя внешний контракт.", 500, 40, count=4),
        "W-03": node("Маршруты на карте", "Показать многоступенчатый маршрут. Взаимодействие с картой не должно мешать чтению выбранного блока.", 500, 540),
        "W-04": node("Механика движения", "Армия последовательно проходит точки маршрута. Обновления состояния должны быть воспроизводимы.", 950, 40),
        "W-05": node("Стоимость маршрута", "Рассчитать время и расход ресурсов, сохранив объяснимый результат для пользователя.", 950, 540),
        "W-06": node("Сквозная проверка", "Проверить путь от задания маршрута до завершения движения. Сохранить результаты, включая неуспешные проверки.", 1400, 250),
        "W-07": node("Старый расчёт", "Предыдущая декомпозиция. Этот блок будет удалён из актуального плана, но его работа остаётся видимой.", 60, 750),
        "W-02.1": node("Модель графа", "Согласовать узлы, рёбра, веса и ограничения маршрута.", 60, 80, "W-02"),
        "W-02.2": node("Алгоритм поиска", "Найти маршрут с учётом недостижимых узлов и остановок.", 500, 80, "W-02"),
        "W-02.3": node("Граничные случаи", "Независимые проверки циклов, пустых маршрутов и недостижимой цели.", 950, 80, "W-02"),
        "W-02.2.1": node("Базовый проход", "Проверить поиск на небольшом графе.", 60, 80, "W-02.2"),
        "W-02.2.2": node("Углубление поиска", "Добавить ограничения, сохранив внешний формат ответа.", 60, 580, "W-02.2"),
    }
    pairs = [("W-01", "W-02"), ("W-01", "W-03"), ("W-02", "W-04"), ("W-03", "W-05"), ("W-04", "W-06"), ("W-05", "W-06"), ("W-02.1", "W-02.2"), ("W-02.2", "W-02.3"), ("W-02.2.1", "W-02.2.2")]
    plan = {"schema": "waypoint.plan/1", "project_id": "demo", "title": "Маршруты армий", "description": "Вымышленный пример. Не подключён к Codex.", "nodes": nodes, "edges": {f"E-{i}": {"from": a, "to": b} for i, (a, b) in enumerate(pairs, 1)}}
    counter = 0
    events = []
    def e(kind, payload, agent=None, ns=None, es=None, minute=0):
        nonlocal counter
        counter += 1
        events.append({"schema": "waypoint.event/1", "event_id": f"demo-event-{counter}", "project_id": "demo", "source": "demo", "agent_id": agent, "kind": kind, "at": f"2026-10-16T12:{minute:02}:00+00:00", "node_ids": ns or [], "edge_ids": es or [], "payload": payload})
    actors = [("A1", "Codex Lead", None, "idle", []), ("A2", "Design Agent", "A1", "completed", ["W-01"]), ("A3", "Backend Lead", "A1", "running", ["W-02"]), ("A4", "Interface Lead", "A1", "running", ["W-03"]), ("A5", "Path Agent", "A3", "running", ["W-02.2", "W-02.3"]), ("A6", "Rules QA", "A3", "idle", ["W-06"]), ("A7", "Map UI", "A4", "running", ["W-03"]), ("A8", "Old Path", "A1", "running", ["W-07"]), ("A9", "Utility Agent", "A1", "running", ["unplanned"])]
    for aid, name, parent, activity, scope in actors:
        e("agent.upsert", {"name": name, "parent_id": parent, "provider": "demo", "session_id": "shared-container"}, aid)
        e("agent.activity", {"state": activity}, aid)
        e("scope.set", {}, aid, scope)
    e("source.health", {"source_key": "demo", "state": "demo", "detail": "Демонстрационные данные, не живая телеметрия"})
    messages = [
        ("A2", "W-01", "Формат route = points + constraints. Отдельно описал совместимость и пределы ответственности модулей.", 12),
        ("A2", "W-01", "Контракт подготовлен. Передаю двум ветвям: расчёту и отображению. Наличие формата ещё не означает, что их интеграция проверена.", 17),
        ("A3", "W-02", "Начал расчёт маршрута. Раскрываю блок на модель графа, алгоритм поиска и независимые пограничные проверки.", 20),
        ("A5", "W-02.2", "Проверяю граничные точки и выбор следующего узла. Пустой маршрут должен отличаться от недостижимого.", 21),
        ("A3", "W-02", "Использую контракт W-01. Не меняю правила задачи ради обхода неуспешного теста: сохраняю диагностику и исправляю ветвь.", 22),
        ("A4", "W-03", "Собираю слой отображения. Колесо над сообщениями прокручивает чат, над пустой картой — изменяет масштаб.", 23),
        ("A7", "W-03", "Кнопка «На уровень выше» возвращает к прежнему положению карты. Хлебные крошки доступны и мышью, и клавиатурой.", 24),
        ("A5", "W-02.3", "Два крайних случая ещё не завершены. Результат теста и текстовый статус блока отображаются отдельно.", 25),
        ("A8", "W-07", "План изменился во время работы. Моя прежняя задача не исчезает из истории: вижу пометку старого блока.", 26),
        ("A9", "unplanned", "Нашёл побочную проблему вне плана. Не создаю фиктивную задачу только ради наблюдателя.", 27),
        ("A6", "W-06", "Сквозная проверка ожидает результатов обеих ветвей. Это пояснение исполнителя, не запрет со стороны карты.", 28),
    ]
    for i, (aid, node_id, msg, minute) in enumerate(messages):
        e("item.upsert", {"item_id": f"m-{i}", "type": "agentMessage", "text": msg, "state": "completed"}, aid, [node_id], minute=minute)
    # A meaningful long chat, only the small visible window is rendered by the UI.
    for i in range(14):
        e("item.upsert", {"item_id": f"detail-{i}", "type": "agentMessage", "text": f"Проверка {i + 1}. Сверяю ожидаемое поведение с фактическим результатом. Комментарий сохранён один раз и связан с блоком, без отдельного пересказа для карты.", "state": "completed"}, "A3", ["W-02"], minute=29)
    e("item.upsert", {"item_id": "edge-1", "type": "agentMessage", "text": "Контракт зафиксирован. Расчёт и интерфейс могут развиваться независимо, общая проверка — на точке интеграции.", "state": "completed"}, "A1", es=["E-1"], minute=18)
    for node_id, status in [("W-01", "done"), ("W-02", "Разбираю граничный случай"), ("W-03", "В работе"), ("W-04", "Ожидает зависимости"), ("W-05", "Запланировано"), ("W-06", "Ожидает проверки"), ("W-07", "В работе по прежнему плану")]:
        e("node.status", {"status": status, "explanation": "Статус сообщён исполнителем. Waypoint не запрещает дальнейшую работу."}, "A1", [node_id], minute=30)
    e("node.result", {"summary": "Контракт подготовлен и проверен на трёх контрольных случаях.", "difference": "Добавлено явное различение пустого пути и недостижимой цели."}, "A2", ["W-01"], minute=30)
    for node_id, outcomes in {"W-01": ["passed"] * 3, "W-02": ["passed", "failed", "not_run", "not_run"], "W-03": ["passed", "not_run", "not_run"]}.items():
        for i, outcome in enumerate(outcomes, 1):
            e("test.result", {"test_id": f"T-{i}", "run_id": "demo-run", "outcome": outcome, "freshness": "unknown", "basis": "fictional example, not a source commit"}, "A6", [node_id], minute=31)
    return plan, events


def seed(store):
    if store.head("demo"):
        return
    plan, events = fixture()
    first = store.import_plan(plan, None, "demo-plan-v1")
    store.ingest(events)
    second = copy.deepcopy(plan)
    del second["nodes"]["W-07"]
    second["nodes"]["W-02"]["acceptance"]["A-3"] = {"text": "Отдельно проверять недостижимую цель и отсутствие точек."}
    store.import_plan(second, first["version"], "demo-plan-v2")
