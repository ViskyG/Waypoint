(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    api.registerTranslations('projects', {
        en: {
            title: 'Projects', intro: 'Registered projects · work observation, history and plans',
            noPurpose: 'Purpose has not been described yet', unknown: 'unknown',
            counts: '{agents} active agents · {blocks} active blocks', sources: 'Sources: {state}',
            source: 'Source', sourceDetail: '{source}: {effective} · reported: {reported}, {age}',
            observed: 'Last observed: {at}', noData: 'no data', open: 'Open project',
            empty: 'No projects yet. Import a plan using wp plan-import.',
            healthConnected: 'connected', healthDisconnected: 'disconnected', healthStale: 'data is stale', healthUnknown: 'state unknown',
            reportConnected: 'connected', reportDisconnected: 'disconnected', reportStale: 'stale', reportUnknown: 'unknown',
            ageUnknown: 'age unknown', secondsAgo: '{count} s ago', minutesAgo: '{count} min ago', hoursAgo: '{count} h ago', daysAgo: '{count} d ago'
        },
        ru: {
            title: 'Проекты', intro: 'Зарегистрированные проекты · наблюдение за работой, история и планы',
            noPurpose: 'Назначение пока не описано', unknown: 'неизвестно',
            counts: '{agents} активных агентов · {blocks} активных блоков', sources: 'Источники: {state}',
            source: 'Источник', sourceDetail: '{source}: {effective} · сообщение: {reported}, {age}',
            observed: 'Последнее наблюдение: {at}', noData: 'нет данных', open: 'Открыть проект',
            empty: 'Пока нет проектов. Импортируйте план через wp plan-import.',
            healthConnected: 'подключены', healthDisconnected: 'отключены', healthStale: 'данные устарели', healthUnknown: 'состояние неизвестно',
            reportConnected: 'подключён', reportDisconnected: 'отключён', reportStale: 'устарел', reportUnknown: 'неизвестен',
            ageUnknown: 'давность неизвестна', secondsAgo: '{count} с назад', minutesAgo: '{count} мин назад', hoursAgo: '{count} ч назад', daysAgo: '{count} дн назад'
        }
    });
    const t = (key, params) => api.t('projects.' + key, params);
    const el = (tag, cls, text) => { const node = document.createElement(tag); node.className = cls; if (text !== undefined) node.textContent = String(text); return node; };
    const healthKeys = {connected: 'healthConnected', disconnected: 'healthDisconnected', stale: 'healthStale', unknown: 'healthUnknown'};
    const reportKeys = {connected: 'reportConnected', disconnected: 'reportDisconnected', stale: 'reportStale', unknown: 'reportUnknown'};
    const reportAge = seconds => {
        if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) return t('ageUnknown');
        if (seconds < 60) return t('secondsAgo', {count: Math.floor(seconds)});
        if (seconds < 3600) return t('minutesAgo', {count: Math.floor(seconds / 60)});
        if (seconds < 86400) return t('hoursAgo', {count: Math.floor(seconds / 3600)});
        return t('daysAgo', {count: Math.floor(seconds / 86400)});
    };
    api.mountProjectCatalogue = (container, summaries, {onOpenProject}) => {
        function render() {
            const top = container.scrollTop, left = container.scrollLeft;
            container.replaceChildren(el('h1', '', t('title')), el('p', 'small-note', t('intro')));
            const list = el('div', 'project-catalogue');
            for (const project of summaries) {
                const card = el('article', 'project-card'); card.dataset.project = project.project_id;
                card.append(el('h2', '', project.title || project.project_id), el('p', 'project-purpose', project.purpose || t('noPurpose')));
                const count = value => value == null ? t('unknown') : String(value);
                card.append(el('p', 'small-note', t('counts', {agents: count(project.distinct_active_agents), blocks: count(project.distinct_active_blocks)})));
                const health = project.source_health;
                card.append(el('p', 'small-note source-health', t('sources', {state: t(healthKeys[health?.state] || 'healthUnknown')})));
                for (const source of (Array.isArray(health?.sources) ? health.sources : [])) {
                    const line = el('p', 'small-note source-health-detail', t('sourceDetail', {
                        source: source.source_key || t('source'), effective: t(healthKeys[source.state] || 'healthUnknown'),
                        reported: t(reportKeys[source.reported_state] || 'reportUnknown'), age: reportAge(source.age_seconds)
                    }));
                    if (source.reported_at) line.append(document.createTextNode(` · ${source.reported_at}`));
                    card.append(line);
                }
                card.append(el('p', 'small-note', t('observed', {at: project.last_observed_at || t('noData')})));
                const open = el('button', 'open-project', t('open')); open.onclick = () => onOpenProject(project.project_id); card.append(open); list.append(card);
            }
            if (!summaries.length) list.append(el('p', 'small-note', t('empty')));
            container.append(list); container.scrollTop = top; container.scrollLeft = left;
        }
        render(); const unsubscribe = api.onLanguageChange(render);
        return () => { unsubscribe(); container.replaceChildren(); };
    };
})();
