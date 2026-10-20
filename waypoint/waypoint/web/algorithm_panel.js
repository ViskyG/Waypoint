/* Curated algorithm records: DOM-only display, no source execution or file reads. */
(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    api.registerTranslations('algorithms', {
        en: {
            repository: 'Repository', empty: 'No algorithms have been described for this scope yet.',
            definition: 'Definition r{revision}', codeLinked: 'Code linked', implementationPlanned: 'Implementation planned',
            correctness: 'Correctness: {state}', confirmed: 'confirmed', failedCheck: 'a check failed', unchecked: 'not checked',
            measured: 'Measurements recorded', notMeasured: 'No measurements', installed: 'Integration confirmed', notInstalled: 'Integration not confirmed',
            evidenceCount: 'Total evidence: {total} · on this page: {page}',
            correctnessConflict: 'Current checks conflict; a passing result does not cancel a failed result.',
            comparisonsSummary: 'Total comparisons: {total}; missing basis: {unresolved}. {scope}',
            pageComparisons: 'Only comparisons on this page are shown below.',
            registryComparisons: 'Open history to see individual evidence and comparisons.',
            descendant: '{node} (descendant)', inputs: 'Inputs', outputs: 'Outputs', steps: 'Steps', invariants: 'Invariants',
            edgeCases: 'Edge cases', sourceCode: 'Source code', testability: 'Testability', missingCases: 'Missing checks', resourceRisks: 'Resource risks',
            stale: 'stale', current: 'current revision', unknown: 'unknown',
            passed: 'passed', failed: 'failed', notRun: 'not run',
            evidenceSummary: '{event} · {freshness} · {outcome}', staleReasons: 'Reasons for staleness', evidence: 'Evidence',
            measurement: '{metric}: {value} {unit}; n={count}; {statistic}; {method}',
            measurementBasis: 'Environment: {environment}; data: {dataset}; workload: {workload}; semantics: {semantics}',
            measurementAbsent: 'No measurement',
            comparison: 'Comparison: {state}; {reasons} · evidence: {freshness}; baseline: {baseline}; candidate: {candidate}',
            comparisonNotMeasured: 'not measured', comparisonNotComparable: 'not comparable', comparisonNotEstablished: 'not established',
            comparisonRegressed: 'regressed', comparisonUnchanged: 'unchanged', comparisonImproved: 'improved',
            newer: 'Newer evidence', older: 'Earlier evidence', pages: 'Evidence pages'
        },
        ru: {
            repository: 'Репозиторий', empty: 'Для этой области алгоритмы ещё не описаны.',
            definition: 'Определение r{revision}', codeLinked: 'Код указан', implementationPlanned: 'Реализация запланирована',
            correctness: 'Корректность: {state}', confirmed: 'подтверждена', failedCheck: 'есть неуспешная проверка', unchecked: 'не проверена',
            measured: 'Измерения записаны', notMeasured: 'Измерений нет', installed: 'Интеграция подтверждена', notInstalled: 'Интеграция не подтверждена',
            evidenceCount: 'Всего свидетельств: {total} · на этой странице: {page}',
            correctnessConflict: 'Есть противоречивые текущие проверки; успешный результат не отменяет неуспешный.',
            comparisonsSummary: 'Сравнений всего: {total}; не найдено основание: {unresolved}. {scope}',
            pageComparisons: 'Ниже показаны сравнения только этой страницы.',
            registryComparisons: 'Откройте историю для отдельных свидетельств и сравнений.',
            descendant: '{node} (потомок)', inputs: 'Входы', outputs: 'Результаты', steps: 'Шаги', invariants: 'Инварианты',
            edgeCases: 'Пограничные случаи', sourceCode: 'Исходный код', testability: 'Проверяемость', missingCases: 'Недостающие проверки', resourceRisks: 'Риски ресурсов',
            stale: 'устарело', current: 'текущая версия', unknown: 'неизвестно',
            passed: 'успешно', failed: 'неуспешно', notRun: 'не выполнялась',
            evidenceSummary: '{event} · {freshness} · {outcome}', staleReasons: 'Причины устаревания', evidence: 'Свидетельства',
            measurement: '{metric}: {value} {unit}; n={count}; {statistic}; {method}',
            measurementBasis: 'Среда: {environment}; данные: {dataset}; нагрузка: {workload}; семантика: {semantics}',
            measurementAbsent: 'Измерение отсутствует',
            comparison: 'Сравнение: {state}; {reasons} · свидетельство: {freshness}; база: {baseline}; кандидат: {candidate}',
            comparisonNotMeasured: 'нет измерений', comparisonNotComparable: 'несопоставимо', comparisonNotEstablished: 'не установлено',
            comparisonRegressed: 'ухудшение', comparisonUnchanged: 'без изменений', comparisonImproved: 'улучшение',
            newer: 'Более новые свидетельства', older: 'Более ранние свидетельства', pages: 'Страницы свидетельств'
        }
    });
    const t = (key, params) => api.t('algorithms.' + key, params);
    const freshness = value => ({stale: t('stale'), current: t('current'), unknown: t('unknown')})[value || 'unknown'] || value;
    const outcome = value => ({passed: t('passed'), failed: t('failed'), not_run: t('notRun')})[value || 'not_run'] || value;
    const comparisonKeys = {not_measured: 'comparisonNotMeasured', not_comparable: 'comparisonNotComparable', not_established: 'comparisonNotEstablished', regressed: 'comparisonRegressed', unchanged: 'comparisonUnchanged', improved: 'comparisonImproved'};
    function element(tag, text, className) { const node = document.createElement(tag); if (text != null) node.textContent = String(text); if (className) node.className = className; return node; }
    function list(parent, label, values) { if (!values?.length) return; const section = element('section'); section.append(element('h4', label)); const ul = element('ul'); for (const value of values) ul.append(element('li', value)); section.append(ul); parent.append(section); }
    function reference(parent, ref, repository, revision) {
        const text = `${ref.path || ''}${ref.symbol ? ' · ' + ref.symbol : ''}${revision ? ' @ ' + revision : ''}`;
        const line = element('p', text, 'algorithm-reference');
        // Local paths are displayed as data. Only an explicit repository URL can navigate.
        if (typeof repository === 'string') { try { const url = new URL(repository); if (['http:', 'https:'].includes(url.protocol)) { const a = element('a', t('repository')); a.href = url.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; line.append(document.createTextNode(' · '), a); } } catch (_) {} }
        parent.append(line);
    }
    api.mountAlgorithms = function (container, initialView, callbacks = {}) {
        let view = initialView;
        function render() {
            // Only the presentation changes. Keep the current page, expanded evidence and reader position.
            const expanded = new Map(Array.from(container.querySelectorAll('details.algorithm-evidence'), node => [node.dataset.evidence, node.open]));
            const scroll = []; for (let node = container; node; node = node.parentElement) scroll.push([node, node.scrollTop, node.scrollLeft]);
            container.replaceChildren();
            const algorithms = Array.isArray(view) ? view : view?.algorithms || [];
            if (!algorithms.length) container.append(element('p', t('empty'), 'empty'));
            for (const record of algorithms) {
                const d = record.definition || record;
                const card = element('article', null, 'algorithm-card'); card.dataset.algorithm = record.id || d.id;
                const title = element('button', d.title || record.id, 'algorithm-title'); title.type = 'button'; title.onclick = () => callbacks.onOpenAlgorithm?.(record.id || d.id); card.append(title);
                card.append(element('p', d.purpose));
                const status = element('p', null, 'algorithm-status');
                const correctness = {passed: 'confirmed', failed: 'failedCheck', not_run: 'unchecked'}[record.tested] || 'unchecked';
                for (const label of [t('definition', {revision: d.definition_revision || '?'}), t(record.implemented ? 'codeLinked' : 'implementationPlanned'), t('correctness', {state: t(correctness)}), t(record.measured ? 'measured' : 'notMeasured'), t(record.installed ? 'installed' : 'notInstalled')]) status.append(element('span', label + ' · '));
                card.append(status);
                if (record.evidence_count != null) {
                    card.append(element('p', t('evidenceCount', {total: record.evidence_count, page: (record.evidence || []).length}), 'algorithm-history-summary'));
                    if (record.correctness_conflict) card.append(element('p', t('correctnessConflict'), 'source-warning'));
                    if (record.comparisons_summary) card.append(element('p', t('comparisonsSummary', {total: record.comparisons_summary.total, unresolved: record.comparisons_summary.unresolved, scope: t(record.comparisons_scope === 'page' ? 'pageComparisons' : 'registryComparisons')}), 'small-note'));
                }
                for (const association of record.associations || []) { const b = element('button', association.direct ? association.node_id : t('descendant', {node: association.node_id})); b.type = 'button'; b.onclick = () => callbacks.onOpenNode?.(association.node_id); card.append(b); }
                list(card, t('inputs'), d.inputs); list(card, t('outputs'), d.outputs); list(card, t('steps'), d.steps); list(card, t('invariants'), d.invariants); list(card, t('edgeCases'), d.edge_cases);
                if (d.implementation) { card.append(element('h4', t('sourceCode'))); for (const ref of d.implementation.refs || []) reference(card, ref, d.implementation.repository, d.implementation.revision); }
                if (d.testability) { card.append(element('h4', t('testability')), element('p', d.testability.strategy)); for (const ref of d.testability.test_refs || []) reference(card, ref); list(card, t('missingCases'), d.testability.missing_cases); }
                list(card, t('resourceRisks'), d.resource_risks);
                for (const evidence of record.evidence || []) {
                    const p = evidence.payload || {}; const details = element('details', null, 'algorithm-evidence');
                    details.dataset.evidence = evidence.event_id; details.open = expanded.get(evidence.event_id) || false;
                    details.append(element('summary', t('evidenceSummary', {event: evidence.event_id, freshness: freshness(evidence.freshness), outcome: outcome(p.correctness?.outcome)})));
                    details.append(element('p', `${evidence.source || ''} · ${evidence.at || ''}`));
                    // Reasons, paths, measurement values and notes are recorded evidence, never translated as prose.
                    list(details, t('staleReasons'), evidence.stale_reasons); list(details, t('evidence'), p.correctness?.evidence_refs);
                    if (p.measurement) {
                        const m = p.measurement;
                        details.append(element('p', t('measurement', {metric: m.metric, value: m.value, unit: m.unit, count: m.n, statistic: m.statistic, method: m.method})), element('p', t('measurementBasis', {environment: m.environment_ref, dataset: m.dataset_ref, workload: m.workload_ref, semantics: m.semantic_revision})));
                    } else details.append(element('p', t('measurementAbsent')));
                    if (p.note) details.append(element('p', p.note)); card.append(details);
                }
                for (const comparison of record.comparisons || []) {
                    card.append(element('p', t('comparison', {
                        state: comparisonKeys[comparison.state] ? t(comparisonKeys[comparison.state]) : comparison.state,
                        reasons: (comparison.reasons || []).join(', '), freshness: freshness(comparison.freshness),
                        baseline: freshness(comparison.baseline_freshness), candidate: freshness(comparison.candidate_freshness)
                    })), element('p', comparison.note || ''));
                }
                if (record.evidence_scope === 'page') {
                    const controls = element('div', null, 'algorithm-pages'); controls.setAttribute('aria-label', t('pages'));
                    if (callbacks.canGoNewer) { const newer = element('button', t('newer'), 'algorithm-newer'); newer.onclick = () => callbacks.onNewer?.(); controls.append(newer); }
                    if (record.has_more) { const older = element('button', t('older'), 'algorithm-older'); older.onclick = () => callbacks.onOlder?.(record.before); controls.append(older); }
                    card.append(controls);
                }
                container.append(card);
            }
            for (const [node, top, left] of scroll) { node.scrollTop = top; node.scrollLeft = left; }
        }
        render(); const unsubscribe = api.onLanguageChange(render);
        return {update(nextView) { view = nextView; render(); }, dispose() { unsubscribe(); container.replaceChildren(); }};
    };
})();
