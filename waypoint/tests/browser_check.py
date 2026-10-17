"""Real Chromium input checks of the authored UI; fictional backend fixture.

Run against a separately started `wp serve --demo` in a disposable data dir.
No live Codex or user application is contacted by this test.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.request import Request,urlopen
from playwright.sync_api import sync_playwright


def run(url: str, data: Path, root: Path, offline_mode: bool = False):
    tokens=json.loads((data/'access.json').read_text());results=[];errors=[]
    def check(name, condition=True):
        if not condition:raise AssertionError(name)
        results.append(name)
    with sync_playwright() as p:
        executable = os.environ.get('WAYPOINT_BROWSER') or next((str(x) for x in [Path('/usr/bin/chromium'), Path(p.chromium.executable_path), *sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'), reverse=True)] if x.exists()), None)
        browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1660,'height':1050},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        if offline_mode:
            page.set_content((root/'preview.html').read_text(), wait_until='load')
        else:
            page.goto(url+'/#key='+tokens['read'],wait_until='domcontentloaded')
        page.wait_for_selector('.node[data-node="W-02"]')
        check('Agent strip has all nine distinct agents',page.locator('.agent-card').count()==9)
        check('Two levels of orchestrators are present',page.locator('.orch').count()==3)
        check('In-node message region is 235 CSS pixels',page.locator('.node[data-node="W-02"] .messages').evaluate('(e)=>getComputedStyle(e).height')=='235px')
        before=page.evaluate('waypointView().camera')
        page.get_by_role('button',name='Раскрыть W-02',exact=True).click()
        check('Nested graph opens',page.evaluate('waypointView().scope')=='W-02')
        page.get_by_role('button',name='Раскрыть W-02.2',exact=True).click()
        check('Second nested level opens',page.evaluate('waypointView().scope')=='W-02.2')
        page.get_by_role('button',name='На уровень выше',exact=True).click()
        check('Up restores immediate parent',page.evaluate('waypointView().scope')=='W-02')
        page.locator('#crumbs').get_by_role('button',name='Карта',exact=True).click()
        check('Clickable ancestor restores root camera',page.evaluate('waypointView().camera')==before)
        page.get_by_role('button',name='Раскрыть W-02',exact=True).click()
        parent_camera=page.evaluate('waypointView().camera')
        page.get_by_role('button',name='Раскрыть W-02.2',exact=True).click()
        page.go_back();page.wait_for_function("() => waypointView().scope==='W-02'")
        check('Browser back restores parent scope and camera',page.evaluate('waypointView().camera')==parent_camera)
        page.locator('#crumbs').get_by_role('button',name='Карта',exact=True).click()
        chat=page.locator('.node[data-node="W-02"] .messages');chat.evaluate('(e)=>e.scrollTop=0');chat.hover();z=page.evaluate('waypointView().camera.z');scroll=chat.evaluate('(e)=>e.scrollTop')
        page.mouse.wheel(0,270);page.wait_for_timeout(150)
        check('Native chat wheel scrolls',chat.evaluate('(e)=>e.scrollTop')>scroll)
        check('Chat wheel does not zoom graph',page.evaluate('waypointView().camera.z')==z)
        vp=page.locator('#viewport').bounding_box();x=vp['x']+25;y=vp['y']+40
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+90,y+35,steps=6);page.mouse.up()
        check('Real pointer pan changes camera',page.evaluate('waypointView().camera')!=before)
        page.mouse.move(x,y);page.mouse.wheel(0,-150);page.wait_for_timeout(100)
        check('Canvas wheel zooms',page.evaluate('waypointView().camera.z')>z)
        page.locator('#search').fill('W-01');page.locator('#search').press('Enter')
        page.locator('#tabs').get_by_role('button',name='Приёмка',exact=True).click()
        check('Acceptance displays actual result and difference',page.locator('#inspector-body').inner_text().find('недостижимой цели')>=0)
        page.locator('#close').click();page.locator('.agent-card').filter(has_text='Backend Lead').click()
        check('Actor selection highlights its work region',page.locator('.node.highlight').count()>=1)
        page.locator('#close').click();page.locator('#outside').click()
        check('Off-map work remains accessible','побочную проблему' in page.locator('#inspector-body').inner_text())
        page.locator('#close').click();page.locator('#diff').click();page.locator('.diff-row').first.wait_for()
        check('Structural version diff shows removed W-07','W-07' in page.locator('#inspector-body').inner_text())
        page.locator('#close').click()
        versions=page.locator('#version option').evaluate_all('(xs)=>xs.map(x=>x.value)')
        page.select_option('#version',versions[-1]);page.wait_for_timeout(300)
        check('Old plan is labelled without time-travel claim','активность показана текущая' in page.locator('#map-note').inner_text())
        page.select_option('#version',versions[0]);page.wait_for_timeout(300)
        if not offline_mode:
            # Native local HTTP -> durable event -> browser update, not a demo-only mutation.
            event={'event_id':'browser-'+uuid.uuid4().hex,'project_id':'demo','source':'browser-fixture','agent_id':'A3','kind':'node.status','at':'2026-10-16T23:00:00Z','node_ids':['W-02'],'payload':{'status':'Проверено браузером','explanation':'Synthetic local integration'}}
            req=Request(url+'/api/p/demo/events',data=json.dumps({'events':[event]}).encode(),method='POST',headers={'Authorization':'Bearer '+tokens['write'],'Content-Type':'application/json'})
            with urlopen(req) as reply:assert reply.status==200
            page.locator('#search').fill('W-02');page.locator('#search').press('Enter');page.locator('#close').click()
            page.wait_for_function("() => document.querySelector('[data-node=\"W-02\"] .status-label')?.textContent==='Проверено браузером'",timeout=6000)
            check('Committed service event reaches browser through long-poll')
        if not offline_mode:
            def emit(events):
                req=Request(url+'/api/p/demo/events',data=json.dumps({'events':events}).encode(),method='POST',headers={'Authorization':'Bearer '+tokens['write'],'Content-Type':'application/json'})
                with urlopen(req) as reply: assert reply.status==200
            def item(i,text=None):
                return {'event_id':'reader-'+uuid.uuid4().hex,'project_id':'demo','source':'browser-fixture','agent_id':'A3','kind':'item.upsert','at':'2026-10-17T09:00:00Z','node_ids':['W-02'],'edge_ids':[],'payload':{'item_id':'reader-'+str(i),'type':'agentMessage','text':text or f'Synthetic reader message {i}. '+('Long readable line for reader-window checks. '*8),'state':'completed'}}
            emit([item(i) for i in range(140)])
            page.locator('#search').fill('W-02');page.locator('#search').press('Enter')
            page.locator('#inspector-body [data-item="reader-139"]').wait_for()
            page.locator('.node[data-node="W-02"] [data-item="reader-139"]').wait_for()
            check('Inspector is bounded to a page',page.locator('#inspector-body .message').count()<=100)
            check('Card has a bounded reader window',page.locator('.node[data-node="W-02"] .message').count()<=24)
            page.evaluate("window.__keptCard=document.querySelector('[data-node=\"W-02\"]');window.__keptMessage=__keptCard.querySelector('[data-item=\"reader-116\"]');window.__otherCard=document.querySelector('[data-node=\"W-01\"]');")
            page.locator('.node[data-node="W-02"] .messages').evaluate('(e)=>e.scrollTop=30')
            page.locator('#inspector-body').evaluate('(e)=>e.scrollTop=80')
            page.wait_for_timeout(70)
            card_top=page.locator('.node[data-node="W-02"] .messages').evaluate('(e)=>e.scrollTop')
            inspector_top=page.locator('#inspector-body').evaluate('(e)=>e.scrollTop')
            selection=page.evaluate("""()=>{ const text=window.__keptMessage.querySelector('.message-text').firstChild; const range=document.createRange();range.setStart(text,0);range.setEnd(text,25);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);return selection.toString(); }""")
            emit([item(140),item(116,'Revised synthetic message 116. '+('Preserved original selection while copying. '*8))])
            page.locator('.node[data-node="W-02"] .new-messages:not([hidden])').wait_for()
            page.locator('#inspector-body .inspector-latest:not([hidden])').wait_for()
            selected_after=page.evaluate('getSelection().toString()')
            if selected_after!=selection: print('selection diagnostic',page.evaluate("({selected:getSelection().toString(),connected:window.__keptMessage.isConnected,cardKept:window.__keptCard===document.querySelector('[data-node=\"W-02\"]'),reader:{follow:window.__keptCard._reader.follow,top:window.__keptCard._reader.top,ids:window.__keptCard._reader.items.map(i=>i.id)},pending:!!window.__keptMessage._pendingItem})"))
            check('Append preserves selected text',selected_after==selection)
            check('Revision preserves selected message DOM',page.evaluate("window.__keptMessage===document.querySelector('[data-node=\"W-02\"] [data-item=\"reader-116\"]')"))
            check('Append preserves frozen card position',page.locator('.node[data-node="W-02"] .messages').evaluate('(e)=>e.scrollTop')==card_top)
            check('Append preserves frozen inspector position',page.locator('#inspector-body').evaluate('(e)=>e.scrollTop')==inspector_top)
            check('Card and unrelated card retain identity',page.evaluate("window.__keptCard===document.querySelector('[data-node=\"W-02\"]') && window.__otherCard===document.querySelector('[data-node=\"W-01\"]')"))
            page.evaluate('getSelection().removeAllRanges()')
            page.wait_for_function("() => window.__keptMessage.textContent.includes('Revised synthetic')")
            check('Deferred revision appears after selection clears')
            page.locator('.node[data-node="W-02"] .new-messages').click()
            page.locator('#inspector-body .inspector-latest').click()
            check('Explicit latest returns both readers to tail',page.locator('#inspector-body [data-item="reader-140"]').count()==1 and page.locator('.node[data-node="W-02"] [data-item="reader-140"]').count()==1)
            emit([item(141)])
            page.locator('#inspector-body [data-item="reader-141"]').wait_for()
            check('Open inspector follows live tail',page.locator('#inspector-body').evaluate('(e)=>e.scrollHeight-e.scrollTop-e.clientHeight<12'))
            page.locator('#inspector-body .scope-toggle').click()
            page.locator('#inspector-body [data-item="reader-141"]').wait_for()
            check('Direct-only filter excludes descendants',page.locator('#inspector-body .message-origin').evaluate_all("xs=>xs.every(x=>x.textContent==='W-02')"))
            page.locator('#inspector-body .older-messages').click()
            page.wait_for_function("() => document.querySelectorAll('#inspector-body .message').length>100")
            check('Earlier messages paginate with bounded DOM',100<page.locator('#inspector-body .message').count()<=200)
            page.locator('#close').click()
            page.locator('#search').fill('W-02');page.locator('#search').press('Enter')
            scope={'event_id':uuid.uuid4().hex,'project_id':'demo','source':'browser-fixture','agent_id':'A3','kind':'scope.set','at':'2026-10-17T10:00:00Z','node_ids':['W-02'],'edge_ids':[],'payload':{'source_boundary':{'source_key':'fixture-native','generation':1,'revision':100}}}
            native=item(142,'Synthetic native envelope after verified focus.');native['node_ids']=[];native['at']='2026-10-17T10:01:00Z';native['payload'].update(source_key='fixture-native',source_generation=1,source_revision=101,source_first_revision=101)
            emit([scope,native])
            page.locator('#inspector-body [data-item="reader-142"]').wait_for()
            page.locator('.node[data-node="W-02"] [data-item="reader-142"]').wait_for()
            check('Empty native envelope uses Store focus attribution in both readers')
            revised=item(142,'Synthetic revised native envelope.');revised['node_ids']=[];revised['at']='2026-10-17T10:02:00Z';revised['payload'].update(source_key='fixture-native',source_generation=1,source_revision=102,source_first_revision=101)
            emit([revised])
            page.wait_for_function("() => document.querySelector('#inspector-body [data-item=\"reader-142\"]')?.textContent.includes('Synthetic revised native')")
            page.wait_for_function("() => document.querySelector('[data-node=\"W-02\"] [data-item=\"reader-142\"]')?.textContent.includes('Synthetic revised native')")
            check('Empty native revision refreshes mounted card and inspector')
            page.locator('#close').click()
            page.locator('#outside').click()
            check('Unknown block remains in off-map drawer','побочную проблему' in page.locator('#inspector-body').inner_text())
            page.locator('#close').click()
            page.locator('#viewport').focus()
            camera=page.evaluate('waypointView().camera')
            page.keyboard.press('ArrowRight')
            check('Keyboard pans focused canvas',page.evaluate('waypointView().camera.x')!=camera['x'])
        # Show a useful overview with readable chat and no large right inspector.
        if offline_mode:
            page.set_content((root/'preview.html').read_text(),wait_until='load')
        else:
            page.reload(wait_until='domcontentloaded')
        page.wait_for_selector('.node[data-node="W-02"]')
        check('Read model refreshed without caught UI error', not page.locator('#foot-status').get_attribute('class'))
        page.locator('#crumbs').get_by_role('button',name='Карта',exact=True).click()
        page.locator('#reset-selection').click() if page.locator('#reset-selection').is_visible() else None
        page.evaluate("document.documentElement.dataset.theme='terracotta'")
        page.screenshot(path=str(root/'evidence/ui-terracotta.png'))
        page.locator('#theme').click()
        check('Dark theme switch',page.evaluate('document.documentElement.dataset.theme')=='obsidian')
        page.wait_for_timeout(180)
        check('Dark theme cards have dark surfaces',page.locator('.agent-card').first.evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(25, 28, 31)')
        page.screenshot(path=str(root/'evidence/ui-obsidian.png'))
        check('No JS exceptions',not errors)
        # Offline file is the same client, not a separate fake renderer.
        offline=browser.new_page(viewport={'width':1660,'height':1050})
        offline.on('pageerror',lambda e:errors.append(str(e)))
        offline.set_content((root/'preview.html').read_text(),wait_until='load')
        offline.wait_for_selector('.node')
        check('Offline HTML content renders without service',offline.locator('#connection').text_content()=='Демо')
        offline.get_by_role('button',name='Раскрыть W-02',exact=True).click()
        offline.screenshot(path=str(root/'evidence/ui-nested.png'))
        check('Offline breadcrumbs work',offline.locator('#crumbs button').count()==2)
        check('No JS exceptions in offline mode',not errors)
        report={'status':'PASS','scope':'C06.1/C06.2 browser integration', 'executable':str(executable),'checks':results,'check_count':len(results),'js_errors':errors,'browser':browser.version,'fixture':'SYNTHETIC','real_input_actions':True,'live_codex_tested':False,'mode':'offline-set-content' if offline_mode else 'local-http','browser_http_integration':'NOT_RUN_POLICY_BLOCKED' if offline_mode else 'PASS'}
        (root/'evidence/browser-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        browser.close()
        return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:18769');p.add_argument('--data',type=Path,required=True);p.add_argument('--offline',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.url,a.data,Path(__file__).resolve().parents[1],a.offline),ensure_ascii=False,indent=2))
