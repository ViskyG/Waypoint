/* Explicit read-only UI modules; loaded in source order, also in offline preview. */
(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    const themes = [
        {id: 'terracotta', label: 'Терракота', reference: 'next-stage/visuals/terracotta.png', state: 'ready'},
        {id: 'obsidian', label: 'Обсидиан', reference: 'next-stage/visuals/obsidian.png', state: 'ready'},
        {id: null, label: 'Третье оформление · ожидается референс', reference: null, state: 'intended_distinct_reference_missing'}
    ];
    api.getThemeRegistry = () => themes.map(theme => ({...theme}));
    api.mountThemeSelector = select => {
        let saved; try { saved = localStorage.getItem('waypoint-theme'); } catch {}
        const active = themes.some(theme => theme.id === saved && theme.state === 'ready') ? saved : 'terracotta';
        select.replaceChildren();
        for (const theme of themes) { const option = document.createElement('option'); option.textContent = theme.label; option.value = theme.id || ''; option.disabled = theme.state !== 'ready'; select.append(option); }
        const apply = id => { document.documentElement.dataset.theme = id; select.value = id; try { localStorage.setItem('waypoint-theme', id); } catch {} };
        apply(active); select.onchange = () => apply(select.value);
        select.title = 'Два оформления готовы. Для третьего нужен отдельный подтверждённый референс (N09).';
        return () => { select.onchange = null; };
    };
})();
