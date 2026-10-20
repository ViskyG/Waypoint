(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    api.registerTranslations('plan', {
        en: {
            active_agents: '{count} active agents inside', active_blocks: '{count} active leaf blocks',
            status_done: '✓ Done', status_not_reported: 'Not reported', start_requirements: 'To start', finish_requirements: 'To finish',
            no_requirements: 'No additional requirements', availability_available: 'available', availability_satisfied: 'available',
            availability_waived: 'requirement waived', availability_conflict: 'conflicting evidence', availability_missing: 'not received yet',
            availability_unavailable: 'unavailable', availability_stale: 'stale', availability_unknown: 'availability unconfirmed', availability_not_required: 'not required',
            requirement: 'Requirement', order_only: 'Order · does not block', phase_start: 'start', phase_finish: 'finish',
            scope_subtree: 'block and descendants', scope_node: 'specified block only',
            dependency_target: '{producer} → {target} · {phase} · {scope}', workspace: 'Working copy: {ref}', inherited: 'Inherited from group {id}',
            receipt_count: 'Receipts: {count}', stale_receipt_count: 'Stale receipts: {count}',
            early_work: 'Work started before inputs were confirmed', early_work_note: 'Saved observation of work starting. Later input confirmation preserves this history.',
            incident_counts: 'Periods with the same basis: {periods} · ledger records: {records}',
            recent_incidents: 'Showing the latest 20 periods. Complete records are preserved in the event ledger.',
            incident_observations: '{count} observations in one period', incident_range: '{first} — {last} · receipt {firstSeq}–{lastSeq}',
            unknown: 'unknown', raw_records: 'Original records: latest {count}; ledger preserved',
            warning_received: 'Received: {time} · version {version}', warning_requirement: '{producer} · at start: {availability}',
            project_plan: 'Project plan', historic_structure: 'Current observations over an older plan structure. This is not a historical replay.',
            status_activity_note: 'Reported statuses and descendant activity are shown separately.', missing_intent: 'The owner-facing description has not been filled in yet',
            reported: 'Reported: {status}', result_saved: 'Result saved', checks_confirmed: 'Checks confirmed: {passed}/{total}',
            intent_details: 'Context and change', intent_context: 'Why', intent_change: 'What will change', intent_scope: 'Scope'
        },
        ru: {
            active_agents: '{count} активных агентов внутри', active_blocks: '{count} активных конечных блоков',
            status_done: '✓ Готово', status_not_reported: 'Не указан', start_requirements: 'Для начала', finish_requirements: 'Для завершения',
            no_requirements: 'Дополнительные требования отсутствуют', availability_available: 'доступно', availability_satisfied: 'доступно',
            availability_waived: 'требование снято', availability_conflict: 'противоречивые подтверждения', availability_missing: 'ещё не получено',
            availability_unavailable: 'недоступно', availability_stale: 'устарело', availability_unknown: 'доступность не подтверждена', availability_not_required: 'не требуется',
            requirement: 'Требование', order_only: 'Порядок · не блокирует', phase_start: 'начало', phase_finish: 'завершение',
            scope_subtree: 'блок и подблоки', scope_node: 'только указанный блок',
            dependency_target: '{producer} → {target} · {phase} · {scope}', workspace: 'Рабочая копия: {ref}', inherited: 'Унаследовано от группы {id}',
            receipt_count: 'Подтверждений: {count}', stale_receipt_count: 'Устаревших подтверждений: {count}',
            early_work: 'Работа началась до подтверждения входов', early_work_note: 'Сохранённое наблюдение о начале работы. Позднее подтверждение входов сохраняет эту историю.',
            incident_counts: 'Периодов с одинаковым основанием: {periods} · записей журнала: {records}',
            recent_incidents: 'Показаны последние 20 периодов. Полные записи сохранены в журнале событий.',
            incident_observations: '{count} наблюдений одного периода', incident_range: '{first} — {last} · receipt {firstSeq}–{lastSeq}',
            unknown: 'неизвестно', raw_records: 'Исходные записи: последние {count}; журнал сохранён',
            warning_received: 'Получено: {time} · версия {version}', warning_requirement: '{producer} · при старте: {availability}',
            project_plan: 'План проекта', historic_structure: 'Текущие наблюдения поверх старой структуры плана. Историческое воспроизведение не выполняется.',
            status_activity_note: 'Сообщённые статусы и активность потомков показаны раздельно.', missing_intent: 'Описание для владельца пока не заполнено',
            reported: 'Сообщено: {status}', result_saved: 'Результат сохранён', checks_confirmed: 'Подтверждено проверок: {passed}/{total}',
            intent_details: 'Контекст и изменение', intent_context: 'Зачем', intent_change: 'Что изменится', intent_scope: 'Границы'
        }
    });
    const t = (key, values) => api.t('plan.' + key, values);
    const availabilityLabel = value => ['available', 'satisfied', 'waived', 'conflict', 'missing', 'unavailable', 'stale', 'unknown', 'not_required'].includes(value) ? t('availability_' + value) : value;
    const el = (tag, cls, text) => { const node = document.createElement(tag); node.className = cls; if (text !== undefined) node.textContent = String(text); return node; };
    api.intentFor = node => node?.x_observability?.intent || null;
    api.nodeView = (view, id) => view.node_views?.[id] || {};
    api.activityText = projection => {
        const activity = projection.activity || projection.descendant_activity || projection.descendants || {};
        const active = activity.distinct_active_agents ?? activity.active_agents ?? activity.active_agent_count;
        const blocks = activity.distinct_active_leaves ?? activity.active_leaves ?? activity.active_blocks;
        return [active != null ? t('active_agents', {count: active}) : '', blocks != null ? t('active_blocks', {count: blocks}) : ''].filter(Boolean).join(' · ');
    };
    api.reportedStatus = (view, id) => { const projection = api.nodeView(view, id); return projection.reported_status?.status ?? projection.reported_status ?? projection.status?.status ?? view.node_states?.find(state => state.id === id)?.status ?? 'not_reported'; };
    api.statusLabel = status => status === 'done' ? t('status_done') : status === 'not_reported' ? t('status_not_reported') : status;
    api.resultFor = (view, id) => api.nodeView(view,id).status?.result || view.node_states?.find(state => state.id === id)?.result;
    api.appendDependencies = (container, projection) => {
        const prerequisites = projection.prerequisites;
        if (!prerequisites) return;
        for (const phase of ['start', 'finish']) {
            const requirements = prerequisites[phase]; if (!requirements) continue;
            const section = el('details', 'prerequisites'); section.dataset.disclosure = 'prerequisites-' + phase; section.append(el('summary', '', t(phase === 'start' ? 'start_requirements' : 'finish_requirements')));
            const list = Array.isArray(requirements) ? requirements : requirements.requirements || requirements.items || [requirements];
            if (!list.length) section.append(el('p', 'small-note', t('no_requirements')));
            for (const requirement of list) {
                const record = el('div','dependency-record');
                const availability = requirement.availability || requirement.state || 'unknown';
                const order = requirement.classification === 'order';
                record.dataset.relation = requirement.classification || 'legacy_unknown';
                record.append(el('strong','', (requirement.producer_id || requirement.declared_target_id || t('requirement')) + ' · ' + (order ? t('order_only') : availabilityLabel(availability))));
                if (requirement.declared_target_id) record.append(el('p','small-note',t('dependency_target', {producer: requirement.producer_id, target: requirement.declared_target_id, phase: t(phase === 'start' ? 'phase_start' : 'phase_finish'), scope: t(requirement.target_scope === 'subtree' ? 'scope_subtree' : 'scope_node')})));
                if (requirement.why) record.append(el('p','',requirement.why));
                if (requirement.workspace_ref) record.append(el('p','small-note',t('workspace', {ref: JSON.stringify(requirement.workspace_ref)})));
                if (requirement.inherited) record.append(el('small','small-note',t('inherited', {id: requirement.declared_target_id || ''})));
                if (requirement.receipts?.length) record.append(el('p','small-note',t('receipt_count', {count: requirement.receipts.length})));
                if (requirement.stale_receipts?.length) record.append(el('p','small-note',t('stale_receipt_count', {count: requirement.stale_receipts.length})));
                section.append(record);
            }
            container.append(section);
        }
        if (projection.dependency_warnings?.length) {
            const history = el('section','dependency-history-warning');
            history.append(el('h4','',t('early_work')));
            history.append(el('p','small-note',t('early_work_note')));
            if (projection.dependency_incidents?.length) {
                history.append(el('p','small-note',t('incident_counts', {periods: projection.dependency_incident_count ?? projection.dependency_incidents.length, records: projection.dependency_warning_count})));
                if (projection.dependency_incidents_has_more) history.append(el('p','small-note',t('recent_incidents')));
                for (const incident of projection.dependency_incidents) {
                    const record=el('div','dependency-incident');record.dataset.incident=incident.incident_id;
                    record.append(el('strong','',t('incident_observations', {count: incident.receipt_count})),el('p','small-note',t('incident_range', {first: incident.first_observed_at || t('unknown'), last: incident.last_observed_at || t('unknown'), firstSeq: incident.first_seq, lastSeq: incident.last_seq})));
                    for (const requirement of incident.requirements || []) record.append(el('p','',`${requirement.producer_id || requirement.edge_id} · ${availabilityLabel(requirement.availability || 'unknown')}`));
                    history.append(record);
                }
            }
            const raw=el('details','dependency-warning-raw');raw.dataset.disclosure = 'warning-raw';raw.append(el('summary','',t('raw_records', {count: projection.dependency_warnings.length})));
            for (const warning of projection.dependency_warnings) {
                const record = el('div','dependency-record');
                record.append(el('p','',t('warning_received', {time: warning.observed_at || t('unknown'), version: warning.basis?.plan_version || t('unknown')})));
                for (const requirement of warning.requirements || []) record.append(el('p','',t('warning_requirement', {producer: requirement.producer_id || requirement.edge_id, availability: availabilityLabel(requirement.availability || requirement.state || 'unknown')})));
                raw.append(record);
            }
            history.append(raw);
            container.append(history);
        }
    };
    api.mountPlan = (container, initialView, {onOpenNode, preferences = {}}) => {
        let current = initialView;
        const expanded = new Set(preferences.expanded || []);
        const disclosures = new Map();
        const render = view => {
            const top = container.scrollTop;
            for (const row of container.querySelectorAll('.plan-row[data-node]')) for (const details of row.querySelectorAll('details[data-disclosure]')) disclosures.set(JSON.stringify([row.dataset.node, details.dataset.disclosure]), details.open);
            current = view; container.replaceChildren();
            const plan = view.plan; container.append(el('h1', '', plan.title || t('project_plan')));
            if (view.purpose || view.project?.purpose || plan.x_observability?.purpose) container.append(el('p', 'project-purpose', view.purpose || view.project?.purpose || plan.x_observability.purpose));
            container.append(el('p', 'small-note version-observation', t(view.version !== view.current_version ? 'historic_structure' : 'status_activity_note')));
            const appendNode = (id, node, depth, seen) => {
                if (seen.has(id)) return; seen.add(id);
                const row = el('article', 'plan-row'); row.dataset.node = id; row.style.setProperty('--depth', Math.min(depth, 12));
                const open = el('button', 'plan-node-link', id + ' · ' + node.title); open.onclick = () => onOpenNode(id); row.append(open);
                const intent = api.nodeView(view,id).intent || api.intentFor(node); row.append(el('p', intent ? 'plan-intent' : 'small-note missing-intent', intent?.summary || t('missing_intent')));
                const status = api.reportedStatus(view,id); row.dataset.status = status;
                row.append(el('p', 'plan-status', t('reported', {status: api.statusLabel(status)})));
                const result = api.resultFor(view,id), checks = (view.checks || []).filter(check => check.node_id === id);
                if (result) { const proof = el('p','plan-result',result.summary || t('result_saved')); row.append(proof); if (result.evidence_ref) row.append(el('p','evidence-reference',result.evidence_ref)); }
                const testCount = Object.keys(node.tests || {}).length;
                if (testCount) row.append(el('p','small-note plan-checks',t('checks_confirmed', {passed: Object.keys(node.tests).filter(tid => checks.some(check => check.test_id === tid && check.outcome === 'passed')).length, total: testCount})));
                const activity = api.activityText(api.nodeView(view, id)); if (activity) row.append(el('p', 'small-note descendant-activity', activity));
                if (intent) { const details = el('details', 'intent-details'); details.dataset.disclosure = 'intent'; details.open = expanded.has(id); details.append(el('summary', '', t('intent_details'))); for (const [label, field] of [['intent_context', 'context'], ['intent_change', 'change'], ['intent_scope', 'scope']]) if (intent[field]) details.append(el('h4', '', t(label)), el('p', 'prose', typeof intent[field] === 'string' ? intent[field] : JSON.stringify(intent[field]))); details.ontoggle = () => { if (details.open) expanded.add(id); else expanded.delete(id); preferences.expanded = [...expanded]; preferences.onChange?.(); }; row.append(details); }
                api.appendDependencies(row, api.nodeView(view, id));
                for (const details of row.querySelectorAll('details[data-disclosure]')) { const key = JSON.stringify([id, details.dataset.disclosure]); if (disclosures.has(key)) details.open = disclosures.get(key); }
                container.append(row);
                for (const [childId, child] of Object.entries(plan.nodes)) if (child.parent === id) appendNode(childId, child, depth + 1, seen);
            };
            const seen = new Set(); for (const [id, node] of Object.entries(plan.nodes)) if (!node.parent || !plan.nodes[node.parent]) appendNode(id, node, 0, seen);
            for (const [id, node] of Object.entries(plan.nodes)) if (!seen.has(id)) appendNode(id, node, 0, seen);
            container.scrollTop = preferences.top ?? top;
        };
        container.onscroll = () => { preferences.top = container.scrollTop; preferences.onChange?.(); }; render(initialView);
        const unsubscribe = api.onLanguageChange(() => render(current));
        return {update: render, dispose() { unsubscribe(); preferences.top = container.scrollTop; preferences.expanded = [...expanded]; preferences.onChange?.(); container.onscroll = null; container.replaceChildren(); }};
    };
})();
