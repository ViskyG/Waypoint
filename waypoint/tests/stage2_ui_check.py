"""Targeted Chromium UI seam checks with declared SYNTHETIC API fixtures.

Exercises authored assets, never claims live Codex/service verification. N08 owns
composed real service evidence. No ingestion or user DB is changed by this file.
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT/'waypoint/web'

def state(project, status='waiting'):
    nodes = {
        'ROOT': {'title':project+' parent','assignment':'Executor shell command details','parent':None,'layout':{'x':0,'y':0},'tests':{},'x_observability':{'intent':{'summary':'Keep project '+project+' understandable','context':'Owner needs context','change':'Show readable intent'}}},
        'LEAF': {'title':project+' child','assignment':'Technical child task','parent':'ROOT','layout':{'x':0,'y':0},'tests':{}}
    }
    return {'version':project+'v1','current_version':project+'v1','cursor':1,'basis':{'plan_version':project+'v1','cursor':1,'projection_version':'observability/1'},'plan':{'title':project+' purpose','nodes':nodes,'edges':{}},'node_views':{'ROOT':{'status':{'status':status},'activity':{'distinct_active_agents':2,'distinct_active_leaves':1},'prerequisites':{'start':[],'finish':[]}}},'node_states':[{'id':'ROOT','status':status}],'agents':[],'scopes':[],'sources':[],'items':[],'checks':[],'ghosts':{},'warnings':[]}

async def run():
    checks=[]; errors=[]; held=[]; delayed=[]; hold_target=None; request_seen=asyncio.Event()
    async with async_playwright() as pw:
        candidates=[Path('/usr/bin/chromium'),Path(pw.chromium.executable_path),*sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'),reverse=True)]
        browser=await pw.chromium.launch(executable_path=str(next(p for p in candidates if p.exists())),headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':1660,'height':1050})
        page.on('pageerror',lambda error: errors.append(str(error)))
        async def route_handler(route):
            url=route.request.url
            path=url.split('http://waypoint.test',1)[-1]
            if hold_target and ((hold_target == 'catalogue' and path.startswith('/api/projects')) or ('/api/p/A/' in path and hold_target in path)):
                delayed.append(route);request_seen.set();return
            if path.startswith('/static/'):
                file=WEB/path.split('?',1)[0].split('/')[-1]
                await route.fulfill(body=file.read_bytes(),content_type='text/css' if file.suffix=='.css' else 'text/javascript');return
            if path.startswith('/api/projects'):
                await route.fulfill(json=[{'project_id':p,'title':p,'purpose':'Purpose '+p,'distinct_active_agents':2,'distinct_active_blocks':1,'source_health':'connected'} for p in ['A','B']]);return
            if '/events?' in path:
                held.append(route);return
            if '/state' in path:
                project=path.split('/')[3]
                await route.fulfill(json=state(project));return
            if '/versions' in path:
                project=path.split('/')[3];await route.fulfill(json=[{'version':project+'v1','ordinal':1}]);return
            if '/items?' in path:
                await route.fulfill(json={'items':[],'has_more':False,'before':None});return
            if '/algorithms?' in path:
                await route.fulfill(json={'basis':{'plan_version':path.split('/')[3]+'v1'},'algorithms':[]});return
            await route.fulfill(body=(WEB/'index.html').read_bytes(),content_type='text/html')
        await page.route('http://waypoint.test/**',route_handler)
        await page.goto('http://waypoint.test/#key=synthetic-key')
        await page.locator('.project-card').first.wait_for()
        assert await page.locator('.project-card').count()==2; assert await page.locator('#viewport').is_hidden();checks.append('Default home is metadata project catalogue')
        assert await page.locator('#theme option').count()==3
        assert await page.locator('#theme option').last.is_disabled();checks.append('Three selection slots; only two real ready themes')
        await page.select_option('#theme','obsidian');await page.reload();await page.locator('.project-card').first.wait_for()
        assert await page.evaluate('document.documentElement.dataset.theme')=='obsidian';checks.append('Registry selection survives reload')
        await page.locator('.project-card[data-project="A"] button').click();await page.locator('.node[data-node="ROOT"]').wait_for()
        await page.locator('#project-views button[data-view="plan"]').click();await page.locator('.plan-row').first.wait_for()
        text=await page.locator('#plan-view').inner_text();assert 'Keep project A understandable' in text and 'Сообщено: waiting' in text and '2 активных агентов' in text;checks.append('Plan consumes intent and independent parent/descendant projection')
        await page.locator('.plan-row[data-node="ROOT"] .intent-details summary').click()
        await page.locator('.plan-row[data-node="ROOT"] .plan-node-link').click();await page.locator('#inspector-body .task-subtabs').wait_for()
        text=await page.locator('#inspector-body').inner_text();assert 'Keep project A understandable' in text and 'Executor shell command details' not in text
        await page.locator('.task-subtabs').get_by_text('Для исполнителя',exact=True).click();assert 'Executor shell command details' in await page.locator('#inspector-body').inner_text();checks.append('Human Task first; executor instructions in separate subtab')
        await page.locator('#close').click();await page.locator('#project-views button[data-view="plan"]').click();assert await page.locator('.plan-row[data-node="ROOT"] .intent-details').evaluate('(x)=>x.open');checks.append('Map roundtrip restores expanded Plan context')
        await page.select_option('#project','B');await page.wait_for_function("waypointView().project==='B' && waypointView().basis?.plan_version==='Bv1'")
        for route in held[:]:
            try: await route.fulfill(json={'events':[{'kind':'plan.changed'}],'cursor':999} if '/events?' in route.request.url else state('A'))
            except Exception: pass
        await page.wait_for_timeout(100)
        assert await page.evaluate('waypointView().project')=='B' and await page.evaluate('waypointView().basis.plan_version')=='Bv1';checks.append('Late prior-project events cannot replace selected project')
        # Each async surface must reject a response from a prior navigation.
        for target in ['state','versions','items','algorithms','catalogue']:
            hold_target = target;request_seen.clear();delayed.clear()
            if target=='catalogue':
                await page.locator('#home').click()
            else:
                await page.select_option('#project','A')
                if target in ['items','algorithms']:
                    await page.wait_for_function("waypointView().project==='A' && waypointView().basis?.plan_version==='Av1'")
                    if target=='algorithms': await page.locator('#project-views button[data-view="algorithms"]').click()
                    else: await page.locator('#project-views button[data-view="map"]').click()
            await asyncio.wait_for(request_seen.wait(),5)
            hold_target=None
            await page.select_option('#project','B')
            await page.wait_for_function("waypointView().project==='B' && waypointView().basis?.plan_version==='Bv1'")
            for pending in delayed:
                payload = state('A') if target=='state' else [{'version':'Av1','ordinal':1}] if target=='versions' else {'items':[],'has_more':False} if target=='items' else {'algorithms':[],'basis':{'plan_version':'Av1'}} if target=='algorithms' else [{'project_id':'A','title':'STALE ONLY'}]
                try: await pending.fulfill(json=payload)
                except Exception: pass
            await page.wait_for_timeout(50)
            assert await page.evaluate('waypointView().project')=='B' and await page.evaluate('waypointView().basis.plan_version')=='Bv1'
            if target=='catalogue': assert await page.locator('#project option[value="B"]').count()==1
        checks.append('Late state, versions, items, algorithms and catalogue replies cannot mutate next project')
        await page.locator('#project-views button[data-view="map"]').click();await page.locator('.node[data-node="ROOT"] .assignment').click();await page.locator('#tabs').get_by_text('Сообщения',exact=True).click();await page.locator('.reader-filter summary').click()
        await page.locator('.type-filter').get_by_text('Ничего',exact=True).click();assert await page.locator('.type-filter input[data-category]:checked').count()==0;checks.append('Reader filter distinguishes empty category selection from all')
        await page.select_option('#theme','terracotta');await page.screenshot(path=str(ROOT/'evidence/stage2-terracotta-synthetic.png'))
        await page.select_option('#theme','obsidian');await page.screenshot(path=str(ROOT/'evidence/stage2-obsidian-synthetic.png'))
        assert not errors,errors;checks.append('No browser application exceptions across both themes')
        await browser.close()
    result={'status':'PASS','fixture':'SYNTHETIC API; authored assets in real Chromium','live_codex_tested':False,'real_service_tested':False,'checks':checks,'limitations':['Target N08 browser/service/store evidence is separate.','Browser automation covers late state, versions, items, events, algorithms and catalogue replies; production connection is verified separately.']}
    out=ROOT/'evidence/stage2-ui-synthetic.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':asyncio.run(run())
