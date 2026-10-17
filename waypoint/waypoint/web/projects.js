(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    const el = (tag, cls, text) => { const node = document.createElement(tag); node.className = cls; if (text !== undefined) node.textContent = String(text); return node; };
    const healthLabels = {connected: 'подключены', disconnected: 'отключены', stale: 'данные устарели', unknown: 'состояние неизвестно'};
    const reportLabels = {connected: 'подключён', disconnected: 'отключён', stale: 'устарел', unknown: 'неизвестен'};
    const reportAge = seconds => {
        if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) return 'давность неизвестна';
        if (seconds < 60) return `${Math.floor(seconds)} с назад`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)} мин назад`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)} ч назад`;
        return `${Math.floor(seconds / 86400)} дн назад`;
    };
    api.mountProjectCatalogue = (container, summaries, {onOpenProject}) => {
        container.replaceChildren(el('h1', '', 'Проекты'), el('p', 'small-note', 'Зарегистрированные проекты · наблюдение за работой, история и планы'));
        const list = el('div', 'project-catalogue');
        for (const project of summaries) {
            const card = el('article', 'project-card'); card.dataset.project = project.project_id;
            card.append(el('h2', '', project.title || project.project_id), el('p', 'project-purpose', project.purpose || 'Назначение пока не описано'));
            const count = value => value == null ? 'неизвестно' : String(value);
            card.append(el('p', 'small-note', `${count(project.distinct_active_agents)} активных агентов · ${count(project.distinct_active_blocks)} активных блоков`));
            const health = project.source_health;
            card.append(el('p', 'small-note source-health', 'Источники: ' + (healthLabels[health?.state] || healthLabels.unknown)));
            for (const source of (Array.isArray(health?.sources) ? health.sources : [])) {
                const report = reportLabels[source.reported_state] || reportLabels.unknown;
                const effective = healthLabels[source.state] || healthLabels.unknown;
                const line = el('p', 'small-note source-health-detail', `${source.source_key || 'Источник'}: ${effective} · сообщение: ${report}, ${reportAge(source.age_seconds)}`);
                if (source.reported_at) line.append(document.createTextNode(` · ${source.reported_at}`));
                card.append(line);
            }
            card.append(el('p', 'small-note', 'Последнее наблюдение: ' + (project.last_observed_at || 'нет данных')));
            const open = el('button', 'open-project', 'Открыть проект'); open.onclick = () => onOpenProject(project.project_id); card.append(open); list.append(card);
        }
        if (!summaries.length) list.append(el('p', 'small-note', 'Пока нет проектов. Импортируйте план через wp plan-import.'));
        container.append(list); return () => { container.replaceChildren(); };
    };
})();
