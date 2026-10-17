"""Read-only product audit; synthetic disposable HTTP DB, no production contact."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'waypoint'), str(ROOT / 'waypoint/tests')]
from stage2_http_browser_check import plan, TOKENS
from waypoint.domain import now


def run():
    from playwright.sync_api import sync_playwright
    base = 'http://127.0.0.1:18783'
    def api(path, body=None):
        token = TOKENS['write' if body is not None else 'read']
        req = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with urlopen(req, timeout=10) as reply:
            return json.load(reply)
    def emit(kind, payload, node_ids=None, at=None):
        return api('/api/p/contract-audit/events', {'events': [{
            'event_id': uuid.uuid4().hex, 'project_id': 'contract-audit', 'source': 'audit',
            'kind': kind, 'agent_id': 'actor', 'at': at or now(),
            'node_ids': node_ids or [], 'payload': payload}]})
    results = {'fixture': 'SYNTHETIC disposable project, no native Codex contact',
               'production_data_modified': False, 'checks': {}}
    with tempfile.TemporaryDirectory(prefix='waypoint-contract-audit-') as temp:
        log = open(Path(temp) / 'service.log', 'w')
        service = subprocess.Popen([sys.executable, str(ROOT / 'waypoint/tests/stage2_http_browser_check.py'),
                                    '--serve', temp, '--port', '18783'], stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    api('/api/health'); break
                except Exception:
                    time.sleep(.05)
            p = plan('contract-audit')
            p['x_observability']['workspace_ref'] = 'plan-default'
            p['edges']['ORDER'] = {'from': 'OTHER', 'to': 'ROOT', 'x_observability': {
                'relation': 'order', 'phase': 'start', 'target_scope': 'subtree', 'why': 'Ordering context only'}}
            api('/api/p/contract-audit/plans', {'plan': p, 'request_id': 'audit-initial'})
            emit('source.health', {'source_key': 'audit', 'state': 'connected'}, at='2020-01-01T00:00:00Z')
            summary = api('/api/projects?summary=true')[0]
            results['checks']['stale_health'] = {'expected': 'stale/unknown source, no fresh connection claim',
                'actual': summary['source_health']}
            prereq = api('/api/p/contract-audit/prerequisites?node=ROOT&workspace=override-base')
            results['checks']['workspace_basis'] = {'request_workspace': 'override-base', 'actual_basis': prereq['basis']}
            state = api('/api/p/contract-audit/state')
            results['checks']['order_projection'] = {'actual': state['node_views']['ROOT']['prerequisites'],
                'raw_edge_present': 'ORDER' in state['plan']['edges']}
            for i in range(40):
                emit('item.upsert', {'item_id': 'msg-' + str(i), 'type': 'agentMessage',
                     'text': 'Message %d. ' % i + 'Synthetic long content. ' * 24}, ['ROOT'])
            with sync_playwright() as pw:
                paths = [Path('/usr/bin/chromium'), Path(pw.chromium.executable_path),
                         *Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome')]
                browser = pw.chromium.launch(executable_path=str(next(p for p in paths if p.exists())),
                                            headless=True, args=['--no-sandbox'])
                try:
                    page = browser.new_page(viewport={'width': 1500, 'height': 1000})
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.goto(base + '/#key=' + TOKENS['read'])
                    page.locator('.project-card button').click()
                    page.locator('.node[data-node="ROOT"] .assignment').click()
                    page.locator('#tabs').get_by_text('Сообщения', exact=True).click()
                    page.locator('#inspector-body .message').first.wait_for()
                    page.locator('.reader-filter summary').click()
                    page.locator('.type-filter').get_by_text('Ничего', exact=True).click()
                    page.locator('[data-category="message"]').check()
                    page.locator('#inspector-body .message[data-item="msg-5"]').wait_for()
                    body = page.locator('#inspector-body')
                    body.evaluate('(x)=>{x.scrollTop=300;x.dispatchEvent(new Event("scroll"))}')
                    before = page.locator('#inspector-body .message').count()
                    receipt = emit('item.upsert', {'item_id': 'msg-5', 'type': 'commandExecution',
                                   'text': 'Corrected category: command, should leave message filter'}, ['ROOT'])
                    seq = receipt['receipts'][0]['seq']
                    page.wait_for_function('(seq)=>waypointView().basis.cursor>=seq', arg=seq, timeout=8000)
                    page.wait_for_timeout(500)
                    filtered = api('/api/p/contract-audit/items?node=ROOT&categories=message&limit=100')
                    results['checks']['corrected_from_filter'] = {
                        'expected': 'msg-5 removed from message reader after machine type correction',
                        'server_contains_corrected_item': any(x['id'] == 'msg-5' for x in filtered['items']),
                        'browser_contains_corrected_item': page.locator('#inspector-body .message[data-item="msg-5"]').count() > 0,
                        'reader_before_count': before,
                        'reader_after_count': page.locator('#inspector-body .message').count(),
                        'scroll_top': body.evaluate('(x)=>x.scrollTop'), 'event_seq': seq}
                    page.locator('#close').click()
                    page.locator('#project-views button[data-view="plan"]').click()
                    text = page.locator('.plan-row[data-node="ROOT"]').inner_text()
                    results['checks']['order_plan_view'] = {'order_reason_visible': 'Ordering context only' in text,
                                                           'root_row': text}
                    results['browser'] = browser.version
                    results['browser_errors'] = errors
                finally:
                    browser.close()
        finally:
            service.terminate()
            try:
                service.wait(timeout=5)
            except subprocess.TimeoutExpired:
                service.kill(); service.wait()
            log.close()
    path = Path(__file__).with_name('CONTRACT_REPRODUCTION.json')
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    run()
