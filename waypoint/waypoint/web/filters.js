/* Per-reader category controls. An empty selection is deliberately distinct from all. */
(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    const categories = {message:'Сообщения',explanation:'Пояснения',plan:'План',command:'Команды',tool:'Инструменты',change:'Изменения',test:'Проверки',agent:'Агенты',other:'Прочее'};
    api.bindTypeFilter = function (container, initialQuery = {}, {onChange} = {}) {
        let query = {...initialQuery};
        function notify() { onChange?.({...query, categories: query.categories == null ? null : [...query.categories]}); }
        function render() {
            container.replaceChildren(); const field = document.createElement('fieldset'); field.className = 'type-filter'; const legend = document.createElement('legend'); legend.textContent = 'Типы сообщений'; field.append(legend);
            for (const [label, selected] of [['Все', null], ['Ничего', []]]) { const button = document.createElement('button'); button.type = 'button'; button.textContent = label; button.onclick = () => { query.categories = selected; render(); notify(); }; field.append(button); }
            for (const [category, title] of Object.entries(categories)) { const label = document.createElement('label'); const input = document.createElement('input'); input.type = 'checkbox'; input.checked = query.categories == null || query.categories.includes(category); input.dataset.category = category; input.onchange = () => { const selection = new Set(query.categories == null ? Object.keys(categories) : query.categories); if (input.checked) selection.add(category); else selection.delete(category); query.categories = Object.keys(categories).filter(c => selection.has(c)); notify(); }; label.append(input, document.createTextNode(title)); field.append(label); }
            const errorLabel = document.createElement('label'); const error = document.createElement('input'); error.type = 'checkbox'; error.checked = !!query.only_errors; error.onchange = () => { query.only_errors = error.checked; notify(); }; errorLabel.append(error, document.createTextNode('Только ошибки')); field.append(errorLabel); container.append(field);
        }
        render(); return {update(nextQuery) { query = {...nextQuery}; render(); }, dispose() {container.replaceChildren();}};
    };
})();
