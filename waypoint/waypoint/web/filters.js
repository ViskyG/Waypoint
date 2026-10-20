/* Per-reader category controls. An empty selection is deliberately distinct from all. */
(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    api.registerTranslations('filters', {
        en: {
            legend: 'Message types', all: 'All', none: 'None', errors: 'Errors only',
            message: 'Messages', explanation: 'Explanations', plan: 'Plan', command: 'Commands',
            tool: 'Tools', change: 'Changes', test: 'Checks', agent: 'Agents', other: 'Other'
        },
        ru: {
            legend: 'Типы сообщений', all: 'Все', none: 'Ничего', errors: 'Только ошибки',
            message: 'Сообщения', explanation: 'Пояснения', plan: 'План', command: 'Команды',
            tool: 'Инструменты', change: 'Изменения', test: 'Проверки', agent: 'Агенты', other: 'Прочее'
        }
    });
    const t = key => api.t('filters.' + key);
    const categories = ['message', 'explanation', 'plan', 'command', 'tool', 'change', 'test', 'agent', 'other'];
    api.readerQuery = value => ({categories: Array.isArray(value?.categories) ? categories.filter(key => value.categories.includes(key)) : null, only_errors: value?.only_errors === true});
    api.bindTypeFilter = function (container, initialQuery = {}, {onChange} = {}) {
        let query = {...initialQuery};
        function notify() { onChange?.({...query, categories: query.categories == null ? null : [...query.categories]}); }
        function render() {
            const scrollTop = container.scrollTop, scrollLeft = container.scrollLeft;
            const active = container.contains(document.activeElement) ? document.activeElement.dataset.filterControl : null;
            container.replaceChildren();
            const field = document.createElement('fieldset'); field.className = 'type-filter';
            const legend = document.createElement('legend'); legend.textContent = t('legend'); field.append(legend);
            for (const [key, selected] of [['all', null], ['none', []]]) {
                const button = document.createElement('button'); button.type = 'button'; button.textContent = t(key); button.dataset.filterControl = key;
                button.onclick = () => { query.categories = selected; render(); notify(); }; field.append(button);
            }
            for (const category of categories) {
                const label = document.createElement('label'); const input = document.createElement('input'); input.type = 'checkbox';
                input.checked = query.categories == null || query.categories.includes(category); input.dataset.category = category; input.dataset.filterControl = category;
                input.onchange = () => {
                    const selection = new Set(query.categories == null ? categories : query.categories);
                    if (input.checked) selection.add(category); else selection.delete(category);
                    query.categories = categories.filter(c => selection.has(c)); notify();
                };
                label.append(input, document.createTextNode(t(category))); field.append(label);
            }
            const errorLabel = document.createElement('label'); const error = document.createElement('input'); error.type = 'checkbox';
            error.checked = !!query.only_errors; error.dataset.filterControl = 'errors';
            error.onchange = () => { query.only_errors = error.checked; notify(); };
            errorLabel.append(error, document.createTextNode(t('errors'))); field.append(errorLabel); container.append(field);
            if (active) container.querySelector(`[data-filter-control="${active}"]`)?.focus({preventScroll: true});
            container.scrollTop = scrollTop; container.scrollLeft = scrollLeft;
        }
        render();
        // A language change is display-only: it must not change the reader query or request another window.
        const unsubscribe = api.onLanguageChange(render);
        return {update(nextQuery) { query = {...nextQuery}; render(); }, dispose() { unsubscribe(); container.replaceChildren(); }};
    };
})();
