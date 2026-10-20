/* Explicit read-only UI modules; loaded in source order, also in offline preview. */
(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    api.registerTranslations('themes', {
        en: {
            terracotta: 'Terracotta', obsidian: 'Obsidian',
            pending: 'Third theme · reference pending', selector: 'Theme',
            availability: 'Two themes are ready. The third needs a separate confirmed reference (N09).'
        },
        ru: {
            terracotta: 'Терракота', obsidian: 'Обсидиан',
            pending: 'Третье оформление · ожидается референс', selector: 'Оформление',
            availability: 'Два оформления готовы. Для третьего нужен отдельный подтверждённый референс (N09).'
        }
    });
    const t = key => api.t('themes.' + key);
    const themes = [
        {id: 'terracotta', labelKey: 'terracotta', reference: 'next-stage/visuals/terracotta.png', state: 'ready'},
        {id: 'obsidian', labelKey: 'obsidian', reference: 'next-stage/visuals/obsidian.png', state: 'ready'},
        {id: null, labelKey: 'pending', reference: null, state: 'intended_distinct_reference_missing'}
    ];
    api.getThemeRegistry = () => themes.map(({labelKey, ...theme}) => ({...theme, label: t(labelKey)}));
    api.mountThemeSelector = select => {
        let saved; try { saved = localStorage.getItem('waypoint-theme'); } catch {}
        let active = themes.some(theme => theme.id === saved && theme.state === 'ready') ? saved : 'terracotta';
        const render = () => {
            select.replaceChildren();
            for (const theme of themes) {
                const option = document.createElement('option'); option.textContent = t(theme.labelKey);
                option.value = theme.id || ''; option.disabled = theme.state !== 'ready'; select.append(option);
            }
            select.value = active; select.title = t('availability'); select.setAttribute('aria-label', t('selector'));
        };
        const apply = id => {
            if (!themes.some(theme => theme.id === id && theme.state === 'ready')) return;
            active = id; document.documentElement.dataset.theme = id; select.value = id;
            try { localStorage.setItem('waypoint-theme', id); } catch {}
        };
        render(); apply(active); select.onchange = () => apply(select.value);
        const unsubscribe = api.onLanguageChange(render);
        return () => { unsubscribe(); select.onchange = null; };
    };
})();
