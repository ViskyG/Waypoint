(() => {
    'use strict';
    const api = window.WaypointUI = window.WaypointUI || {};
    const el = (tag, cls, text) => { const node = document.createElement(tag); node.className = cls; if (text !== undefined) node.textContent = String(text); return node; };
    api.intentFor = node => node?.x_observability?.intent || null;
    api.nodeView = (view, id) => view.node_views?.[id] || {};
    api.activityText = projection => {
        const activity = projection.activity || projection.descendant_activity || projection.descendants || {};
        const active = activity.distinct_active_agents ?? activity.active_agents ?? activity.active_agent_count;
        const blocks = activity.distinct_active_leaves ?? activity.active_leaves ?? activity.active_blocks;
        return [active != null ? `${active} активных агентов внутри` : '', blocks != null ? `${blocks} активных конечных блоков` : ''].filter(Boolean).join(' · ');
    };
    api.reportedStatus = (view, id) => { const projection = api.nodeView(view, id); return projection.reported_status?.status ?? projection.reported_status ?? projection.status?.status ?? view.node_states?.find(state => state.id === id)?.status ?? 'Не указан'; };
    api.statusLabel = status => status === 'done' ? '✓ Готово' : status;
    api.resultFor = (view, id) => api.nodeView(view,id).status?.result || view.node_states?.find(state => state.id === id)?.result;
    api.appendDependencies = (container, projection) => {
        const prerequisites = projection.prerequisites;
        if (!prerequisites) return;
        for (const phase of ['start', 'finish']) {
            const requirements = prerequisites[phase]; if (!requirements) continue;
            const section = el('details', 'prerequisites'); section.append(el('summary', '', phase === 'start' ? 'Для начала' : 'Для завершения'));
            const list = Array.isArray(requirements) ? requirements : requirements.requirements || requirements.items || [requirements];
            if (!list.length) section.append(el('p', 'small-note', 'Дополнительные требования отсутствуют'));
            const labels = {available:'доступно',satisfied:'доступно',waived:'требование снято',conflict:'противоречивые подтверждения',missing:'ещё не получено',unavailable:'недоступно',stale:'устарело',unknown:'доступность не подтверждена',not_required:'не требуется'};
            for (const requirement of list) {
                const record = el('div','dependency-record');
                const availability = requirement.availability || requirement.state || 'unknown';
                const order = requirement.classification === 'order';
                record.dataset.relation = requirement.classification || 'legacy_unknown';
                record.append(el('strong','', (requirement.producer_id || requirement.declared_target_id || 'Требование') + ' · ' + (order ? 'Порядок · не блокирует' : labels[availability] || availability)));
                if (requirement.declared_target_id) record.append(el('p','small-note',`${requirement.producer_id} → ${requirement.declared_target_id} · ${phase === 'start' ? 'начало' : 'завершение'} · ${requirement.target_scope === 'subtree' ? 'блок и подблоки' : 'только указанный блок'}`));
                if (requirement.why) record.append(el('p','',requirement.why));
                if (requirement.workspace_ref) record.append(el('p','small-note','Рабочая копия: ' + JSON.stringify(requirement.workspace_ref)));
                if (requirement.inherited) record.append(el('small','small-note','Унаследовано от группы ' + (requirement.declared_target_id || '')));
                if (requirement.receipts?.length) record.append(el('p','small-note','Подтверждений: ' + requirement.receipts.length));
                if (requirement.stale_receipts?.length) record.append(el('p','small-note','Устаревших подтверждений: ' + requirement.stale_receipts.length));
                section.append(record);
            }
            container.append(section);
        }
        if (projection.dependency_warnings?.length) {
            const history = el('section','dependency-history-warning');
            history.append(el('h4','','Работа началась до подтверждения входов'));
            history.append(el('p','small-note','Сохранённое наблюдение о начале работы. Позднее подтверждение входов сохраняет эту историю.'));
            for (const warning of projection.dependency_warnings) {
                const record = el('div','dependency-record');
                record.append(el('p','',`Получено: ${warning.observed_at || 'время неизвестно'} · версия ${warning.basis?.plan_version || 'неизвестна'}`));
                for (const requirement of warning.requirements || []) record.append(el('p','',`${requirement.producer_id || requirement.edge_id} · при старте: ${requirement.availability || requirement.state || 'unknown'}`));
                history.append(record);
            }
            container.append(history);
        }
    };
    api.mountPlan = (container, initialView, {onOpenNode, preferences = {}}) => {
        let current = initialView;
        const expanded = new Set(preferences.expanded || []);
        const render = view => {
            const top = container.scrollTop; current = view; container.replaceChildren();
            const plan = view.plan; container.append(el('h1', '', plan.title || 'План проекта'));
            if (view.purpose || view.project?.purpose || plan.x_observability?.purpose) container.append(el('p', 'project-purpose', view.purpose || view.project?.purpose || plan.x_observability.purpose));
            container.append(el('p', 'small-note version-observation', view.version !== view.current_version ? 'Текущие наблюдения поверх старой структуры плана. Историческое воспроизведение не выполняется.' : 'Сообщённые статусы и активность потомков показаны раздельно.'));
            const appendNode = (id, node, depth, seen) => {
                if (seen.has(id)) return; seen.add(id);
                const row = el('article', 'plan-row'); row.dataset.node = id; row.style.setProperty('--depth', Math.min(depth, 12));
                const open = el('button', 'plan-node-link', id + ' · ' + node.title); open.onclick = () => onOpenNode(id); row.append(open);
                const intent = api.nodeView(view,id).intent || api.intentFor(node); row.append(el('p', intent ? 'plan-intent' : 'small-note missing-intent', intent?.summary || 'Описание для владельца пока не заполнено'));
                const status = api.reportedStatus(view,id); row.dataset.status = status;
                row.append(el('p', 'plan-status', 'Сообщено: ' + api.statusLabel(status)));
                const result = api.resultFor(view,id), checks = (view.checks || []).filter(check => check.node_id === id);
                if (result) { const proof = el('p','plan-result',result.summary || 'Результат сохранён'); row.append(proof); if (result.evidence_ref) row.append(el('p','evidence-reference',result.evidence_ref)); }
                const testCount = Object.keys(node.tests || {}).length;
                if (testCount) row.append(el('p','small-note plan-checks',`Подтверждено проверок: ${Object.keys(node.tests).filter(tid => checks.some(check => check.test_id === tid && check.outcome === 'passed')).length}/${testCount}`));
                const activity = api.activityText(api.nodeView(view, id)); if (activity) row.append(el('p', 'small-note descendant-activity', activity));
                if (intent) { const details = el('details', 'intent-details'); details.open = expanded.has(id); details.append(el('summary', '', 'Контекст и изменение')); for (const [label, field] of [['Зачем', 'context'], ['Что изменится', 'change'], ['Границы', 'scope']]) if (intent[field]) details.append(el('h4', '', label), el('p', 'prose', typeof intent[field] === 'string' ? intent[field] : JSON.stringify(intent[field]))); details.ontoggle = () => { if (details.open) expanded.add(id); else expanded.delete(id); preferences.expanded = [...expanded]; preferences.onChange?.(); }; row.append(details); }
                api.appendDependencies(row, api.nodeView(view, id)); container.append(row);
                for (const [childId, child] of Object.entries(plan.nodes)) if (child.parent === id) appendNode(childId, child, depth + 1, seen);
            };
            const seen = new Set(); for (const [id, node] of Object.entries(plan.nodes)) if (!node.parent || !plan.nodes[node.parent]) appendNode(id, node, 0, seen);
            for (const [id, node] of Object.entries(plan.nodes)) if (!seen.has(id)) appendNode(id, node, 0, seen);
            container.scrollTop = preferences.top ?? top;
        };
        container.onscroll = () => { preferences.top = container.scrollTop; preferences.onChange?.(); }; render(initialView);
        return {update: render, dispose() { preferences.top = container.scrollTop; preferences.expanded = [...expanded]; preferences.onChange?.(); container.onscroll = null; container.replaceChildren(); }};
    };
})();
