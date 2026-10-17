(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    const el = (tag, cls, text) => { const node = document.createElement(tag); node.className = cls; if (text !== undefined) node.textContent = String(text); return node; };
    api.mountProjectCatalogue = (container, summaries, {onOpenProject}) => {
        container.replaceChildren(el('h1', '', 'Проекты'), el('p', 'small-note', 'Зарегистрированные проекты · наблюдение за работой, история и планы'));
        const list = el('div', 'project-catalogue');
        for (const project of summaries) {
            const card = el('article', 'project-card'); card.dataset.project = project.project_id;
            card.append(el('h2', '', project.title || project.project_id), el('p', 'project-purpose', project.purpose || 'Назначение пока не описано'));
            const count = value => value == null ? 'неизвестно' : String(value);
            card.append(el('p', 'small-note', `${count(project.distinct_active_agents)} активных агентов · ${count(project.distinct_active_blocks)} активных блоков`));
            const health = typeof project.source_health === 'object' ? JSON.stringify(project.source_health) : project.source_health;
            card.append(el('p', 'small-note', 'Источники: ' + (health || 'неизвестно')), el('p', 'small-note', 'Последнее наблюдение: ' + (project.last_observed_at || 'нет данных')));
            const open = el('button', 'open-project', 'Открыть проект'); open.onclick = () => onOpenProject(project.project_id); card.append(open); list.append(card);
        }
        if (!summaries.length) list.append(el('p', 'small-note', 'Пока нет проектов. Импортируйте план через wp plan-import.'));
        container.append(list); return () => { container.replaceChildren(); };
    };
})();
