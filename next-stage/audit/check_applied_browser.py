#!/usr/bin/env python3
"""Read-only Chromium check of audit status registration on installed Waypoint.

No event fixture, fake messages, browser route mocking or native Codex RPC.
Capability remains local; screenshots cover the Plan, never message bodies.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]

def main():
    data = ROOT / '.runtime/data'
    key = json.loads((data / 'access.json').read_text())['read']
    url = json.loads((data / 'connection.json').read_text())['url']
    changed = ['WPT-N02', 'WPT-N03', 'WPT-N04', 'WPT-N05', 'WPT-N07', 'WPT-N08']
    with sync_playwright() as pw:
        candidates = [Path('/usr/bin/chromium'), Path(pw.chromium.executable_path),
                      *Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome')]
        browser = pw.chromium.launch(executable_path=str(next(p for p in candidates if p.exists())),
                                    headless=True, args=['--no-sandbox'])
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            errors = []
            page.on('pageerror', lambda exc: errors.append(str(exc)))
            page.add_init_script('sessionStorage.setItem("waypoint-read-key",' + json.dumps(key) + ')')
            page.goto(url)
            page.locator('.project-card button').click()
            page.wait_for_function('() => Boolean(window.waypointView?.().basis)')
            page.locator('#project-views button[data-view="plan"]').click()
            page.wait_for_function('() => document.querySelectorAll(".plan-row").length===38')
            for node in changed:
                row = page.locator('.plan-row[data-node="' + node + '"]')
                assert row.get_attribute('data-status') == 'Требуются исправления', node
            for node in changed:
                assert page.locator('.plan-row[data-node="' + node + '-FIX"]').get_attribute('data-status') == 'not_started'
            assert '✓ Готово' in page.locator('.plan-row[data-node="WPT-N01"]').inner_text()
            for node in ['WPT-N09', 'WPT-INPUT-T3']:
                assert page.locator('.plan-row[data-node="' + node + '"]').get_attribute('data-status') == 'awaiting reference'
            page.locator('.plan-row[data-node="WPT-N04-FIX"]').scroll_into_view_if_needed()
            page.screenshot(path=str(ROOT / 'next-stage/audit/APPLIED_PLAN.png'))
            page.locator('.plan-row[data-node="WPT-N04-FIX"] .plan-node-link').click()
            page.locator('#tabs').get_by_text('Тесты', exact=True).click()
            page.get_by_text('failed', exact=False).first.wait_for()
            check_text = page.locator('#inspector-body').inner_text()
            assert 'T01' in check_text and 'failed' in check_text and 'CONTRACT-F01' in check_text
            basis = page.evaluate('() => waypointView().basis')
            result = {'status': 'PASS', 'browser': browser.version,
                'target': 'installed localhost Waypoint, actual production data, read-only',
                'head': basis['plan_version'], 'cursor': basis['cursor'],
                'checks': ['38 nodes visible', 'six parents require corrections',
                    'six FIX remain not_started', 'N01 done remains green-labelled',
                    'N09 and third-reference input remain awaiting', 'N04-FIX T01 failed evidence readable'],
                'browser_errors': errors, 'native_connection_retested': False,
                'source_mutations': False, 'event_writes': False, 'capability_exported': False,
                'limitations': 'Read-only verification of audit projection, not remediation acceptance or a new native Codex/restart campaign.'}
            assert not errors
        finally:
            browser.close()
    (ROOT / 'next-stage/audit/APPLIED_BROWSER.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
