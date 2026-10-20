"""N10 bounded localization regression in actual Chromium over loopback HTTP.

Default mode uses a disposable Store and explicitly synthetic authored records.
Live mode is a separate read-only smoke, never evidence of a native Codex run.
Every execution requires a fresh output directory; failures remain immutable.
No request interception, HTML replacement, production writes or provider RPC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'waypoint'), str(ROOT / 'waypoint/tests')]
from stage2_http_browser_check import plan, TOKENS
from waypoint.domain import now

CASES = ('default', 'storage', 'labels', 'reader', 'plan', 'algorithm')
SOURCE_PATHS = tuple('waypoint/waypoint/web/' + name for name in (
    'index.html', 'i18n.js', 'app.js', 'style.css', 'themes.js', 'filters.js',
    'projects.js', 'plan.js', 'algorithm_panel.js')) + (
        'waypoint/tests/i18n_browser_check.py',)
AUTHORED = 'Сообщения · Messages · Все · All <img src=x onerror="window.i18nInjected=1">'
PROJECT_TITLE = 'Проекты · Projects · ' + AUTHORED
CUSTOM_STATUS = 'Готово вручную · custom status'
STAMP = '2026-10-20T12:34:00Z'


def source_hashes():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_PATHS}


def run(args):
    from playwright.sync_api import sync_playwright
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    cases = tuple(args.cases.split(',')) if not args.live else ('live',)
    result = {
        'started_at': now(), 'status': 'RUNNING', 'checks': [], 'cases_requested': cases,
        'scope': ('Read-only installed-service browser smoke; no synthetic/native provenance claim'
                  if args.live else 'SYNTHETIC authored records; actual Chromium → HTTP → disposable Store'),
        'live_codex_tested': False, 'production_data_modified': False,
        'api_routes_mocked': False, 'browser_errors': [], 'diagnostics': [],
        'source_hashes_at_start': source_hashes(),
        'limitations': ['Localization checks do not rerun algorithm correctness or prove a native Codex source.'],
    }
    current = 'setup'
    browser = page = service = None
    temporary = None
    base = f'http://127.0.0.1:{args.port}'
    tokens, project = TOKENS, 'i18n-synthetic'

    def check(label, condition=True, **details):
        nonlocal current
        current = label
        result['checks'].append({'name': label, 'passed': bool(condition), **details})
        if not condition:
            if page and not args.live:
                page.screenshot(path=str(output / 'failure.png'))
            raise AssertionError(label)

    def api(path, body=None):
        request = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                          headers={'Authorization': 'Bearer ' + tokens['write' if body is not None else 'read'],
                                   'Content-Type': 'application/json'})
        with urlopen(request, timeout=10) as response:
            return json.load(response)

    def event(kind, payload, nodes=None):
        return {'event_id': uuid.uuid4().hex, 'project_id': project, 'source': 'synthetic-i18n',
                'kind': kind, 'agent_id': 'localization-fixture', 'at': STAMP,
                'node_ids': nodes or [], 'edge_ids': [], 'payload': payload}

    def fixture():
        p = plan(project)
        p['title'] = PROJECT_TITLE
        p['nodes']['ROOT']['title'] = AUTHORED
        p['nodes']['ROOT']['assignment'] = AUTHORED
        p['nodes']['ROOT']['x_observability']['intent'] = {
            'summary': AUTHORED, 'context': AUTHORED, 'change': AUTHORED, 'scope': AUTHORED}
        p['nodes']['OTHER']['x_observability']['outputs'] = {
            'OUT': {'definition': 'Synthetic required input', 'revision': 1}}
        p['x_observability']['workspace_ref'] = 'synthetic-i18n-workspace'
        p['x_observability']['algorithms']['merge']['title'] = AUTHORED
        for index in range(24):
            p['nodes']['SCROLL-' + str(index)] = {
                'title': 'Synthetic scroll context ' + str(index), 'parent': 'ROOT',
                'assignment': AUTHORED, 'layout': {'x': 40 + index * 400, 'y': 800},
                'acceptance': {}, 'tests': {},
                'x_observability': {'intent': {'summary': AUTHORED, 'context': AUTHORED,
                                               'change': AUTHORED}}}
        p['edges']['NEEDS'] = {'from': 'OTHER', 'to': 'ROOT', 'x_observability': {
            'relation': 'requires', 'phase': 'start', 'target_scope': 'node', 'why': AUTHORED,
            'condition': {'output_id': 'OUT', 'revision': 1, 'workspace': 'consumer'}}}
        api('/api/p/' + project + '/plans', {'plan': p, 'request_id': 'synthetic-i18n-plan'})
        records = [event('agent.upsert', {'name': AUTHORED}),
                   event('node.status', {'status': CUSTOM_STATUS, 'explanation': AUTHORED}, ['ROOT']),
                   event('node.status', {'status': 'done', 'explanation': AUTHORED}, ['OTHER']),
                   event('scope.set', {}, ['ROOT']), event('scope.set', {}, ['ROOT'])]
        records += [event('item.upsert', {'item_id': 'msg-' + str(index), 'type': 'agentMessage',
                    'text': f'msg-{index}: {AUTHORED}\n' + ('Original copied text. ' * 14),
                    'state': 'completed'}, ['ROOT']) for index in range(320)]
        records.append(event('item.upsert', {'item_id': 'cmd', 'type': 'commandExecution',
                                             'text': AUTHORED, 'state': 'completed'}, ['ROOT']))
        api('/api/p/' + project + '/events', {'events': records})
        observations = [event('algorithm.observation', {
            'algorithm_id': 'merge', 'definition_revision': 1, 'implementation_ref': 'synthetic-r1',
            'observation_kind': 'correctness',
            'correctness': {'outcome': 'passed', 'evidence_refs': ['fixture:i18n-not-a-real-run']},
            'measurement': None, 'comparison': None, 'note': AUTHORED}, ['ROOT']) for _ in range(237)]
        api('/api/p/' + project + '/events', {'events': observations})

    def new_context(init=None):
        context = browser.new_context(locale='ru-RU', timezone_id='UTC',
                                      viewport={'width': 1660, 'height': 1050})
        context.add_init_script('''(() => {
            const original = Date.prototype.toLocaleTimeString;
            Date.prototype.toLocaleTimeString = function(locale, options) {
                (window.i18nDateLocales ||= []).push(locale);
                return original.call(this, locale, options);
            };
        })();''')
        if init:
            context.add_init_script(init)
        return context

    def open_page(context, enter_project=True):
        nonlocal page
        page = context.new_page()
        page.on('pageerror', lambda error: result['browser_errors'].append(str(error)))
        page.goto(base + '/#key=' + tokens['read'])
        page.locator('.project-card[data-project="' + project + '"]').wait_for()
        if enter_project:
            page.locator('.project-card[data-project="' + project + '"] button').click()
            page.locator('.node[data-node="ROOT"]').wait_for()

    def language(value):
        page.select_option('#language', value)
        page.wait_for_function('(value)=>document.documentElement.lang===value', arg=value)

    def diagnostics(label):
        data = page.evaluate('WaypointUI.translationDiagnostics()')
        result['diagnostics'].append({'case': label, **data})
        check(label + ': no missing UI translation keys', not data['missing'])
        check(label + ': no uncaught application errors', not result['browser_errors'])

    def assert_authored(label):
        check(label + ': authored project title stays exact', page.locator('.project-title').inner_text() == PROJECT_TITLE)
        check(label + ': authored task title stays exact', page.locator('.node[data-node="ROOT"] .title h3').inner_text() == AUTHORED)
        check(label + ': authored HTML remains text', page.evaluate('window.i18nInjected') is None and
              page.locator('.node[data-node="ROOT"] img').count() == 0)

    def open_messages():
        page.locator('.node[data-node="ROOT"] .assignment').click()
        page.locator('#tabs').get_by_role('button', name='Messages', exact=True).click()
        page.locator('#inspector-body .message[data-item="msg-319"]').wait_for()
        page.locator('.reader-filter summary').click()

    def count(selector, amount):
        page.wait_for_function('(v)=>document.querySelectorAll(v.selector).length===v.amount',
                               arg={'selector': selector, 'amount': amount})

    def reader_ids():
        return page.locator('#inspector-body .message').evaluate_all('(rows)=>rows.map(row=>row.dataset.item)')

    def query():
        return page.locator('#inspector-body .type-filter').evaluate('''field=>({
            categories:[...field.querySelectorAll('input[data-category]:checked')].map(x=>x.dataset.category),
            errors:field.querySelector('[data-filter-control="errors"]').checked})''')

    def anchor():
        return page.locator('#inspector-body').evaluate('''body=>{
            const top=body.getBoundingClientRect().top;
            const edge=Math.max(top,body.querySelector('.reader-controls').getBoundingClientRect().bottom);
            const row=[...body.querySelectorAll('.message')].find(x=>x.getBoundingClientRect().bottom>edge);
            return {item:row.dataset.item,offset:row.getBoundingClientRect().top-top};}''')

    def anchor_offset(saved):
        return page.locator('#inspector-body').evaluate('''(body,id)=>{
            const row=[...body.querySelectorAll('.message')].find(x=>x.dataset.item===id);
            return row ? row.getBoundingClientRect().top-body.getBoundingClientRect().top : null;}''', saved['item'])

    try:
        if args.live:
            from waypoint.client import Client
            client = Client(args.data)
            base, tokens, project = client.url, {'read': client.tokens['read']}, args.project
        else:
            temporary = tempfile.TemporaryDirectory(prefix='waypoint-i18n-browser-')
            log = Path(temporary.name) / 'service.log'
            with log.open('w') as stream:
                service = subprocess.Popen([sys.executable, str(ROOT / 'waypoint/tests/stage2_http_browser_check.py'),
                                            '--serve', temporary.name, '--port', str(args.port)],
                                           stdout=stream, stderr=stream, cwd=ROOT)
            for _ in range(100):
                try:
                    api('/api/health')
                    break
                except Exception:
                    if service.poll() is not None:
                        raise RuntimeError(log.read_text()[-2000:])
                    time.sleep(.05)
            else:
                raise RuntimeError('Disposable service did not start')
            fixture()
        with sync_playwright() as pw:
            choices = [Path('/usr/bin/chromium'), Path(pw.chromium.executable_path),
                       *sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'), reverse=True)]
            browser = pw.chromium.launch(executable_path=str(next(path for path in choices if path.exists())),
                                         headless=True, args=['--no-sandbox'])
            result['browser'] = browser.version
            if args.live:
                current = 'read-only installed-service smoke'
                context = new_context()
                page = context.new_page()
                page.on('pageerror', lambda error: result['browser_errors'].append(str(error)))
                page.goto(base + '/#project=' + project + '&key=' + tokens['read'])
                page.locator('#language').wait_for()
                page.locator('#nodes .node').first.wait_for()
                before = page.locator('.project-title').inner_text()
                check('Installed service defaults to English with Russian browser locale',
                      page.locator('html').get_attribute('lang') == 'en' and page.locator('#home').inner_text() == 'Projects')
                language('ru')
                check('Installed service switches to Russian without changing authored project title',
                      page.locator('#home').inner_text() == 'Проекты' and page.locator('.project-title').inner_text() == before)
                language('en')
                check('Installed service returns to English', page.locator('#home').inner_text() == 'Projects')
                diagnostics('live')
                context.close()
                page = None
            if 'default' in cases:
                current = 'English default and persisted language'
                context = new_context()
                open_page(context, False)
                check('English is default even when navigator locale is Russian',
                      page.evaluate('navigator.language') == 'ru-RU' and page.locator('html').get_attribute('lang') == 'en'
                      and page.locator('#home').inner_text() == 'Projects')
                check('Catalogue generated labels are English; authored title remains exact',
                      page.locator('.project-card h2').inner_text() == PROJECT_TITLE and
                      page.locator('.project-card .open-project').inner_text() == 'Open project')
                language('ru')
                check('Russian selector updates catalogue and accessible labels',
                      page.locator('#home').inner_text() == 'Проекты' and page.locator('#language').get_attribute('aria-label') == 'Язык интерфейса'
                      and page.locator('.project-card .open-project').inner_text() == 'Открыть проект')
                page.reload()
                page.locator('.project-card').wait_for()
                check('Russian language persists across reload', page.locator('#language').input_value() == 'ru'
                      and page.locator('html').get_attribute('lang') == 'ru')
                language('en')
                page.reload()
                page.locator('.project-card').wait_for()
                check('English language persists across reload', page.locator('html').get_attribute('lang') == 'en')
                diagnostics('default')
                page.screenshot(path=str(output / 'default.png'))
                context.close()
                page = None
            if 'storage' in cases:
                for variant, init in [
                    ('invalid', "localStorage.setItem('waypoint-language','invalid-language');"),
                    ('getter-denied', "Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Denied','SecurityError')}});"),
                    ('setter-denied', "const original=Storage.prototype.setItem;Storage.prototype.setItem=function(...args){if(this===window.localStorage)throw new DOMException('Denied','SecurityError');return original.apply(this,args)};"),
                ]:
                    current = 'storage ' + variant
                    context = new_context(init)
                    open_page(context, False)
                    check(variant + ': fallback English renders without storage access',
                          page.locator('html').get_attribute('lang') == 'en' and page.locator('#home').inner_text() == 'Projects')
                    language('ru')
                    check(variant + ': selector remains usable', page.locator('#home').inner_text() == 'Проекты')
                    if variant != 'invalid':
                        page.reload()
                        page.locator('.project-card').wait_for()
                        check(variant + ': denied persistence safely reloads English', page.locator('html').get_attribute('lang') == 'en')
                    diagnostics(variant)
                    context.close()
                    page = None
            if 'labels' in cases:
                current = 'labels and small viewport'
                context = new_context()
                open_page(context)
                assert_authored('English map')
                check('English map theme and project-view labels are localized',
                      page.locator('#theme option[value="terracotta"]').inner_text() == 'Terracotta' and
                      page.locator('#project-views button').all_text_contents() == ['Map', 'Plan', 'Algorithms'])
                page.locator('.node[data-node="ROOT"] .assignment').click()
                check('English inspector tabs and authored human task are distinct',
                      page.locator('#tabs button').all_text_contents() == ['Task', 'Acceptance', 'Messages', 'Tests', 'Status', 'Algorithms']
                      and AUTHORED in page.locator('#inspector-body').inner_text())
                language('ru')
                assert_authored('Russian map')
                check('Russian map theme tabs and accessibility labels are localized',
                      page.locator('#theme option[value="terracotta"]').inner_text() == 'Терракота'
                      and page.locator('#tabs button').all_text_contents() == ['Задание', 'Приёмка', 'Сообщения', 'Тесты', 'Статус', 'Алгоритмы']
                      and page.locator('#search').get_attribute('placeholder') == 'Найти блок…'
                      and page.locator('#language').get_attribute('aria-label') == 'Язык интерфейса')
                page.set_viewport_size({'width': 390, 'height': 844})
                box = page.locator('#language').bounding_box()
                check('Language selector is visible inside a small viewport', bool(box) and
                      0 <= box['x'] < 390 and box['x'] + box['width'] <= 391 and
                      0 <= box['y'] and box['y'] + box['height'] <= 844)
                language('en')
                check('Small-viewport selector switches the actual UI', page.locator('#home').inner_text() == 'Projects')
                diagnostics('labels')
                page.screenshot(path=str(output / 'small-viewport.png'))
                context.close()
                page = None
            if 'reader' in cases:
                current = 'old reader window preservation'
                context = new_context()
                open_page(context)
                page.select_option('#theme', 'obsidian')
                open_messages()
                page.locator('.type-filter [data-filter-control="none"]').click()
                count('#inspector-body .message', 0)
                page.locator('.type-filter input[data-category="message"]').click()
                count('#inspector-body .message', 100)
                page.locator('#inspector-body').evaluate('''body=>{
                    const row=body.querySelector('[data-item="msg-250"]');
                    const top=body.querySelector('.reader-controls').getBoundingClientRect().bottom;
                    body.scrollTop+=row.getBoundingClientRect().top-top-2;body.dispatchEvent(new Event('scroll'));}''')
                page.locator('#inspector-body [data-item="msg-250"] .message-text').evaluate('''node=>{
                    const range=document.createRange();range.setStart(node.firstChild,0);range.setEnd(node.firstChild,36);
                    const selection=getSelection();selection.removeAllRanges();selection.addRange(range);}''')
                selected = page.evaluate('getSelection().toString()')
                page.locator('#inspector-body .older-messages').click()
                count('#inspector-body .message', 200)
                saved, ids, saved_query = anchor(), reader_ids(), query()
                check('Reader setup uses an explicit filter and old200-row window',
                      saved_query == {'categories': ['message'], 'errors': False} and 'msg-120' in ids)
                original_text = page.locator('#inspector-body [data-item="msg-250"] .message-text').text_content()
                for lang in ['ru', 'en']:
                    language(lang)
                    page.locator('#inspector-body .reader-filter summary').filter(
                        has_text='Фильтр сообщений' if lang == 'ru' else 'Message filter').wait_for()
                    check(lang + ': language toggle preserves exact old window, filter and theme',
                          reader_ids() == ids and query() == saved_query and
                          page.locator('html').get_attribute('data-theme') == 'obsidian')
                    offset = anchor_offset(saved)
                    check(lang + ': language toggle preserves item/pixel anchor and selection',
                          offset is not None and abs(offset - saved['offset']) < 3 and
                          page.evaluate('getSelection().toString()') == selected,
                          anchor=saved, actual_offset=offset, selected_expected=selected,
                          selected_actual=page.evaluate('getSelection().toString()'))
                    check(lang + ': message bytes/HTML text remain authored',
                          page.locator('#inspector-body [data-item="msg-250"] .message-text').text_content() == original_text
                          and page.locator('#inspector-body .message-text img').count() == 0)
                calls = page.evaluate('window.i18nDateLocales')
                check('Message date rendering uses selected UI locale, independently of browser locale',
                      'en-US' in calls and 'ru-RU' in calls and all(value in ['en-US', 'ru-RU'] for value in calls))
                diagnostics('reader')
                page.screenshot(path=str(output / 'reader.png'))
                context.close()
                page = None
            if 'plan' in cases:
                current = 'plan details and scroll'
                context = new_context()
                open_page(context)
                page.locator('#project-views [data-view="plan"]').click()
                row = page.locator('.plan-row[data-node="ROOT"]')
                row.wait_for()
                for selector in ['.intent-details', '.prerequisites[data-disclosure="prerequisites-start"]', '.dependency-warning-raw']:
                    row.locator(selector + ' > summary').click()
                page.locator('#plan-view').evaluate('node=>{node.scrollTop=360;node.dispatchEvent(new Event("scroll"))}')
                before = page.locator('#plan-view').evaluate('node=>node.scrollTop')
                for lang in ['ru', 'en']:
                    language(lang)
                    check(lang + ': Plan preserves intent prerequisites and raw-history disclosure',
                          all(row.locator(selector).evaluate('node=>node.open') for selector in
                              ['.intent-details', '.prerequisites[data-disclosure="prerequisites-start"]', '.dependency-warning-raw']))
                    check(lang + ': Plan scroll and authored status/intent remain unchanged',
                          abs(page.locator('#plan-view').evaluate('node=>node.scrollTop') - before) < 3 and
                          CUSTOM_STATUS in row.locator('.plan-status').inner_text() and row.locator('.plan-intent').inner_text() == AUTHORED)
                    check(lang + ': canonical done is localized separately from custom status',
                          ('✓ Готово' if lang == 'ru' else '✓ Done') in
                          page.locator('.plan-row[data-node="OTHER"] .plan-status').inner_text())
                diagnostics('plan')
                page.screenshot(path=str(output / 'plan.png'))
                context.close()
                page = None
            if 'algorithm' in cases:
                current = 'algorithm current page preservation'
                context = new_context()
                open_page(context)
                page.locator('#project-views [data-view="algorithms"]').click()
                page.locator('#algorithms-view .algorithm-title').click()
                count('#inspector-body .algorithm-evidence', 100)
                first = page.locator('#inspector-body .algorithm-evidence').evaluate_all('(rows)=>rows.map(x=>x.dataset.evidence)')
                page.locator('#inspector-body .algorithm-older').click()
                page.wait_for_function('(first)=>document.querySelector("#inspector-body .algorithm-evidence")?.dataset.evidence!==first', arg=first[0])
                count('#inspector-body .algorithm-evidence', 100)
                ids = page.locator('#inspector-body .algorithm-evidence').evaluate_all('(rows)=>rows.map(x=>x.dataset.evidence)')
                details = page.locator('#inspector-body .algorithm-evidence').first
                details.locator('summary').click()
                for lang in ['ru', 'en']:
                    language(lang)
                    page.locator('#inspector-body .algorithm-newer').filter(
                        has_text='Более новые свидетельства' if lang == 'ru' else 'Newer evidence').wait_for()
                    check(lang + ': algorithm page2 IDs and open evidence remain exact',
                          page.locator('#inspector-body .algorithm-evidence').evaluate_all('(rows)=>rows.map(x=>x.dataset.evidence)') == ids
                          and details.evaluate('node=>node.open'))
                    check(lang + ': algorithm authored title and evidence remain text',
                          page.locator('#inspector-body .algorithm-title').inner_text() == AUTHORED and
                          AUTHORED in details.inner_text() and page.evaluate('window.i18nInjected') is None)
                diagnostics('algorithm')
                page.screenshot(path=str(output / 'algorithm.png'))
                context.close()
                page = None
            browser.close()
            browser = None
        check('Source stayed frozen during acceptance', source_hashes() == result['source_hashes_at_start'])
        result['status'] = 'PASS'
    except Exception:
        result['status'], result['failed_at'], result['failure'] = 'FAIL', current, traceback.format_exc()
        if args.live:
            for capability in tokens.values():
                result['failure'] = result['failure'].replace(capability, '[redacted capability]')
        if page and not args.live:
            try:
                page.screenshot(path=str(output / 'failure.png'))
            except Exception:
                pass
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if service and service.poll() is None:
            service.terminate()
            try:
                service.wait(timeout=5)
            except subprocess.TimeoutExpired:
                service.kill()
                service.wait()
        if temporary:
            temporary.cleanup()
        result['finished_at'], result['source_hashes_at_finish'] = now(), source_hashes()
        result['check_count'] = len(result['checks'])
        (output / 'RESULT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'checks': result['check_count'], 'output': str(output),
                      'failed_at': result.get('failed_at'), 'failure': result.get('failure')}, ensure_ascii=False))
    return int(result['status'] != 'PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18786)
    parser.add_argument('--cases', default=','.join(CASES))
    parser.add_argument('--live', action='store_true', help='Separate read-only installed-service smoke')
    parser.add_argument('--data', type=Path, default=ROOT / '.runtime/data')
    parser.add_argument('--project', default='waypoint')
    args = parser.parse_args()
    if not args.live and (not args.cases or any(value not in CASES for value in args.cases.split(','))):
        parser.error('Unknown or empty case selection')
    sys.exit(run(args))
