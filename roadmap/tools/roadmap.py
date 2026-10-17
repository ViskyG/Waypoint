#!/usr/bin/env python3
"""Read/validate/render one Waypoint roadmap. No live sources, agents or shared writes.

Working paths in source_refs resolve relative to the roadmap directory. Generated
views are disposable; ROADMAP.plan.json is the only authored work definition.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import platform
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'waypoint'


def unique_object(pairs):
    value = {}
    for k, v in pairs:
        if k in value:
            raise ValueError('Duplicate JSON key: ' + k)
        value[k] = v
    return value


def load(path=None):
    value = json.loads((path or ROOT / 'ROADMAP.plan.json').read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    return value.get('plan', value)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def fingerprint(plan):
    return hashlib.sha256(json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def parents(plan, node_id):
    result, seen = [], set()
    while node_id is not None:
        if node_id in seen:
            raise ValueError('Parent cycle')
        seen.add(node_id)
        result.append(node_id)
        node_id = plan['nodes'][node_id].get('parent')
    return result


def predecessors(plan, node_id, inherit=False):
    targets = parents(plan, node_id) if inherit else [node_id]
    return sorted({edge['from'] for edge in plan['edges'].values() if edge['to'] in targets})


def children(plan, node_id):
    return [key for key, node in plan['nodes'].items() if node.get('parent') == node_id]


def complete_set(plan, completed):
    done = set(completed) | set(plan.get('x_roadmap', {}).get('initial_supplied_ids', []))
    # Group metadata may be displayed as supplied when all its children are supplied.
    # Packet completion remains a real executor declaration, never derived from labels.
    for key, node in plan['nodes'].items():
        if node.get('x_roadmap', {}).get('kind') == 'group':
            cs = children(plan, key)
            if cs and all(c in done for c in cs):
                done.add(key)
    return done


def frontier(plan, completed=(), stages=False):
    done = complete_set(plan, completed)
    kind = 'stage' if stages else 'packet'
    ready, waiting = [], []
    for key, node in plan['nodes'].items():
        if node.get('x_roadmap', {}).get('kind') != kind or key in done:
            continue
        if stages and any(p in done for p in parents(plan, key)[1:] if plan['nodes'][p].get('x_roadmap', {}).get('kind') == 'packet'):
            continue
        missing = [v for v in predecessors(plan, key, inherit=stages) if v not in done]
        if missing:
            waiting.append({'id': key, 'requires': missing})
        else:
            ready.append(key)
    return {'meaning': 'planning frontier from supplied source + explicit completion receipts; not live status or assignment',
            'completed_receipts': sorted(set(completed)), 'ready': ready, 'waiting': waiting}


def heading(plan):
    return '> Сгенерировано из `ROADMAP.plan.json`, SHA-256 содержимого `' + fingerprint(plan) + '`.\n> Это представление плана, не самостоятельный источник статусов. Менять JSON и затем выполнять `python tools/roadmap.py render`.\n\n'


def block_text(plan, key, level=2):
    node = plan['nodes'][key]
    x = node.get('x_roadmap', {})
    deps = predecessors(plan, key)
    lines = [('#' * level) + ' ' + key + ' — ' + node['title'], '', node['assignment'], '',
             '**Предшественники:** ' + (', '.join(deps) or 'нет дополнительных прямых зависимостей') + '.', '', '**Условия приёмки**', '']
    lines += [f'- `{aid}` — {a["text"]}' for aid, a in node['acceptance'].items()]
    if node['tests']:
        lines += ['', '**Планируемые проверки — исходы ещё не получены**', '']
        for tid, t in node['tests'].items():
            lines += [f'- `{tid}` **{t["label"]}.** {t["procedure"]} Уровень: {t["evidence_level"]}. Инвалидируется: {t["invalidated_by"]}']
    if x.get('delivered_source'):
        result = x['delivered_source']
        lines += ['', '**Уже поставлено:** ' + ', '.join('`' + p + '`' for p in result['paths']) + '.',
                  'Статус поставки: `SOURCE_DELIVERED`; целевая приёмка: `NOT_RUN`. Повторной реализации не требуется.']
    return '\n'.join(lines) + '\n'


def packet_text(plan, key):
    out = '# Пакет ' + key + '\n\n' + heading(plan)
    out += 'Все относительные пути ниже считаются от каталога `roadmap/`, не от `packets/`. '
    out += 'Назначения в этом документе нет; сначала координация с текущим владельцем работ.\n\n'
    out += block_text(plan, key)
    cs = children(plan, key)
    if cs:
        out += '\n## Вложенные этапы того же пакета\n\n'
        for c in cs:
            out += block_text(plan, c, 3) + '\n'
    out += '\n## Возврат\n\nИспользовать `../waypoint/reports/RETURN_TO_CHAT_RU.md` и дополнить полями из `RETURN_FIELDS.md`. '
    out += 'Вернуть actual/expected diff, текущий plan_version, изменённые пути, реальную базу, пройденные/непройденные проверки и безопасное следующее действие. '
    out += 'Не копировать приватные тексты, auth или всю рабочую БД в отчёт.\n'
    return out


def rendered(plan):
    h = heading(plan)
    packets = [k for k, n in plan['nodes'].items() if n.get('x_roadmap', {}).get('kind') == 'packet']
    stages = [k for k, n in plan['nodes'].items() if n.get('x_roadmap', {}).get('kind') == 'stage']
    out = '# Waypoint — дорожная карта реализации\n\n' + h
    out += '**MIXED.** Доводим имеющийся продукт; C01–C04 — поставленная исходная база, C05–C07 — сохранённые идентичности оставшихся капсул. '
    out += 'WPT-R00 добавлен как короткая проверка рабочей базы и первый импорт.\n\n'
    out += f'Состав: {len(plan["nodes"])} узлов, {len(plan["edges"])} зависимостей, {len(packets)} исполнимых пакета и {len(stages)} вложенных этапов. Группа исходников не является новой задачей.\n\n'
    out += '```text\nC01–C04 (исходники поставлены)\n        ↓\n      R00 (рабочая база + импорт этой карты)\n        ├── C05 (источник / привязки / индекс) ──┐\n        └── C06 (непрерывное чтение) ──────────┤\n                                             ↓\n                           C07 (одна интеграция и передача)\n\nВнутренний стык: C05.3 → C06.3. Он не останавливает C06.1/C06.2.\n```\n\n'
    out += '## Пакеты и волны\n\n| ID | Результат | Прямые зависимости | Волна |\n|---|---|---|---|\n'
    for k in packets:
        n = plan['nodes'][k]
        out += f'| [{k}](packets/{k}.md) | {n["title"]} | {", ".join(predecessors(plan, k))} | {n["x_roadmap"]["wave"]} |\n'
    out += '\n## Исходное доступное действие\n\n'
    out += '`' + ', '.join(frontier(plan)['ready']) + '` — плановый старт, не запущенный исполнитель. '
    out += 'После принятого R00 доступны C05/C06, после обоих — C07. Проверка существующего head обязательна перед импортом, но Waypoint не вводит блокировку работы агента.\n\n'
    out += '## Единый граф и наследование требований\n\n'
    out += 'Родитель — пакет работ; его условия дополняются проверками дочерних этапов. Нельзя выполнять родителя повторно после детей. '
    out += 'Внешние зависимости родителя действуют на входе всех его детей. Внутренние рёбра уточняют порядок только соответствующих этапов. '
    out += 'Показать карту можно в `PREVIEW.html`; требования и приёмка уже находятся в native полях импортируемого JSON.\n\n'
    out += '## Где что читать\n\n'
    out += '`CODEX_START.md` — передача исполнителю. `FORMAT.md` — контракт одного графа. `RUNNER_WAVES.md` — производная группировка, не новая очередь. '
    out += '`AUTHORING_PROFILE.md` и `templates/PROJECT.plan.json` — правило для следующих карт. `evidence/VALIDATION.json` — реально выполненные проверки этого пакета.\n\n'
    out += '## Исходная база\n\n'
    for k in plan['x_roadmap']['initial_supplied_ids']:
        n = plan['nodes'][k]
        out += f'**{k} — {n["title"]}.** '+ n['assignment'].split('\n\n')[0] + '\n\n'
    out += '## Дерево вложенных этапов\n\n'
    for k in packets:
        out += f'### {k} — {plan["nodes"][k]["title"]}\n\n'
        cs = children(plan, k)
        if not cs:
            out += 'Короткий пакет без дополнительного дробления.\n\n'
        for c in cs:
            out += f'**{c} — {plan["nodes"][c]["title"]}.** '+ plan['nodes'][c]['assignment'].split('\n\n')[0] + '\n\n'
    out += '## Изменение плана\n\n'
    out += 'После начала работ текущую версию получать из Store: export → изменение только нужных полей → import с base_version и стабильным request_id. '
    out += 'Git хранит контрольные снимки. Не перезаписывать живую карту этим начальным JSON и не редактировать отдельно производные задания. '
    out += 'Обновлённый экспорт сохранять как новый authoring baseline; затем заново формировать Markdown/волны/preview.\n'
    wave_text = '# Runner — производная группировка того же графа\n\n' + h
    wave_text += 'Это описание состава передачи, **не исполняемые команды Runner и не новая очередь**. Протокол установленного Runner здесь не исследован и не подменяется вымышленным API. '
    wave_text += 'Udot выбирает разрешённый канал и привязывает волну к фактическому snapshot/base до применения. MIXED допускает прямой Codex без ожидания необязательного чата.\n\n'
    for wave, info in plan['x_roadmap']['waves'].items():
        members = [k for k in packets if plan['nodes'][k]['x_roadmap'].get('wave') == wave]
        wave_text += f'## {wave} — {info["title"]}\n\nСостав: '+ ', '.join('`'+m+'`' for m in members)+'.\n\n'
        wave_text += '**Вход:** '+ '; '.join(m+' ← '+', '.join(predecessors(plan,m)) for m in members)+'.\n\n'
        wave_text += '**Граница интеграции:** '+info['integration_boundary']+'\n\n'
        if wave == 'RW-01':
            wave_text += 'C05 владеет adapters/collector/Store/API/миграцией и узким CLI binding seam. C06 владеет web assets/browser fixtures. '
            wave_text += 'Один backend-писатель сериализует C05.1–C05.3; C06.1/C06.2 готовятся параллельно. C06.3 ждёт C05.3. '
            wave_text += 'В runner-пакет UI не включать store.py/server.py. При изменении публичного read-контракта интегратор уведомляет C06 до его применения.\n\n'
        if wave == 'RW-00':
            wave_text += 'Можно подготовить чтение/fixtures офлайн, но нельзя объявлять рабочую базу принятой до реальной проверки. После возвращения машины сначала сверка local/Git/Drive, потом применение.\n\n'
        if wave == 'RW-02':
            wave_text += 'Применяет один интегратор. Здесь требуются целевые наблюдения и обычный браузер, поэтому нельзя объединять её с чистой подготовкой RW-01 в одну неподтверждённую волну.\n\n'
    wave_text += '## При задержке или отказе\n\nНет чат-результата — Codex может выполнить тот же разрешённый scope, переиспользовав доступные исходники. '
    wave_text += 'Есть живой писатель — его участок не дублируется. Runner недоступен — сохраняется пакет для обычной локальной интеграции, но не создаётся альтернативный протокол команд. '
    wave_text += 'Отказ конкретной проверки блокирует её утверждение, а не независимые подготовительные задачи.\n'
    result = {'ROADMAP.md': out, 'RUNNER_WAVES.md': wave_text,
              'INITIAL_FRONTIER.json': encoded(frontier(plan)),
              'INITIAL_IMPORT.json': encoded({'request_id':'roadmap-initial-'+fingerprint(plan)[:24], 'base_version':None, 'plan':plan})}
    for k in packets:
        result['packets/'+k+'.md'] = packet_text(plan, k)
    return result


def render(plan, check=False):
    generated = rendered(plan)
    stale = []
    for name, text in generated.items():
        path = ROOT / name
        if check:
            if not path.is_file() or path.read_text(encoding='utf-8') != text:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
    if stale:
        raise ValueError('Stale generated views: ' + ', '.join(stale))
    return {'generated_files':list(generated),'check_only':check}


def validate(plan):
    # Pure source/Store checks in disposable paths. Never connect to existing Codex.
    sys.path.insert(0, str(BASE))
    from waypoint.domain import validate_plan, ContractError, digest
    from waypoint.store import Store
    import jsonschema
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    normalized, warnings = validate_plan(plan)
    check('native_domain_keeps_entire_plan', normalized == plan)
    check('planned_dependency_graph_is_acyclic', not warnings)
    schema = json.loads((BASE/'schemas/plan.schema.json').read_text())
    jsonschema.Draft202012Validator(schema).validate(plan)
    check('native_json_schema_accepts_roadmap', True)
    check('all_nodes_have_assignment_and_acceptance', all(n.get('assignment') and n.get('acceptance') for n in plan['nodes'].values()))
    check('existing_capsule_ids_preserved', all('WPT-C%02d'%i in plan['nodes'] for i in range(1,8)))
    for k,n in plan['nodes'].items():
        check('native_packet_contains_read_set_'+k, all(r['uri'] in n['assignment'] for r in n.get('source_refs',[])))
        for r in n.get('source_refs',[]):
            uri=r['uri']
            if '://' in uri:continue
            p=(ROOT/uri).resolve()
            check('source_exists_'+k+'_'+uri,p.exists() and p.is_relative_to(ROOT.parent))
        if n['x_roadmap']['kind'] in ('packet','stage'):
            check('checks_have_procedure_and_invalidation_'+k, bool(n['tests']) and all(t.get('procedure') and t.get('invalidated_by') for t in n['tests'].values()))
    check('initial_packet_frontier_is_R00',frontier(plan)['ready']==['WPT-R00'])
    check('after_R00_C05_C06_parallel',frontier(plan,['WPT-R00'])['ready']==['WPT-C05','WPT-C06'])
    check('C06_reader_starts_without_C05_completion','WPT-C06.1' in frontier(plan,['WPT-R00'],True)['ready'])
    check('C06_rich_test_waits_for_index','WPT-C06.3' not in frontier(plan,['WPT-R00','WPT-C06.1','WPT-C06.2'],True)['ready'])
    check('C06_rich_test_starts_after_index','WPT-C06.3' in frontier(plan,['WPT-R00','WPT-C06.1','WPT-C06.2','WPT-C05.3'],True)['ready'])
    check('C07_requires_both_branches',frontier(plan,['WPT-R00','WPT-C05','WPT-C06'])['ready']==['WPT-C07'])
    check('finished_frontier_is_empty',not frontier(plan,['WPT-R00','WPT-C05','WPT-C06','WPT-C07'])['ready'])
    with tempfile.TemporaryDirectory(prefix='waypoint-roadmap-check-') as tmp:
        store = Store(Path(tmp)/'check.sqlite')
        try:
            first = store.import_plan(plan, None, 'roadmap-validator-first')
            readback = store.plan(plan['project_id'])['plan']
            check('actual_store_roundtrip_all_fields',readback==plan)
            check('store_exact_request_retry_is_idempotent',store.import_plan(plan,None,'roadmap-validator-first')==first)
            export = {'base_version':first['version'],'plan':readback}
            check('export_wrapper_retains_metadata',json.loads(encoded(export))['plan']['x_roadmap']==plan['x_roadmap'])
            a=copy.deepcopy(plan);b=copy.deepcopy(plan)
            a['nodes']['WPT-C05']['title']+=' · A'
            av=store.import_plan(a,first['version'],'roadmap-validator-a')
            b['nodes']['WPT-C06']['title']+=' · B'
            bv=store.import_plan(b,first['version'],'roadmap-validator-b',merge=True)
            merged=store.plan(plan['project_id'])['plan']
            check('disjoint_stale_edits_merge',merged['nodes']['WPT-C05']['title']==a['nodes']['WPT-C05']['title'] and merged['nodes']['WPT-C06']['title']==b['nodes']['WPT-C06']['title'])
            c=copy.deepcopy(merged);d=copy.deepcopy(merged)
            c['nodes']['WPT-C07']['acceptance']['A-01']['text']='proposal-c'
            d['nodes']['WPT-C07']['acceptance']['A-01']['text']='proposal-d'
            cv=store.import_plan(c,bv['version'],'roadmap-validator-c')
            try:
                store.import_plan(d,bv['version'],'roadmap-validator-d',merge=True)
            except ContractError as e:
                check('conflicting_acceptance_rejected',e.code=='merge_conflict')
            else:raise AssertionError('conflict accepted')
            check('conflict_did_not_install_partial_plan',store.head(plan['project_id'])==cv['version'])
            try:store.import_plan(d,None,'roadmap-validator-first')
            except ContractError as e:check('same_request_id_different_body_rejected',e.code=='idempotency_conflict')
            else:raise AssertionError('id conflict accepted')
            seed=json.loads((ROOT/'INITIAL_SOURCE_EVIDENCE.json').read_text())['events']
            reply=store.ingest(seed,project=plan['project_id'])
            repeated=store.ingest(seed,project=plan['project_id'])
            check('source_evidence_exact_retry_no_duplicates',all(not x['created'] for x in repeated['receipts']))
            state=store.state(plan['project_id'])
            check('no_fictional_live_agents_or_green_future_tests',not state['agents'] and not state['checks'])
            sample=load(ROOT/'templates/PROJECT.plan.json')
            jsonschema.Draft202012Validator(schema).validate(sample)
            sv=store.import_plan(sample,None,'roadmap-template-first')
            check('second_project_same_schema_without_conversion',store.plan(sample['project_id'])['plan']==sample)
        finally:store.close()
    # Actual route via in-process HTTP client; not a target browser or live service proof.
    import importlib.metadata
    from fastapi.testclient import TestClient
    from waypoint.server import create_app
    with tempfile.TemporaryDirectory(prefix='waypoint-roadmap-api-') as tmp:
        tokens={'read':'fixture-roadmap-read-capability','write':'fixture-roadmap-write-capability'}
        app=create_app(Path(tmp),tokens=tokens,testing=True)
        with TestClient(app) as client:
            w={'Authorization':'Bearer '+tokens['write']};r={'Authorization':'Bearer '+tokens['read']}
            response=client.post('/api/p/waypoint/plans',headers=w,json={'request_id':'roadmap-api-first','base_version':None,'plan':plan})
            check('native_plan_http_route_accepts',response.status_code==200)
            response=client.get('/api/p/waypoint/packet/WPT-C05',headers=r)
            data=response.json()
            check('native_packet_http_exposes_complete_assignment',response.status_code==200 and data['assignment']==plan['nodes']['WPT-C05']['assignment'])
            check('native_packet_http_has_criteria_tests_sources_children',data['acceptance']==plan['nodes']['WPT-C05']['acceptance'] and data['tests']==plan['nodes']['WPT-C05']['tests'] and set(data['children'])==set(children(plan,'WPT-C05')) and data['source_refs']==plan['nodes']['WPT-C05']['source_refs'])
            readback=client.get('/api/p/waypoint/plan',headers=r).json()
            check('native_http_export_preserves_extension',readback['plan']==plan)
    render(plan,check=True)
    check('generated_views_match_single_source',True)
    return {'status':'PASS','scope':'roadmap authoring + native Waypoint schema/Store + in-process HTTP contract; no live Codex, deployment or target browser',
            'plan_content_sha256':fingerprint(plan),'node_count':len(plan['nodes']),'edge_count':len(plan['edges']),
            'checks':checks,'check_count':len(checks),
            'environment':{'python':platform.python_version(),'sqlite':__import__('sqlite3').sqlite_version,'fastapi':importlib.metadata.version('fastapi'),'httpx':importlib.metadata.version('httpx'),'jsonschema':importlib.metadata.version('jsonschema')},
            'not_run':['owner-machine integration','live Codex observation','canonical skill publication/installation','Runner application','shared registry/inbox mutation']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path)
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('render');q.add_argument('--check',action='store_true')
    q=sub.add_parser('validate');q.add_argument('--report',type=Path)
    q=sub.add_parser('frontier');q.add_argument('--completed',nargs='*',default=[]);q.add_argument('--stages',action='store_true')
    q=sub.add_parser('packet');q.add_argument('node')
    a=p.parse_args()
    try:
        plan=load(a.plan)
        if a.command=='render': result=render(plan,a.check)
        elif a.command=='validate':
            result=validate(plan)
            if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(encoded(result),encoding='utf8')
        elif a.command=='frontier':result=frontier(plan,a.completed,a.stages)
        else:print(packet_text(plan,a.node));return 0
        print(encoded(result));return 0
    except (ValueError,KeyError,AssertionError,OSError,ImportError) as e:
        print(encoded({'status':'FAIL','error':str(e)}),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
