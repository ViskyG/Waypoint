"""Three targeted completion regressions through real HTTP/Chromium.

All events/projects are SYNTHETIC; this never contacts Codex or production DB.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TOKENS = {'read': 'synthetic-completion-read', 'write': 'synthetic-completion-write'}
PROJECT = 'completion-regressions'


def fixture():
    from test_observability import profile_fixture
    plan = profile_fixture()
    plan['project_id'] = PROJECT
    plan['title'] = 'SYNTHETIC completion regressions'
    plan['x_observability']['workspace_ref'] = 'synthetic-workspace'
    plan['nodes']['A']['layout'] = {'x': 40, 'y': 40}
    plan['nodes']['B']['layout'] = {'x': 450, 'y': 40}
    plan['nodes']['CHILD']['layout'] = {'x': 40, 'y': 40}
    return plan


def run(port, output):
    from playwright.sync_api import sync_playwright
    from waypoint.dependencies import effective_requirements
    from waypoint.domain import now
    base = f'http://127.0.0.1:{port}'
    checks = []; errors = []; current = 'setup'; started = now()
    def api(path, body=None, write=False):
        req = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                      headers={'Authorization': 'Bearer ' + TOKENS['write' if write else 'read'],
                               'Content-Type': 'application/json'})
        with urlopen(req, timeout=15) as response:
            return json.load(response)
    def event(kind, payload, nodes=('CHILD',)):
        return {'schema': 'waypoint.event/1', 'event_id': uuid.uuid4().hex, 'project_id': PROJECT,
                'source': 'demo', 'kind': kind, 'agent_id': 'synthetic-actor', 'at': now(),
                'node_ids': list(nodes), 'edge_ids': [], 'payload': payload}
    def emit(kind, payload, nodes=('CHILD',)):
        return api(f'/api/p/{PROJECT}/events', {'events': [event(kind, payload, nodes)]}, True)['receipts'][0]['seq']
    def check(name, condition=True):
        nonlocal current
        current = name
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    def failure():
        return {'status': 'FAIL', 'fixture': 'SYNTHETIC isolated HTTP project',
                'live_codex_tested': False, 'production_data_modified': False, 'checks': checks,
                'failed_at': current, 'error': traceback.format_exc(), 'browser_errors': errors}
    with tempfile.TemporaryDirectory(prefix='waypoint-completion-regressions-') as temp:
        log = Path(temp)/'service.log'
        with log.open('w') as handle:
            service = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve', temp,
                                        '--port', str(port)], cwd=ROOT, stdout=handle, stderr=handle)
            browser = None
            try:
                for _ in range(100):
                    try:
                        api('/api/health'); break
                    except Exception:
                        if service.poll() is not None:
                            raise RuntimeError(log.read_text())
                        time.sleep(.05)
                else:
                    raise RuntimeError('Disposable service failed to start')
                plan = fixture()
                version = api(f'/api/p/{PROJECT}/plans', {'plan': plan, 'request_id': 'synthetic-completion'}, True)['version']
                emit('scope.set', {})
                before = api(f'/api/p/{PROJECT}/packet/CHILD')
                historical_warning = before['dependency_warnings'][0]
                check('Inherited early scope accepted with original unresolved requirement',
                      historical_warning['requirements'][0]['state'] == 'unknown' and
                      historical_warning['requirements'][0]['declared_target_id'] == 'B')
                requirement = effective_requirements(plan, 'CHILD')[0]
                receipt_seq = emit('dependency.observation', {
                    'edge_id': 'NEEDS', 'consumer_id': 'CHILD',
                    'requirement_fingerprint': requirement['requirement_fingerprint'],
                    'workspace_ref': 'synthetic-workspace', 'availability': 'available',
                    'occurred_at': now(), 'basis': {'kind': 'artifact', 'ref': 'fixture:prepared-input',
                    'explanation': 'Explicit synthetic receipt after accepted early work'}})
                after = api(f'/api/p/{PROJECT}/packet/CHILD')
                check('Late matching receipt satisfies current input without rewriting historical warning',
                      after['prerequisites']['start'][0]['state'] == 'satisfied' and
                      after['dependency_warnings'][0] == historical_warning and
                      historical_warning['basis']['cursor'] < receipt_seq)
                emit('item.upsert', {'item_id': 'rare-old', 'type': 'agentMessage', 'text': 'SYNTHETIC rare old message'})
                commands = [event('item.upsert', {'item_id': f'command-{i}', 'type': 'commandExecution',
                            'state': 'completed', 'text': 'SYNTHETIC command output'}) for i in range(1200)]
                for start in range(0, len(commands), 400):
                    api(f'/api/p/{PROJECT}/events', {'events': commands[start:start+400]}, True)
                rare = api(f'/api/p/{PROJECT}/items?node=CHILD&deep=false&categories=message&limit=1')
                check('Rare message returned before limit behind 1200 newer commands in the same exact scope',
                      [item['id'] for item in rare['items']] == ['rare-old'])
                emit('item.upsert', {'item_id': 'unknown-native', 'type': 'futureProviderNativeType', 'text': 'SYNTHETIC unknown native item'})
                other = api(f'/api/p/{PROJECT}/items?node=CHILD&deep=false&categories=other&limit=1')
                check('All None and Other are distinct through current HTTP Store',
                      api(f'/api/p/{PROJECT}/items?node=CHILD&categories=none')['items'] == [] and
                      len(api(f'/api/p/{PROJECT}/items?node=CHILD&limit=2')['items']) == 2 and
                      [item['id'] for item in other['items']] == ['unknown-native'] and
                      other['items'][0]['native_type'] == 'futureProviderNativeType')
                long_messages = [event('item.upsert', {'item_id': f'long-{i}', 'type': 'agentMessage',
                                 'text': f'SYNTHETIC long message {i}. ' + 'Bounded original text. '*100}) for i in range(24)]
                api(f'/api/p/{PROJECT}/events', {'events': long_messages}, True)
                with sync_playwright() as pw:
                    choices = [Path('/usr/bin/chromium'), Path(pw.chromium.executable_path),
                               *sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'), reverse=True)]
                    browser = pw.chromium.launch(executable_path=str(next(p for p in choices if p.exists())),
                                                headless=True, args=['--no-sandbox'])
                    page = browser.new_page(viewport={'width': 1660, 'height': 1050})
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    item_reads = []
                    def capture_response(response):
                        if f'/api/p/{PROJECT}/items?' in response.url and 'categories=message' in response.url and 'node=CHILD' in response.url and response.status == 200:
                            try:
                                item_reads.append(response.json()['cursor'])
                            except Exception:
                                pass
                    page.on('response', capture_response)
                    page.goto(base + '/#project=' + PROJECT + '&key=' + TOKENS['read'])
                    page.locator('.node[data-node="B"]').wait_for()
                    page.locator('#project-views button[data-view="plan"]').click()
                    warning = page.locator('.plan-row[data-node="CHILD"] .dependency-history-warning')
                    warning.wait_for()
                    check('Plan displays retained early-work warning after input is now available',
                          'Работа началась до подтверждения входов' in warning.inner_text() and
                          'unknown' in warning.inner_text())
                    page.locator('.plan-row[data-node="CHILD"] .plan-node-link').click()
                    page.locator('#inspector-body .dependency-history-warning').wait_for()
                    check('Task displays same historical early-work warning after matching receipt',
                          'Работа началась до подтверждения входов' in page.locator('#inspector-body').inner_text())
                    page.locator('#tabs').get_by_text('Статус', exact=True).click()
                    page.locator('#inspector-body .dependency-history-warning').wait_for()
                    page.locator('#inspector-body .prerequisites').first.locator('summary').click()
                    check('Status displays historical warning separately from current satisfied input',
                          'Работа началась до подтверждения входов' in page.locator('#inspector-body').inner_text() and
                          'доступно' in page.locator('#inspector-body').inner_text())
                    page.locator('#tabs').get_by_text('Сообщения', exact=True).click()
                    page.locator('#inspector-body .message').first.wait_for()
                    page.locator('.reader-filter summary').click()
                    page.locator('.type-filter').get_by_text('Ничего', exact=True).click()
                    page.locator('.type-filter input[data-category="message"]').check()
                    page.wait_for_function('() => document.querySelectorAll("#inspector-body .message").length===25')
                    body = page.locator('#inspector-body')
                    body.evaluate('(x) => x.scrollTop=300')
                    page.wait_for_timeout(100)
                    selection = body.locator('.message-text').first
                    selection.evaluate('x => { const range=document.createRange(); range.selectNodeContents(x); const s=getSelection();s.removeAllRanges();s.addRange(range); }')
                    selected = page.evaluate('getSelection().toString()')
                    top = body.evaluate('(x) => x.scrollTop')
                    hidden_seq = emit('item.upsert', {'item_id': 'hidden-tail', 'type': 'commandExecution', 'state': 'completed', 'text': 'SYNTHETIC hidden command tail'})
                    page.wait_for_function('(seq) => waypointView().basis.cursor>=seq', arg=hidden_seq, timeout=10000)
                    deadline = time.monotonic()+8
                    while not any(cursor >= hidden_seq for cursor in item_reads):
                        if time.monotonic() > deadline:
                            raise AssertionError('Filtered HTTP reader did not consume hidden-event cursor')
                        page.wait_for_timeout(100)
                    check('Hidden-type event consumed by polling and filtered HTTP reader without visible new count',
                          body.locator('.new-messages').is_hidden() and
                          page.evaluate('getSelection().toString()') == selected and
                          abs(body.evaluate('(x) => x.scrollTop') - top) < 3)
                    visible_seq = emit('item.upsert', {'item_id': 'visible-tail', 'type': 'agentMessage', 'text': 'SYNTHETIC visible message positive control'})
                    page.wait_for_function('() => document.querySelector("#inspector-body .new-messages:not([hidden])")?.textContent.includes("Новые сообщения: 1")', timeout=10000)
                    check('Visible message positive control increments visible count exactly once without resetting selection or scroll',
                          page.evaluate('getSelection().toString()') == selected and
                          abs(body.evaluate('(x) => x.scrollTop') - top) < 3)
                    check('No browser application errors', not errors)
                    result = {'status': 'PASS', 'started_at': started, 'completed_at': now(),
                              'fixture': 'SYNTHETIC isolated project and observations',
                              'transport': 'Actual Chromium → localhost HTTP → current schema3 Store → event polling',
                              'live_codex_tested': False, 'production_data_modified': False,
                              'target_criteria': ['WPT-N02/T05', 'WPT-N04/T01', 'WPT-N04/T05'],
                              'checks': checks, 'check_count': len(checks), 'browser': browser.version,
                              'same_scope_newer_command_count': 1200, 'long_visible_messages': 24,
                              'hidden_event_cursor': hidden_seq, 'visible_positive_control_cursor': visible_seq,
                              'plan_version': version,
                              'limitations': ['Controlled early-work regression uses synthetic events; the old owner incident remains INCIDENT_NOT_RECONSTRUCTED.',
                                              'This run does not establish native Codex connectivity or reconstruct past message attribution.']}
                    browser.close(); browser = None
            except Exception:
                result = failure()
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass
            finally:
                service.terminate()
                try:
                    service.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    service.kill(); service.wait()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False))
    return result['status'] == 'PASS'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve')
    parser.add_argument('--port', type=int, default=18775)
    parser.add_argument('--output', type=Path, default=ROOT.parent/'next-stage/evidence/COMPLETION_REGRESSIONS.json')
    args = parser.parse_args()
    if args.serve:
        import uvicorn
        from waypoint.server import create_app
        uvicorn.run(create_app(Path(args.serve), tokens=TOKENS), host='127.0.0.1', port=args.port,
                    log_level='warning', timeout_graceful_shutdown=2)
    else:
        sys.exit(0 if run(args.port, args.output) else 1)
