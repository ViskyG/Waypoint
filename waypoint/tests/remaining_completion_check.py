"""Inspect real registered criteria before submitting prepared N08 completion."""
import json
import os
import sqlite3
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'waypoint'))
from waypoint.client import Client
from waypoint.domain import now
from playwright.sync_api import sync_playwright

def main():
    output=ROOT/'next-stage/evidence/remaining-20261020/COMPLETION_UI.json'
    assert not output.exists()
    binding=json.loads((ROOT/'.runtime/root-binding.json').read_text())
    assert os.environ['CODEX_THREAD_ID']==binding['native_id']
    client=Client(ROOT/'.runtime/data',timeout=8);base='/api/p/waypoint';checks=[]
    state=client.call('GET',base+'/state')
    packets=['WPT-N04-FIX','WPT-N05-FIX','WPT-N07-FIX','WPT-N08-FIX']
    for node in packets:
        expected=set(state['plan']['nodes'][node]['tests'])
        passed={x['test_id'] for x in state['checks'] if x['node_id']==node and x['outcome']=='passed'}
        assert expected<=passed
    bundle=json.loads((ROOT/'.runtime/remaining-20261020/completion-events.json').read_text())
    if state['node_views']['WPT-N08-FIX']['status']['status']=='done':
        # Recover the exact accepted IDs after a verifier UI-navigation timeout;
        # no changed completion payload and no fresh duplicate completion event.
        with sqlite3.connect((ROOT/'.runtime/data/waypoint.db').resolve().as_uri()+'?mode=ro',uri=True) as db:
            completion_seq=min(db.execute('SELECT seq FROM events WHERE event_id=?',(e['event_id'],)).fetchone()[0] for e in bundle['events'])
            assert all(x['seq']<completion_seq for x in state['checks'] if x['node_id']=='WPT-N08-FIX')
    checks.append('All13 remaining criterion IDs and concrete results registered before N08 done')
    errors=[]
    with sync_playwright() as pw:
        choices=[Path('/usr/bin/chromium'),Path(pw.chromium.executable_path),*Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome')]
        browser=pw.chromium.launch(executable_path=str(next(p for p in choices if p.exists())),headless=True,args=['--no-sandbox'])
        try:
            page=browser.new_page(viewport={'width':1660,'height':1050});page.on('pageerror',lambda e:errors.append(type(e).__name__))
            page.add_init_script('sessionStorage.setItem("waypoint-read-key",'+json.dumps(client.tokens['read'])+')')
            page.goto(client.url+'/#project=waypoint');page.locator('.node').first.wait_for()
            page.locator('[data-view="plan"]').click()
            for node in packets:
                row=page.locator('.plan-row[data-node="'+node+'"]');row.wait_for()
                total=len(state['plan']['nodes'][node]['tests'])
                assert 'Подтверждено проверок: '+str(total)+'/'+str(total) in row.inner_text()
                assert 'next-stage/evidence/remaining-20261020/' in row.inner_text()
            checks.append('Plan displays complete per-ID counts and immutable result references for all four repairs')
            for node in packets[:3]:
                row=page.locator('.plan-row[data-node="'+node+'"]')
                assert row.get_attribute('data-status')=='done' and '✓ Готово' in row.locator('.plan-status').inner_text()
                color=row.locator('.plan-status').evaluate('(n)=>getComputedStyle(n).color')
                assert color==row.evaluate('(n)=>{const x=document.createElement("i");x.style.color="var(--pass)";n.append(x);const c=getComputedStyle(x).color;x.remove();return c}')
            checks.append('Completed N04/N05/N07 repairs have actual green done styling')
            page.locator('.plan-row[data-node="WPT-N07-FIX"] .plan-node-link').click()
            page.locator('#tabs').get_by_text('Тесты',exact=True).click()
            panel=page.locator('#inspector-body')
            page.wait_for_function('()=>document.querySelector("#inspector-body")?.textContent.includes("remaining-20261020-N07-current-review")')
            text=panel.inner_text()
            assert 'Запуск и регистрация' in text and 'Версия карты при регистрации:' in text and 'ручная декларация' in text
            assert 'N07_CURRENT_RESULT.json' in text
            checks.append('Actual N07 run/registration/basis visible in Tests separately from historic execution')
            page.locator('#close').click()
            page.locator('[data-view="plan"]').click()
            assert len(bundle['events'])==2 and all(e['kind']=='node.status' and e['payload']['status']=='done' and e['node_ids'][0] in {'WPT-N08','WPT-N08-FIX'} for e in bundle['events'])
            receipts=client.call('POST',base+'/events',bundle)
            for node in ['WPT-N08','WPT-N08-FIX']:
                page.wait_for_function('(id)=>document.querySelector(".plan-row[data-node="+id+"]")?.dataset.status==="done"',arg=node,timeout=15000)
            check_state=client.call('GET',base+'/state')
            for node in ['WPT-N02-FIX','WPT-N03-FIX',*packets,*['WPT-N'+str(i).zfill(2) for i in range(9)]]:
                assert check_state['node_views'][node]['status']['status']=='done'
            assert check_state['node_views']['WPT-N09']['status']['status']!='done'
            checks.append('N00–N08 and all six fixes done; N09 remains open')
            row=page.locator('.plan-row[data-node="WPT-N08-FIX"]');row.scroll_into_view_if_needed();page.screenshot(path=str(output.with_suffix('.png')))
            assert not errors
            result={'status':'PASS','captured_at':now(),'evidence_level':'actual_installed_HTTP_Store_Chromium','checks':checks,'browser':browser.version,'errors':errors,'plan_version':state['version'],'done_receipts':receipts,'criteria_registered_before_done':True,'native_text_exported':False,'N09_closed':False}
        finally:browser.close()
    with output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'status':'FAIL','error_type':type(e).__name__,'diagnostic':str(e).split('Call log:')[0][:400],'private_url_suppressed':True}));sys.exit(1)
