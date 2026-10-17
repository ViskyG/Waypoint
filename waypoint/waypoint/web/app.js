/* Waypoint's one UI: online read model or an explicitly fictional offline fixture.
   All provider/user strings go through textContent. No execution controls exist. */
(() => {
    'use strict';
    const $ = s => document.querySelector(s);
    const el = (tag, cls, text) => { const x = document.createElement(tag); if (cls)
        x.className = cls; if (text !== undefined)
        x.textContent = String(text); return x; };
    const btn = (text, action, cls = '') => { const b = el('button', cls, text); b.type = 'button'; b.onclick = action; return b; };
    const svg = (tag, attrs = {}) => { const x = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k, v] of Object.entries(attrs))
        x.setAttribute(k, v); return x; };
    const demo = window.WAYPOINT_DEMO || null;
    const ui = { project: 'demo', state: null, versions: [], scope: null, selected: null, actor: null, inspector: null, version: null, planMode: false, camera: { x: 60, y: 35, z: .82 }, cameras: {}, drag: null, cursor: 0, busy: false };
    const readers = new Map();
    let key = '', online = false, stopped = false;
    try {
        key = sessionStorage.getItem('waypoint-read-key') || '';
    }
    catch { }
    const initialHash = new URLSearchParams(location.hash.slice(1));
    if (initialHash.has('key')) {
        key = initialHash.get('key');
        try {
            sessionStorage.setItem('waypoint-read-key', key);
        }
        catch { }
        history.replaceState(null, '', location.pathname + location.search);
    }
    try {
        document.documentElement.dataset.theme = localStorage.getItem('waypoint-theme') || 'terracotta';
    }
    catch { }
    function themeLabel() { $('#theme span').textContent = document.documentElement.dataset.theme === 'obsidian' ? 'Обсидиан' : 'Терракота'; }
    themeLabel();
    $('#theme').onclick = () => { document.documentElement.dataset.theme = document.documentElement.dataset.theme === 'obsidian' ? 'terracotta' : 'obsidian'; themeLabel(); try {
        localStorage.setItem('waypoint-theme', document.documentElement.dataset.theme);
    }
    catch { } };
    function notice(text) { const n = $('#notice'); n.textContent = text; n.hidden = false; clearTimeout(n.timer); n.timer = setTimeout(() => n.hidden = true, 5500); }
    async function api(path) { const r = await fetch(path, { headers: { Authorization: 'Bearer ' + key }, cache: 'no-store' }); if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        throw Error(e.message || e.error || `HTTP ${r.status}`);
    } return r.json(); }
    const base = () => '/api/p/' + encodeURIComponent(ui.project);
    function nodeName(id) { return ui.state?.plan.nodes[id]?.title || ui.state?.ghosts?.[id]?.title || id; }
    function nodesWithGhosts() { return { ...ui.state.plan.nodes, ...ui.state.ghosts }; }
    function agentName(id) { return ui.state.agents.find(a => a.id === id)?.name || id; }
    function agentCode(id) { return /^A\d+$/.test(id) ? id : String(id).split('/').pop().slice(0, 6); }
    function childNodes(id) { const result = new Set([id]); let changed = true; while (changed) {
        changed = false;
        for (const [key, n] of Object.entries(ui.state.plan.nodes)) {
            if (result.has(n.parent) && !result.has(key)) {
                result.add(key);
                changed = true;
            }
        }
    } return result; }
    function childAgents(id) { const result = new Set([id]); let changed = true; while (changed) {
        changed = false;
        for (const a of ui.state.agents) {
            if (result.has(a.parent_id) && !result.has(a.id)) {
                result.add(a.id);
                changed = true;
            }
        }
    } return result; }
    function parents(id) { const result = [], seen = new Set(), nodes = ui.state.plan.nodes; while (id && nodes[id] && !seen.has(id)) {
        seen.add(id);
        result.unshift(id);
        id = nodes[id].parent;
    } return result; }
    function actorActive(a) { if (a?.activity_historical) return false; if (!['running', 'active'].includes(a?.activity))
        return false; if (demo || a.activity_source === 'demo')
        return true; const src = ui.state.sources.find(s => s.source_key === a.activity_source); return src && src.state === 'connected' && Date.now() - Date.parse(src.at) < 25000; }
    function visibleNodeFor(id) { const nodes = nodesWithGhosts(), seen = new Set(); while (id && nodes[id] && !seen.has(id)) {
        seen.add(id);
        if ((nodes[id].parent || null) === ui.scope)
            return id;
        id = nodes[id].parent;
    } return null; }
    function workActors(node) { const ids = new Set(); for (const scope of ui.state.scopes) {
        for (const id of scope.node_ids) {
            if (visibleNodeFor(id) === node)
                ids.add(scope.agent_id);
        }
    } return ui.state.agents.filter(a => ids.has(a.id)); }
    function nodeStatus(id) { return ui.state.node_states.find(s => s.id === id) || {}; }
    function nodeMessages(id, deep = true) { const ids = deep ? childNodes(id) : new Set([id]); return ui.state.items.filter(i => i.node_ids?.some(n => ids.has(n))); }
    function fmtTime(t) { const d = new Date(t); return Number.isFinite(+d) ? d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '—'; }
    function kindLabel(k) { return { agentMessage: '', userMessage: 'пользователь', reasoning: 'пояснение', commandExecution: 'команда', mcpToolCall: 'инструмент', fileChange: 'файлы' }[k] ?? k; }
    const itemKey = item => JSON.stringify([item.agent_id || '', item.id]);
    function hasSelection(box) { const selection = window.getSelection(); return selection && !selection.isCollapsed && (box.contains(selection.anchorNode) || box.contains(selection.focusNode)); }
    function patchMessage(box, item) {
        const signature = JSON.stringify(item);
        if (box._signature === signature) return;
        // Keep the actual selected DOM text intact while the reader is copying it.
        if (hasSelection(box)) { box._pendingItem = item; return; }
        box._pendingItem = null; box._signature = signature;
        const next = message(item);
        if (box.textContent !== next.textContent) box.replaceChildren(...next.childNodes);
        box.title = next.title;
    }
    function message(item) { const box = el('div', 'message'); box.dataset.item = item.id; box.dataset.itemKey = itemKey(item); box._signature = JSON.stringify(item); const meta = el('div', 'message-meta'); meta.append(el('b', '', agentCode(item.agent_id || '?')), el('span', '', fmtTime(item.at))); if (kindLabel(item.type))
        meta.append(el('span', 'message-kind', kindLabel(item.type))); box.append(meta); if (item.node_ids?.length || item.edge_ids?.length) box.append(el('small', 'message-origin', [...(item.node_ids || []), ...(item.edge_ids || [])].join(' · '))); box.append(el('div', 'message-text', item.text || (item.type === 'subAgentActivity' ? ['Событие подагента', item.kind, item.agent_thread_id, item.agent_path].filter(Boolean).join(' · ') : 'Без текстового содержимого'))); if (item.truncated)
        box.append(el('small', 'source-warning', 'Длинное содержимое ограничено; оригинал остаётся у источника.')); if (item.attribution === 'unassigned')
        box.title = 'Привязка к блоку не установлена'; return box; }
    document.addEventListener('selectionchange', () => { for (const box of document.querySelectorAll('.message')) if (box._pendingItem && !hasSelection(box)) patchMessage(box, box._pendingItem); });
    function readerFor(channel, kind, id, deep = true) {
        const key = JSON.stringify([ui.project, ui.version, channel, kind, id, deep]);
        if (!readers.has(key)) readers.set(key, { key, kind, id, deep, channel, limit: channel === 'card' ? 24 : 100, items: [], latest: [], pending: new Set(), follow: true, top: 0, needsRefresh: true, hasMore: false });
        return readers.get(key);
    }
    function detachReader(reader) { if (!reader?.scroll) return; reader.top = reader.scroll.scrollTop; reader.scroll = reader.list = reader.button = reader.more = null; }
    function bindReader(reader, list, scroll, button, more = null) {
        if (reader.scroll && reader.scroll !== scroll) detachReader(reader);
        reader.list = list; reader.scroll = scroll; reader.button = button; reader.more = more;
        scroll.onscroll = () => { reader.top = scroll.scrollTop; if (!reader.pending.size) reader.follow = scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight < 12; else if (scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight >= 12) reader.follow = false; };
        button.onclick = () => { reader.follow = true; reader.items = reader.latest.slice(-reader.limit); reader.pending.clear(); paintReader(reader); };
        if (more) more.onclick = () => loadReader(reader, true);
        paintReader(reader); if (reader.needsRefresh && !reader.loading) loadReader(reader);
    }
    function paintReader(reader, prepend = false) {
        if (!reader.list || !reader.scroll?.isConnected) return;
        const { list, scroll } = reader, oldHeight = scroll.scrollHeight, oldTop = scroll.scrollTop;
        const existing = new Map([...list.children].filter(x => x.dataset.itemKey).map(x => [x.dataset.itemKey, x]));
        const keys = new Set(reader.items.map(itemKey));
        for (const child of [...list.children]) if (!keys.has(child.dataset.itemKey)) child.remove();
        let previous = null;
        for (const item of reader.items) { const key = itemKey(item); let box = existing.get(key); if (box) patchMessage(box, item); else box = message(item); const target = previous ? previous.nextSibling : list.firstChild; if (target !== box) list.insertBefore(box, target); previous = box; }
        if (!reader.items.length && !list.children.length) list.append(el('div', 'empty-message', 'Пока нет сообщений'));
        reader.button.hidden = !reader.pending.size;
        reader.button.textContent = `Новые сообщения: ${reader.pending.size} · К последним ↓`;
        if (reader.more) { reader.more.hidden = !reader.hasMore; reader.more.disabled = !!reader.loading; }
        scroll.scrollTop = reader.follow ? scroll.scrollHeight : prepend ? oldTop + scroll.scrollHeight - oldHeight : reader.top;
        reader.top = scroll.scrollTop;
    }
    function updateReader(reader, items, result) {
        const old = new Map(reader.items.map(i => [itemKey(i), i]));
        reader.latest = items.slice(-reader.limit);
        const atTail = !reader.scroll || reader.scroll.scrollHeight - reader.scroll.scrollTop - reader.scroll.clientHeight < 12;
        if (reader.follow && atTail) { reader.items = reader.latest.slice(); reader.pending.clear(); if (result) { reader.before = result.before; reader.hasMore = result.has_more; } }
        else {
            reader.follow = false;
            for (const item of items) if (!old.has(itemKey(item)) && (!reader.items.length || (item.first_seq || 0) > (reader.items.at(-1).first_seq || 0))) reader.pending.add(itemKey(item));
            const revisions = new Map(items.map(i => [itemKey(i), i]));
            reader.items = reader.items.map(i => revisions.get(itemKey(i)) || i);
        }
        paintReader(reader);
    }
    async function loadReader(reader, older = false) {
        if (reader.loading) return;
        reader.loading = true;
        const generation = reader.generation || 0;
        try {
            const result = await stream(reader.kind, reader.id, reader.deep, older ? reader.before : null, reader.limit);
            if (!older && !reader.follow && reader.items.length) {
                const window = await stream(reader.kind, reader.id, reader.deep, Math.max(...reader.items.map(item => item.first_seq || 0)) + 1, Math.min(200, reader.items.length));
                const revisions = new Map(window.items.map(item => [itemKey(item), item]));
                reader.items = reader.items.map(item => revisions.get(itemKey(item)) || item);
            }
            if (older) { reader.follow = false; const combined = new Map([...result.items, ...reader.items].map(i => [itemKey(i), i])); reader.items = [...combined.values()].slice(0, 200); reader.before = result.before; reader.hasMore = result.has_more; paintReader(reader, true); }
            else { updateReader(reader, result.items, result); reader.needsRefresh = generation !== (reader.generation || 0); }
        } catch (e) { notice(e.message); }
        finally { reader.loading = false; if (reader.more) reader.more.disabled = false; if (reader.needsRefresh && generation !== (reader.generation || 0) && reader.scroll?.isConnected) setTimeout(() => loadReader(reader), 0); }
    }
    function invalidateReaders(events = null, previousState = null) {
        for (const reader of readers.values()) {
            const affected = !events || events.some(event => {
                if (event.kind === 'plan.changed' || event.kind === 'scope.set') return true;
                if (!['item.upsert', 'item.link', 'item.identity_corrected'].includes(event.kind)) return false;
                if (reader.kind === 'agent') { const actors = [event.agent_id, event.payload?.previous_agent_id].filter(Boolean); return actors.some(actor => reader.deep ? childAgents(reader.id).has(actor) : reader.id === actor); }
                if (reader.kind === 'outside') return true;
                const projections = [previousState, ui.state].flatMap(state => (state?.items || []).filter(item => item.id === event.payload?.item_id && [event.agent_id, event.payload?.previous_agent_id].includes(item.agent_id)));
                // The native envelope can be empty: attribution lives in Store, not in the source.
                // An older item outside both bounded snapshots must invalidate conservatively.
                if (!projections.length) return true;
                if (reader.kind === 'edge') return projections.some(item => item.edge_ids?.includes(reader.id)) || event.edge_ids?.includes(reader.id);
                const targets = reader.deep ? childNodes(reader.id) : new Set([reader.id]);
                return projections.some(item => item.node_ids?.some(id => targets.has(id))) || event.node_ids?.some(id => targets.has(id));
            });
            if (!affected) continue;
            reader.generation = (reader.generation || 0) + 1;
            reader.needsRefresh = true;
            if (reader.scroll?.isConnected) loadReader(reader);
        }
    }
    function selectActor(id) { ui.actor = ui.actor === id ? null : id; ui.selected = null; renderActors(); renderMap(); if (ui.actor)
        openInspector('agent', id, 'messages');
    else
        closeInspector(); }
    function keyedChildren(parent, children) {
        const keep = new Set(children);
        for (const child of [...parent.children]) if (!keep.has(child)) child.remove();
        children.forEach((child, index) => { if (parent.children[index] !== child) parent.insertBefore(child, parent.children[index] || null); });
    }
    function renderActors() {
        const strip = $('#agents'), rail = $('#orchestrators');
        const oldActors = new Map([...strip.children].map(card => [card.dataset.actor, card]));
        const oldRails = new Map([...rail.children].map(card => [card.dataset.actor, card]));
        const actorCards = [], railCards = [];
        const selected = ui.actor ? childAgents(ui.actor) : new Set();
        $('#active-count').textContent = ui.state.agents.filter(actorActive).length + ' в работе';
        const sorted = [...ui.state.agents].sort((a, b) => Number(actorActive(b)) - Number(actorActive(a)) || a.id.localeCompare(b.id));
        for (const actor of sorted) {
            const scopes = ui.state.scopes.find(scope => scope.agent_id === actor.id)?.node_ids || [];
            const signature = JSON.stringify([actor, scopes, selected.has(actor.id)]);
            let card = oldActors.get(actor.id);
            if (!card || card._signature !== signature) {
                card = btn('', () => selectActor(actor.id), 'agent-card');
                card.dataset.actor = actor.id; card._signature = signature;
                if (['completed', 'done'].includes(actor.activity)) card.classList.add('finished');
                if (selected.has(actor.id)) card.classList.add('selected');
                card.title = actor.id + (actor.activity_historical ? '\nИстория · ' + (actor.activity_reported_by || actor.activity_source || '') + ' · ' + (actor.activity_at || '') : '');
                const text = el('div');
                text.append(el('strong', '', actor.name || agentCode(actor.id)), el('small', '', scopes.join(' · ') || 'Вне карты'));
                if (actor.activity_historical) text.append(el('small', 'activity-provenance', 'История · ' + (actor.activity_reported_by || 'источник')));
                card.append(el('span', 'agent-code', agentCode(actor.id)), text);
            }
            actorCards.push(card);
            const children = ui.state.agents.filter(child => child.parent_id === actor.id);
            if (children.length) {
                const signature = JSON.stringify([actor.id, actor.name, ui.actor === actor.id, children.map(child => child.id)]);
                let card = oldRails.get(actor.id);
                if (!card || card._signature !== signature) {
                    card = btn('', () => selectActor(actor.id), 'orch' + (ui.actor === actor.id ? ' selected' : ''));
                    card.dataset.actor = actor.id; card._signature = signature;
                    const top = el('div', 'orch-top'); top.append(el('span', 'agent-code', agentCode(actor.id)), el('strong', '', actor.name || agentCode(actor.id)));
                    const tags = el('div', 'children'); children.forEach(child => tags.append(el('i', '', agentCode(child.id))));
                    card.append(top, tags);
                }
                railCards.push(card);
            }
        }
        keyedChildren(strip, actorCards); keyedChildren(rail, railCards);
        const outside = ui.state.items.filter(item => !item.node_ids?.length && !item.edge_ids?.length || item.node_ids?.some(id => !ui.state.plan.nodes[id] && !ui.state.ghosts[id]));
        $('#outside-count').textContent = outside.length;
        $('#reset-selection').hidden = !ui.actor && !ui.selected;
    }
    function renderToolbar() { const crumbs = $('#crumbs'); crumbs.replaceChildren(btn('Карта', () => enter(null))); for (const id of parents(ui.scope)) {
        crumbs.append(el('span', '', '›'), btn(id, () => enter(id)));
    } $('#up').disabled = !ui.scope; $('#up').onclick = () => enter(ui.state.plan.nodes[ui.scope]?.parent || null); $('#zoom').textContent = Math.round(ui.camera.z * 100) + '%'; $('#version').replaceChildren(); for (const v of ui.versions) {
        const option = el('option', '', `План ${v.ordinal}`);
        option.value = v.version;
        option.selected = v.version === ui.state.version;
        $('#version').append(option);
    } $('#map-note').textContent = ui.state.version !== ui.state.current_version ? 'Старый план · активность показана текущая' : ui.state.warnings?.length ? 'В плане есть циклические зависимости; работа не заблокирована' : ui.scope ? `Внутри ${ui.scope} · общий поток доступен по названию блока` : ''; }
    function lamp(check) { const span = el('span', 'lamp ' + (check?.outcome || 'not_run') + (check?.freshness === 'stale' ? ' stale' : ''), check?.outcome === 'passed' ? '✓' : ['failed', 'error'].includes(check?.outcome) ? '×' : ''); span.setAttribute('aria-label', check?.outcome || 'не запускался'); return span; }
    function renderNode(id, node, simple = false) {
        const card = el('article', 'node');
        card.dataset.node = id;
        const x = node.layout?.x ?? 0, y = node.layout?.y ?? 0;
        card.style.left = x + 'px';
        card.style.top = y + 'px';
        if (node.retired || node.absent_from_view)
            card.classList.add('ghost');
        let related = false;
        if (ui.actor) {
            const actors = childAgents(ui.actor);
            related = workActors(id).some(a => actors.has(a.id));
            card.classList.add(related ? 'highlight' : 'dim');
        }
        else if (ui.selected === id)
            card.classList.add('highlight');
        const test = el('div', 'test-row'), testBtn = btn('', () => openInspector('node', id, 'tests'));
        let passed = 0;
        const tests = Object.entries(node.tests || {});
        for (const [tid, def] of tests.slice(0, 16)) {
            const check = ui.state.checks.find(c => c.node_id === id && c.test_id === tid);
            if (check?.outcome === 'passed')
                passed++;
            const light = lamp(check);
            light.title = (def.label || tid) + ': ' + (check?.outcome || 'не запускался') + (check?.freshness !== 'current' ? ' · актуальность не подтверждена' : '');
            testBtn.append(light);
        }
        test.append(testBtn, el('span', 'test-count', `${passed}/${tests.length}`));
        const head = el('div', 'node-head'), title = el('div', 'title');
        title.append(el('span', 'node-id', id + (node.retired ? ' · прежний план' : node.absent_from_view ? ' · вне версии' : '')), el('h3', '', node.title));
        title.tabIndex = 0; title.setAttribute('role', 'button'); title.setAttribute('aria-label', 'Сообщения ' + id); title.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); title.click(); } };
        title.onclick = () => { ui.selected = id; renderMap(); openInspector('node', id, 'messages'); };
        head.append(title);
        const hasChild = Object.values(ui.state.plan.nodes).some(n => n.parent === id);
        if (hasChild) {
            const down = btn('↘', () => enter(id));
            down.title = 'Раскрыть внутренний граф';
            down.setAttribute('aria-label', 'Раскрыть ' + id);
            head.append(down);
        }
        const detail = btn('⋯', () => openInspector('node', id, 'assignment'));
        detail.title = 'Подробности';
        head.append(detail);
        const chat = el('div', 'messages');
        chat.dataset.chat = id;
        chat.append(el('div', 'empty-message', ui.planMode ? node.assignment : ''));
        const status = el('div', 'node-status'), state = nodeStatus(id), agents = workActors(id);
        const running = agents.some(actorActive);
        status.append(el('span', 'status-icon' + (running ? ' running' : state.status === 'done' ? ' done' : '')), btn(state.status || 'Запланировано', () => openInspector('node', id, 'status'), 'status-label'));
        const names = el('div', 'node-actors');
        for (const a of agents.slice(0, 4))
            names.append(btn(agentCode(a.id), () => selectActor(a.id)));
        status.append(names);
        const req = btn('ЗАДАНИЕ', () => openInspector('node', id, 'assignment'), 'node-tab assignment'), accept = btn('ПРИЁМКА', () => openInspector('node', id, 'acceptance'), 'node-tab acceptance');
        const latest = btn('', null, 'new-messages'); latest.hidden = true;
        card.append(test, head, chat, status, req, accept, latest);
        card.ondblclick = e => { if (hasChild && !e.target.closest('.messages,button'))
            enter(id); };
        return card;
    }
    function renderMap() {
        if (!ui.state)
            return;
        const world = $('#world');
        world.style.transform = `translate(${ui.camera.x}px, ${ui.camera.y}px) scale(${ui.camera.z})`;
        world.classList.toggle('overview', ui.camera.z < .55);
        const all = nodesWithGhosts(), current = Object.entries(all).filter(([, n]) => (n.parent || null) === ui.scope), vp = $('#viewport').getBoundingClientRect();
        const onScreen = current.filter(([, n]) => { const x = (n.layout?.x || 0) * ui.camera.z + ui.camera.x, y = (n.layout?.y || 0) * ui.camera.z + ui.camera.y; return x + 370 * ui.camera.z > -120 && y + 410 * ui.camera.z > -120 && x < vp.width + 120 && y < vp.height + 120; });
        const ns = $('#nodes');
        const mounted = new Map([...ns.children].map(card => [card.dataset.node, card]));
        const visible = new Set(onScreen.slice(0, 1000).map(([id]) => id));
        for (const [id, card] of mounted) if (!visible.has(id)) { detachReader(card._reader); card.remove(); }
        onScreen.slice(0, 1000).forEach(([id, node]) => {
            let card = mounted.get(id);
            const signature = JSON.stringify([node, nodeStatus(id), ui.state.checks.filter(c => c.node_id === id), workActors(id), ui.actor, ui.selected]);
            if (!card) { card = renderNode(id, node); ns.append(card); }
            else if (card._signature !== signature) {
                const next = renderNode(id, node);
                card.className = next.className; card.style.cssText = next.style.cssText;
                for (const child of [...next.children]) if (!child.classList.contains('messages') && !child.classList.contains('new-messages')) {
                    const old = [...card.children].find(x => x.className === child.className);
                    if (old) old.replaceWith(child); else card.append(child);
                }
            }
            card._signature = signature;
            const chat = card.querySelector('.messages');
            if (ui.camera.z >= .55 && !ui.planMode) {
                const reader = readerFor('card', 'node', id);
                if (card._reader !== reader || reader.scroll !== chat) { detachReader(card._reader); card._reader = reader; bindReader(reader, chat, chat, card.querySelector('.new-messages')); }
                else if (reader.needsRefresh && !reader.loading) loadReader(reader);
            }
        });
        const ed = $('#edges');
        const edgeSignature = JSON.stringify([ui.scope, ui.state.plan.edges, current.map(([id, n]) => [id, n.layout]), ui.state.items.filter(i => i.edge_ids?.length).map(i => [itemKey(i), i.edge_ids])]);
        if (ed._signature !== edgeSignature) {
        ed._signature = edgeSignature;
        ed.replaceChildren();
        const defs = svg('defs'), marker = svg('marker', { id: 'arrow', markerWidth: 8, markerHeight: 8, refX: 6, refY: 3, orient: 'auto', markerUnits: 'strokeWidth' });
        marker.append(svg('path', { d: 'M0,0 L6,3 L0,6', fill: 'none', stroke: 'var(--wait)', 'stroke-width': 1 }));
        defs.append(marker);
        ed.append(defs);
        const groups = new Map();
        for (const [eid, edge] of Object.entries(ui.state.plan.edges)) {
            const a = visibleNodeFor(edge.from), b = visibleNodeFor(edge.to);
            if (!a || !b || a === b)
                continue;
            const k = a + '|' + b;
            const g = groups.get(k) || { a, b, ids: [] };
            g.ids.push(eid);
            groups.set(k, g);
        }
        for (const { a, b, ids } of groups.values()) {
            const p = all[a].layout || {}, q = all[b].layout || {};
            let x1 = (p.x || 0) + 356, y1 = (p.y || 0) + 190, x2 = (q.x || 0) - 26, y2 = (q.y || 0) + 190;
            let d;
            if (x2 > x1)
                d = `M${x1},${y1} C${x1 + 70},${y1} ${x2 - 70},${y2} ${x2},${y2}`;
            else {
                x1 = (p.x || 0) + 165;
                y1 = (p.y || 0) + 387;
                x2 = (q.x || 0) + 165;
                y2 = (q.y || 0);
                d = `M${x1},${y1} C${x1},${y1 + 70} ${x2},${y2 - 70} ${x2},${y2}`;
            }
            const group = svg('g');
            const path = svg('path', { d, class: 'edge', 'marker-end': 'url(#arrow)' }), hit = svg('path', { d, class: 'edge-hit', tabindex: 0, role: 'button', 'aria-label': 'Связь ' + ids.join(', ') });
            const open = () => openInspector('edge', ids[0], 'messages');
            hit.onclick = open;
            hit.onkeydown = e => { if (e.key === 'Enter')
                open(); };
            group.append(path, hit);
            const msgs = ui.state.items.filter(i => i.edge_ids?.some(id => ids.includes(id))).length;
            if (msgs) {
                const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
                const dot = svg('circle', { cx, cy, r: 11, class: 'edge-dot' });
                dot.onclick = open;
                const label = svg('text', { x: cx, y: cy + 4, class: 'edge-caption' });
                label.textContent = String(msgs);
                group.append(dot, label);
            }
            ed.append(group);
        }
        }
        renderCrossScope();
        $('#empty').textContent = !current.length ? 'На этом уровне пока нет блоков' : '';
        $('#summary').textContent = `${current.length} блоков · ${Object.keys(ui.state.plan.edges).length} связей`;
        $('#zoom').textContent = Math.round(ui.camera.z * 100) + '%';
        if (onScreen.length > 1000)
            $('#map-note').textContent = 'Показано 1000 видимых блоков · приблизьте интересующий участок';
    }
    function renderCrossScope() {
        let links = $('#cross-scope');
        if (!links) { links = el('div', 'cross-scope'); links.id = 'cross-scope'; $('#viewport').append(links); }
        const external = Object.entries(ui.state.plan.edges).filter(([, edge]) => !!visibleNodeFor(edge.from) !== !!visibleNodeFor(edge.to));
        const signature = JSON.stringify([ui.scope, external]);
        if (links._signature === signature) return;
        links._signature = signature; links.replaceChildren();
        for (const [id, edge] of external.slice(0, 12)) links.append(btn(`${visibleNodeFor(edge.from) ? '→' : '←'} ${id} · ${visibleNodeFor(edge.from) ? edge.to : edge.from} (другой уровень)`, () => openInspector('edge', id), 'scope-link'));
    }
    async function copyId(value) { try { await navigator.clipboard.writeText(value); notice('Идентификатор скопирован'); } catch { notice(value); } }
    function enter(scope, writeHash = true) { if (scope && !ui.state.plan.nodes[scope])
        return; for (const card of $('#nodes').children) detachReader(card._reader); ui.cameras[ui.scope || '$root'] = { ...ui.camera }; ui.scope = scope; ui.camera = { ...(ui.cameras[scope || '$root'] || { x: 60, y: 30, z: .82 }) }; ui.selected = null; ui.actor = null; closeInspector(); if (writeHash) {
        const h = new URLSearchParams();
        h.set('project', ui.project);
        if (scope)
            h.set('scope', scope);
        history.pushState(null, '', '#' + h.toString());
    } renderToolbar(); renderActors(); renderMap(); }
    function cameraZoom(z, point) { const rect = $('#viewport').getBoundingClientRect(); const p = point || { x: rect.width / 2, y: rect.height / 2 }; z = Math.max(.12, Math.min(1.8, z)); const ratio = z / ui.camera.z; ui.camera.x = p.x - (p.x - ui.camera.x) * ratio; ui.camera.y = p.y - (p.y - ui.camera.y) * ratio; ui.camera.z = z; renderMap(); }
    function focusNode(id) { const node = nodesWithGhosts()[id]; if (!node)
        return notice('Блок не найден'); if ((node.parent || null) !== ui.scope)
        enter(node.parent || null); ui.selected = id; ui.actor = null; const rect = $('#viewport').getBoundingClientRect(); ui.camera.z = .92; ui.camera.x = rect.width * .38 - ((node.layout?.x || 0) + 165) * ui.camera.z; ui.camera.y = 40 - (node.layout?.y || 0) * ui.camera.z; renderMap(); renderActors(); }
    $('#plus').onclick = () => cameraZoom(ui.camera.z * 1.18);
    $('#minus').onclick = () => cameraZoom(ui.camera.z / 1.18);
    $('#zoom').onclick = () => cameraZoom(1);
    $('#fit').onclick = () => { const nodes = Object.values(nodesWithGhosts()).filter(n => (n.parent || null) === ui.scope); if (!nodes.length)
        return; const left = Math.min(...nodes.map(n => n.layout?.x || 0)) - 30, top = Math.min(...nodes.map(n => n.layout?.y || 0)), right = Math.max(...nodes.map(n => (n.layout?.x || 0) + 360)), bottom = Math.max(...nodes.map(n => (n.layout?.y || 0) + 390)); const r = $('#viewport').getBoundingClientRect(), z = Math.min(1, (r.width - 70) / (right - left), (r.height - 60) / (bottom - top)); ui.camera = { x: 35 - left * z, y: 30 - top * z, z: Math.max(.12, z) }; renderMap(); };
    $('#full').onclick = async () => { try {
        if (document.fullscreenElement)
            await document.exitFullscreen();
        else
            await document.documentElement.requestFullscreen();
    }
    catch {
        notice('Полноэкранный режим недоступен в этой среде');
    } };
    const viewport = $('#viewport');
    viewport.addEventListener('wheel', e => { if (e.target.closest('.messages') && ui.camera.z >= .55 && !e.ctrlKey)
        return; e.preventDefault(); const r = viewport.getBoundingClientRect(); cameraZoom(ui.camera.z * Math.exp(-e.deltaY * .0015), { x: e.clientX - r.left, y: e.clientY - r.top }); }, { passive: false });
    viewport.addEventListener('keydown', e => { if (e.target !== viewport || e.altKey || e.ctrlKey || e.metaKey) return; const delta = { ArrowLeft: [70, 0], ArrowRight: [-70, 0], ArrowUp: [0, 70], ArrowDown: [0, -70] }[e.key]; if (delta) { e.preventDefault(); ui.camera.x += delta[0]; ui.camera.y += delta[1]; renderMap(); } else if (e.key === '+' || e.key === '=') { e.preventDefault(); cameraZoom(ui.camera.z * 1.18); } else if (e.key === '-') { e.preventDefault(); cameraZoom(ui.camera.z / 1.18); } });
    viewport.addEventListener('pointerdown', e => { if (e.button !== 1 && (e.button !== 0 || e.target.closest('.node,button,.edge-hit,.edge-dot')))
        return; e.preventDefault(); ui.drag = { x: e.clientX, y: e.clientY, camera: { ...ui.camera } }; viewport.setPointerCapture(e.pointerId); viewport.classList.add('dragging'); });
    viewport.addEventListener('pointermove', e => { if (!ui.drag)
        return; ui.camera.x = ui.drag.camera.x + e.clientX - ui.drag.x; ui.camera.y = ui.drag.camera.y + e.clientY - ui.drag.y; renderMap(); });
    function endDrag() { ui.drag = null; viewport.classList.remove('dragging'); }
    viewport.addEventListener('pointerup', endDrag);
    viewport.addEventListener('pointercancel', endDrag);
    $('#search').addEventListener('keydown', e => { if (e.key !== 'Enter')
        return; const q = e.target.value.trim().toLowerCase(); const found = Object.entries(nodesWithGhosts()).find(([id, n]) => id.toLowerCase() === q) || Object.entries(nodesWithGhosts()).find(([id, n]) => (id + ' ' + n.title).toLowerCase().includes(q)); if (found) {
        focusNode(found[0]);
        openInspector('node', found[0], 'messages');
    }
    else
        notice('Нет подходящего блока'); });
    $('#reset-selection').onclick = () => { ui.actor = ui.selected = null; renderMap(); renderActors(); closeInspector(); };
    $('#outside').onclick = () => openInspector('outside', null, 'messages');
    $('#close').onclick = closeInspector;
    function closeInspector() { if (ui.inspector?.reader) detachReader(ui.inspector.reader); $('#inspector').hidden = true; ui.inspector = null; }
    function blockSection(body, title, content) { body.append(el('h4', '', title), el('div', 'prose', content)); }
    async function stream(kind, id, deep = true, before = null, limit = 100) {
        if (demo) {
            let items = ui.state.items;
            if (kind === 'node') {
                const ids = deep ? childNodes(id) : new Set([id]);
                items = items.filter(i => i.node_ids.some(n => ids.has(n)));
            }
            else if (kind === 'agent')
                items = items.filter(i => deep ? childAgents(id).has(i.agent_id) : i.agent_id === id);
            else if (kind === 'edge')
                items = items.filter(i => i.edge_ids.includes(id));
            else if (kind === 'outside')
                items = items.filter(i => !i.node_ids.length && !i.edge_ids.length || i.node_ids.some(n => !ui.state.plan.nodes[n] && !ui.state.ghosts[n]));
            const eligible = before ? items.filter(i => i.first_seq < before) : items; const page = eligible.slice(-limit); return { items: page, has_more: eligible.length > limit, before: page[0]?.first_seq };
        }
        if (kind === 'outside')
            return { items: ui.state.items.filter(i => !i.node_ids.length && !i.edge_ids.length || i.node_ids.some(n => !ui.state.plan.nodes[n] && !ui.state.ghosts[n])), has_more: false };
        const q = new URLSearchParams({ limit, deep: String(deep), version: ui.state.version });
        q.set(kind, id);
        if (before)
            q.set('before', before);
        return api(base() + '/items?' + q);
    }
    function inspectorSignature(kind, id, tab) {
        const node = nodesWithGhosts()[id], actor = ui.state.agents.find(actor => actor.id === id);
        if (kind === 'node') {
            if (tab === 'assignment') return JSON.stringify([node, ui.state.plan.edges]);
            if (tab === 'acceptance') return JSON.stringify([node?.acceptance, nodeStatus(id).result]);
            if (tab === 'tests') return JSON.stringify([node?.tests, ui.state.checks.filter(check => check.node_id === id)]);
            if (tab === 'status') return JSON.stringify([nodeStatus(id), workActors(id)]);
        }
        if (kind === 'agent') return JSON.stringify([actor, ui.state.scopes.filter(scope => scope.agent_id === id)]);
        return null;
    }
    function refreshInspectorDetails() {
        const inspector = ui.inspector;
        if (!inspector || inspector.tab === 'messages' || inspector.kind === 'diff' || inspector.signature === inspectorSignature(inspector.kind, inspector.id, inspector.tab)) return;
        if (hasSelection($('#inspector-body'))) { inspector.needsRefresh = true; return; }
        const top = $('#inspector-body').scrollTop;
        openInspector(inspector.kind, inspector.id, inspector.tab, inspector.deep).then(() => { $('#inspector-body').scrollTop = top; });
    }
    document.addEventListener('selectionchange', () => { if (ui.inspector?.needsRefresh) refreshInspectorDetails(); });
    async function openInspector(kind, id, tab = 'messages', deep = true) {
        if (ui.inspector?.reader) detachReader(ui.inspector.reader);
        if (kind === 'agent') deep = false;
        const state = { kind, id, tab, deep, signature: inspectorSignature(kind, id, tab) };
        ui.inspector = state;
        const inspector = $('#inspector'), body = $('#inspector-body'), tabs = $('#tabs');
        inspector.hidden = false;
        body.replaceChildren();
        tabs.replaceChildren();
        $('#inspector-id').textContent = id || 'Непривязанная работа';
        $('#inspector-title').textContent = kind === 'node' ? nodeName(id) : kind === 'agent' ? agentName(id) : kind === 'edge' ? 'На переходе' : 'Вне карты';
        const choices = kind === 'node' ? [['assignment', 'Задание'], ['acceptance', 'Приёмка'], ['messages', 'Сообщения'], ['tests', 'Тесты'], ['status', 'Статус']] : kind === 'agent' ? [['messages', 'Сообщения'], ['work', 'Работы']] : [['messages', 'Сообщения']];
        for (const [value, name] of choices)
            tabs.append(btn(name, () => openInspector(kind, id, value, deep), value === tab ? 'current' : ''));
        if (kind === 'agent') { const actor = ui.state.agents.find(actor => actor.id === id); if (actor?.activity_historical) body.append(el('p', 'small-note activity-provenance', 'История · ' + (actor.activity_reported_by || actor.activity_source || '') + ' · ' + actor.activity_at)); }
        if (id) body.append(btn(kind === 'agent' ? 'Копировать native/block ID' : 'Копировать ID блока/связи', () => copyId(id), 'copy-id'));
        if (kind === 'edge') {
            const edge = ui.state.plan.edges[id];
            if (edge) { body.append(el('p', 'small-note', 'Исходные концы связи, включая другие уровни карты:')); for (const endpoint of [edge.from, edge.to]) body.append(btn(endpoint + ' · ' + nodeName(endpoint), () => focusNode(endpoint), 'related')); }
        }
        if (tab === 'messages') {
            if (kind === 'node' && childNodes(id).size > 1)
                body.append(btn(deep ? 'С подблоками ✓' : 'Только этот блок', () => openInspector(kind, id, tab, !deep), 'more scope-toggle'));
            if (kind === 'node' && deep) body.append(el('p', 'small-note', 'Общий поток блока и подблоков; исходные сообщения сохранены один раз.'));
            const more = btn('Более ранние сообщения', null, 'more older-messages'); more.hidden = true;
            const list = el('div', 'inspector-messages'), latest = btn('', null, 'new-messages inspector-latest'); latest.hidden = true;
            body.append(more, list, latest);
            state.reader = readerFor('inspector', kind, id, deep);
            bindReader(state.reader, list, body, latest, more);
            return;
        }
        if (kind === 'agent' && tab === 'work') {
            const scopes = ui.state.scopes.filter(s => s.agent_id === id);
            body.append(el('p', 'small-note', 'Фактическая область работы, не очередь обязательных заданий.'));
            for (const s of scopes)
                for (const n of s.node_ids)
                    body.append(btn(n + ' · ' + nodeName(n), () => focusNode(n), 'related'));
            const a = ui.state.agents.find(a => a.id === id);
            blockSection(body, 'Родитель', a?.parent_id ? agentName(a.parent_id) : 'Не указан');
            blockSection(body, 'Идентификатор агента', id);
            blockSection(body, 'Контейнер сессии', a?.session_id || 'Неизвестен');
            return;
        }
        const node = nodesWithGhosts()[id];
        if (!node)
            return;
        const status = nodeStatus(id);
        if (tab === 'assignment') {
            blockSection(body, 'Задание', node.assignment);
            for (const r of node.source_refs || []) {
                body.append(el('h4', '', r.label || 'Источник'));
                if (/^https?:\/\//.test(r.uri || '')) {
                    const a = el('a', 'prose', r.uri);
                    a.href = r.uri;
                    a.rel = 'noreferrer noopener';
                    a.target = '_blank';
                    body.append(a);
                }
                else
                    body.append(el('div', 'prose', r.uri || ''));
            }
            const edgeEntries = Object.entries(ui.state.plan.edges).filter(([, e]) => e.to === id || e.from === id);
            if (edgeEntries.length)
                body.append(el('h4', '', 'Связи'));
            for (const [, e] of edgeEntries) {
                const other = e.to === id ? e.from : e.to;
                body.append(btn((e.to === id ? '← ' : '→ ') + other + ' · ' + nodeName(other), () => focusNode(other), 'related'));
            }
        }
        else if (tab === 'acceptance') {
            body.append(el('h4', '', 'Ожидалось'));
            for (const [aid, a] of Object.entries(node.acceptance || {})) {
                const row = el('div', 'criterion');
                row.append(el('b', '', aid), el('span', '', a.text || a.label || ''));
                body.append(row);
            }
            body.append(el('h4', '', 'Получено'), el('div', 'result-block', status.result?.summary || 'Результат ещё не описан'));
            body.append(el('h4', '', 'Расхождения с ожиданиями'), el('div', 'result-block', status.result?.difference || 'Не указаны. Это не доказательство отсутствия расхождений.'));
            if (status.result?.plan_version)
                body.append(el('div', 'result-tag', 'Результат относительно ' + status.result.plan_version));
        }
        else if (tab === 'tests') {
            for (const [tid, t] of Object.entries(node.tests || {})) {
                const check = ui.state.checks.find(c => c.node_id === id && c.test_id === tid);
                const row = el('div', 'checkline'), text = el('div');
                text.append(el('div', '', t.label || tid), el('small', '', `${tid} · ${check?.outcome || 'не запускался'} · ${check?.freshness === 'current' ? 'актуальность заявлена исполнителем' : 'актуальность не подтверждена'}`));
                row.append(lamp(check), text);
                body.append(row);
            }
            body.append(el('p', 'small-note', 'Успешные тесты, актуальность результата и статус задачи — отдельные сведения. Карта не меняет статус исполнителя.'));
        }
        else if (tab === 'status') {
            blockSection(body, 'Сообщённый статус', status.status || 'Не указан');
            blockSection(body, 'Пояснение', status.explanation || 'Не указано');
            blockSection(body, 'Последнее сообщение о статусе', status.at || 'Нет');
            for (const a of workActors(id))
                body.append(btn(agentName(a.id) + ' · ' + a.activity, () => openInspector('agent', a.id, 'messages'), 'related'));
        }
        if (Object.values(ui.state.plan.nodes).some(n => n.parent === id))
            body.append(btn('Открыть внутренний граф ↘', () => enter(id), 'more'));
        body.append(btn('Копировать адрес блока', async () => { const link = location.origin + location.pathname + '#project=' + encodeURIComponent(ui.project) + '&scope=' + encodeURIComponent(node.parent || '') + '&node=' + encodeURIComponent(id); try {
            await navigator.clipboard.writeText(link);
            notice('Адрес скопирован');
        }
        catch {
            notice('Блок: ' + id);
        } }, 'more'));
    }
    $('#diff').onclick = async () => { const index = ui.versions.findIndex(v => v.version === ui.state.version), previous = ui.versions[index + 1]; if (!previous)
        return notice('Предыдущей версии нет'); openInspector('diff', null, 'diff'); $('#inspector-title').textContent = 'Изменения плана'; const body = $('#inspector-body'); body.replaceChildren(); try {
        let changes;
        if (demo) {
            const before = demo.states[previous.version].plan, after = ui.state.plan;
            changes = objectDiff(before, after);
        }
        else
            changes = (await api(base() + '/diff?' + new URLSearchParams({ before: previous.version, after: ui.state.version }))).changes;
        for (const c of changes) {
            const row = el('div', 'diff-row');
            row.append(el('code', '', c.op + ' · ' + c.path.join('/')));
            if (c.before !== undefined)
                row.append(el('pre', '', '− ' + JSON.stringify(c.before)));
            if (c.after !== undefined)
                row.append(el('pre', '', '+ ' + JSON.stringify(c.after)));
            body.append(row);
        }
        if (!changes.length)
            body.append(el('p', '', 'Структура не менялась'));
    }
    catch (e) {
        notice(e.message);
    } };
    function objectDiff(a, b, path = []) { if (JSON.stringify(a) === JSON.stringify(b))
        return []; if (a && b && !Array.isArray(a) && !Array.isArray(b) && typeof a === 'object' && typeof b === 'object') {
        return [...new Set([...Object.keys(a), ...Object.keys(b)])].flatMap(k => objectDiff(a[k], b[k], [...path, k]));
    } return [{ path, op: a === undefined ? 'add' : b === undefined ? 'remove' : 'replace', before: a, after: b }]; }
    $('#version').onchange = async (e) => { ui.version = e.target.value; await refresh(true); };
    $('#project').onchange = async (e) => { closeInspector(); for (const reader of readers.values()) detachReader(reader); readers.clear(); $('#nodes').replaceChildren(); ui.project = e.target.value; ui.cursor = 0; ui.version = null; ui.scope = null; ui.camera = { x: 60, y: 35, z: .82 }; await refresh(true); };
    async function refresh(includeVersions = false, events = null) { if (ui.busy)
        return; ui.busy = true; try {
        let state;
        if (demo) {
            state = demo.states[ui.version || demo.current];
            ui.versions = demo.versions;
        }
        else {
            state = await api(base() + '/state' + (ui.version ? '?version=' + encodeURIComponent(ui.version) : ''));
            if (includeVersions)
                ui.versions = await api(base() + '/versions');
        }
        const previousState = ui.state;
        ui.state = state;
        invalidateReaders(events && (state.cursor || 0) <= ui.cursor ? events : null, previousState);
        ui.cursor = Math.max(ui.cursor, state.cursor || 0);
        if (ui.scope && !state.plan.nodes[ui.scope]) {
            ui.scope = null;
            notice('Этот блок отсутствует в выбранной версии. История сохранена.');
        }
        $('.project-title').textContent = 'Карта исполнения';
        renderToolbar();
        renderActors();
        renderMap();
        online = true;
        $('#foot-status').classList.remove('source-warning');
        $('#foot-status').textContent = demo || ui.project === 'demo' ? 'Демо · вымышленные события' : 'Локальный сервис · тексты не отправляются в облако';
        refreshInspectorDetails();
    }
    catch (e) {
        online = false;
        $('#foot-status').textContent = 'Нет связи · показаны последние полученные данные';
        $('#foot-status').classList.add('source-warning');
        notice(e.message);
    }
    finally {
        ui.busy = false;
    } }
    async function watch() { while (!stopped && !demo) {
        try {
            const requestedProject = ui.project;
            const reply = await api(base() + '/events?' + new URLSearchParams({ after: ui.cursor, wait: 12, limit: 200 }));
            if (ui.project !== requestedProject)
                continue;
            if (reply.events.length) {
                ui.cursor = reply.cursor;
                await refresh(reply.events.some(e => e.kind === 'plan.changed'), reply.events);
            }
            else if (!online)
                await refresh(true);
        }
        catch {
            online = false;
            $('#foot-status').textContent = 'Связь прервана · исполнители не остановлены';
            $('#foot-status').classList.add('source-warning');
            await new Promise(r => setTimeout(r, 1800));
        }
    } }
    async function boot() { try {
        const projects = demo ? [{ project_id: 'demo', title: 'Маршруты армий' }] : await api('/api/projects');
        if (!projects.length) {
            $('#empty').textContent = 'Пока нет карт. Импортируйте план через wp plan-import.';
            return;
        }
        const hash = new URLSearchParams(location.hash.slice(1));
        ui.project = projects.some(p => p.project_id === hash.get('project')) ? hash.get('project') : projects[0].project_id;
        $('#project').replaceChildren();
        for (const p of projects) {
            const o = el('option', '', p.title);
            o.value = p.project_id;
            o.selected = p.project_id === ui.project;
            $('#project').append(o);
        }
        $('#connection').textContent = demo ? 'Демо' : 'Локально';
        $('#connection').classList.toggle('demo', !!demo);
        await refresh(true);
        if (hash.get('scope'))
            enter(hash.get('scope'), false);
        if (hash.get('node'))
            focusNode(hash.get('node'));
        watch();
    }
    catch (e) {
        $('#empty').textContent = 'Откройте локальный адрес из команды wp url. Ключ доступа хранится только в этой вкладке.';
        $('#foot-status').textContent = e.message;
    } }
    window.addEventListener('popstate', () => { if (!ui.state)
        return; const p = new URLSearchParams(location.hash.slice(1)); enter(p.get('scope') || null, false); if (p.get('node'))
        focusNode(p.get('node')); });
    window.addEventListener('resize', () => renderMap());
    window.addEventListener('beforeunload', () => { stopped = true; });
    document.addEventListener('keydown', e => { if (e.key === 'Escape')
        closeInspector(); if (e.altKey && e.key === 'ArrowUp' && ui.scope) {
        e.preventDefault();
        enter(ui.state.plan.nodes[ui.scope]?.parent || null);
    } });
    // Developer diagnostic is read-only and does not expose credentials.
    window.waypointView = () => ({ scope: ui.scope, camera: { ...ui.camera }, visibleNodes: document.querySelectorAll('.node').length, version: ui.state?.version, project: ui.project });
    boot();
})();
