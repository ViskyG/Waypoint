/* Curated algorithm records: DOM-only display, no source execution or file reads. */
(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    function element(tag, text, className) { const node = document.createElement(tag); if (text != null) node.textContent = String(text); if (className) node.className = className; return node; }
    function list(parent, label, values) { if (!values?.length) return; const section = element('section'); section.append(element('h4', label)); const ul = element('ul'); for (const value of values) ul.append(element('li', value)); section.append(ul); parent.append(section); }
    function reference(parent, ref, repository, revision) {
        const text = `${ref.path || ''}${ref.symbol ? ' · ' + ref.symbol : ''}${revision ? ' @ ' + revision : ''}`;
        const line = element('p', text, 'algorithm-reference');
        // Local paths are displayed as data. Only an explicit repository URL can navigate.
        if (typeof repository === 'string') { try { const url = new URL(repository); if (['http:', 'https:'].includes(url.protocol)) { const a = element('a', 'Репозиторий'); a.href = url.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; line.append(document.createTextNode(' · '), a); } } catch (_) {} }
        parent.append(line);
    }
    api.mountAlgorithms = function (container, initialView, callbacks = {}) {
        let view = initialView;
        function render() {
            container.replaceChildren();
            const algorithms = Array.isArray(view) ? view : view?.algorithms || [];
            if (!algorithms.length) { container.append(element('p', 'Для этой области алгоритмы ещё не описаны.', 'empty')); return; }
            for (const record of algorithms) {
                const d = record.definition || record;
                const card = element('article', null, 'algorithm-card'); card.dataset.algorithm = record.id || d.id;
                const title = element('button', d.title || record.id, 'algorithm-title'); title.type = 'button'; title.onclick = () => callbacks.onOpenAlgorithm?.(record.id || d.id); card.append(title);
                card.append(element('p', d.purpose));
                const status = element('p', null, 'algorithm-status');
                for (const label of [`Определение r${d.definition_revision || '?'}`, record.implemented ? 'Код указан' : 'Реализация запланирована', `Корректность: ${{passed:'подтверждена',failed:'есть неуспешная проверка',not_run:'не проверена'}[record.tested] || 'не проверена'}`, record.measured ? 'Измерения записаны' : 'Измерений нет', record.installed ? 'Интеграция подтверждена' : 'Интеграция не подтверждена']) status.append(element('span', label + ' · '));
                card.append(status);
                for (const association of record.associations || []) { const b = element('button', `${association.node_id}${association.direct ? '' : ' (потомок)'}`); b.type = 'button'; b.onclick = () => callbacks.onOpenNode?.(association.node_id); card.append(b); }
                list(card, 'Входы', d.inputs); list(card, 'Результаты', d.outputs); list(card, 'Шаги', d.steps); list(card, 'Инварианты', d.invariants); list(card, 'Пограничные случаи', d.edge_cases);
                if (d.implementation) { const h = element('h4', 'Исходный код'); card.append(h); for (const ref of d.implementation.refs || []) reference(card, ref, d.implementation.repository, d.implementation.revision); }
                if (d.testability) { card.append(element('h4', 'Проверяемость'), element('p', d.testability.strategy)); for (const ref of d.testability.test_refs || []) reference(card, ref); list(card, 'Недостающие проверки', d.testability.missing_cases); }
                list(card, 'Риски ресурсов', d.resource_risks);
                for (const evidence of record.evidence || []) { const p = evidence.payload || {}; const details = element('details', null, 'algorithm-evidence'); details.append(element('summary', `${evidence.event_id} · ${evidence.freshness === 'stale' ? 'устарело' : 'текущая версия'} · ${p.correctness?.outcome || 'not_run'}`)); details.append(element('p', `${evidence.source || ''} · ${evidence.at || ''}`)); list(details, 'Причины устаревания', evidence.stale_reasons); list(details, 'Свидетельства', p.correctness?.evidence_refs); if (p.measurement) { const m = p.measurement; details.append(element('p', `${m.metric}: ${m.value} ${m.unit}; n=${m.n}; ${m.statistic}; ${m.method}`), element('p', `Среда: ${m.environment_ref}; данные: ${m.dataset_ref}; нагрузка: ${m.workload_ref}; семантика: ${m.semantic_revision}`)); } else details.append(element('p', 'Измерение отсутствует')); if (p.note) details.append(element('p', p.note)); card.append(details); }
                for (const comparison of record.comparisons || []) { card.append(element('p', `Сравнение: ${comparison.state}; ${(comparison.reasons || []).join(', ')} · свидетельство: ${comparison.freshness || 'unknown'}; база: ${comparison.baseline_freshness || 'unknown'}; кандидат: ${comparison.candidate_freshness || 'unknown'}`), element('p', comparison.note || '')); }
                container.append(card);
            }
        }
        render();
        return {update(nextView) { view = nextView; render(); }, dispose() { container.replaceChildren(); }};
    };
})();
