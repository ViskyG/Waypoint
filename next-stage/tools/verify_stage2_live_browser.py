#!/usr/bin/env python3
"""Actual installed browser/HTTP/current Codex checks; no transcript export."""
import argparse
import json
import os
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'waypoint'))
from waypoint.client import Client
from waypoint.domain import now
from playwright.sync_api import sync_playwright

def run(data,output):
    client=Client(data,timeout=8);base='/api/p/waypoint';actor='codex/'+os.environ['CODEX_THREAD_ID']
    state=client.call('GET',base+'/state');checks=[];errors=[]
    def check(name,condition=True):
        if not condition:raise AssertionError(name)
        checks.append(name)
        print(json.dumps({'verified':name}),flush=True)
    check('All actual N08 start requirements have concrete matching receipts',all(r['availability']=='satisfied' for r in state['node_views']['WPT-N08']['prerequisites']['start'] if r['classification']=='requires'))
    with sync_playwright() as p:
        choices=[Path('/usr/bin/chromium'),Path(p.chromium.executable_path),*sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'),reverse=True)]
        browser=p.chromium.launch(executable_path=next((str(x) for x in choices if x.exists()),None),headless=True,args=['--no-sandbox'])
        try:
            page=browser.new_page(viewport={'width':1660,'height':1050});page.on('pageerror',lambda error:errors.append(type(error).__name__))
            page.goto(client.url+'/#project=waypoint&key='+client.tokens['read'],wait_until='domcontentloaded')
            page.locator('.agent-card').first.wait_for()
            check('Read key removed while project deep link retained','key=' not in page.url and 'project=waypoint' in page.url)
            ids=page.locator('.agent-card').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.actor)')
            check('Actual root and observed nested identities rendered',actor in ids and all(a['id'] in ids for a in state['agents']))
            check('Actual nested parent relationships retained',any(a.get('parent_id')==actor for a in state['agents']))
            page.locator('.agent-card[data-actor="'+actor+'"]').click()
            page.locator('#inspector-body .message-text').first.wait_for()
            items=client.call('GET',base+'/items?agent='+actor+'&limit=100')['items'];matches=0
            for item in reversed(items):
                if not item.get('source','').startswith('codex-ipc/') or not item.get('text') or item.get('truncated'):continue
                found=page.locator('#inspector-body .message').evaluate_all('(nodes,id)=>nodes.filter(n=>n.dataset.item===id).map(n=>n.querySelector(".message-text")?.textContent)',item['id'])
                if found and found[0]==item['text']:matches+=1
                if matches==3:break
            check('Original actual IPC message bodies reach browser exactly',matches>=1)
            # Check the actual reader, independently of the synthetic rich workload.
            page.locator('#inspector-body .reader-filter summary').click()
            page.locator('#inspector-body .type-filter').get_by_role('button',name='Ничего',exact=True).click()
            page.wait_for_function('()=>document.querySelectorAll("#inspector-body .message").length===0')
            check('None filters actual Codex reader to empty')
            page.locator('#inspector-body .type-filter').get_by_role('button',name='Все',exact=True).click()
            page.locator('#inspector-body .message').first.wait_for();check('All restores actual Codex reader')
            page.locator('#close').click()
            page.locator('[data-view="plan"]').click()
            row=page.locator('.plan-row[data-node="WPT-N08"]');row.wait_for()
            check('Current accepted 32-node plan rendered',page.locator('.plan-row').count()==len(state['plan']['nodes']))
            status='Проверка обновления в настоящем браузере · '+now()
            client.call('POST',base+'/events',{'events':[{'event_id':uuid.uuid4().hex,'project_id':'waypoint','source':'agent-signal','agent_id':actor,'kind':'node.status','at':now(),'node_ids':['WPT-N08'],'payload':{'status':status,'explanation':'Actual installed integration acceptance; one observer status event, no executor command.'}}]})
            page.wait_for_function('(status)=>document.querySelector(".plan-row[data-node=WPT-N08] .plan-status")?.textContent.includes(status)',arg=status,timeout=20000)
            check('One actual status event refreshes Plan')
            page.locator('[data-view="map"]').click();page.locator('#search').fill('WPT-N08');page.locator('#search').press('Enter')
            page.wait_for_function('(status)=>document.querySelector(".node[data-node=WPT-N08] .status-label")?.textContent.includes(status)',arg=status,timeout=10000)
            check('Same event refreshes Map without second write')
            page.get_by_role('button',name='Задание',exact=True).click()
            page.get_by_role('button',name='Для владельца',exact=True).wait_for()
            intent=state['plan']['nodes']['WPT-N08']['x_observability']['intent']['summary']
            check('Actual authored human intent displayed',intent in page.locator('#inspector-body').inner_text())
            page.get_by_role('button',name='Для исполнителя',exact=True).click()
            check('Original technical assignment remains available',state['plan']['nodes']['WPT-N08']['assignment'] in page.locator('#inspector-body').inner_text())
            page.locator('#close').click();page.locator('[data-view="algorithms"]').click();page.locator('#algorithms-view .algorithm-card').first.wait_for()
            check('Four real curated mechanisms displayed',page.locator('#algorithms-view .algorithm-card').count()==4)
            for theme in ('terracotta','obsidian'):
                page.select_option('#theme',theme);check('Actual theme '+theme,page.locator('html').get_attribute('data-theme')==theme)
            check('No browser application errors',not errors)
            report={'status':'PASS','fixture':False,'transport':'Actual Chromium → HTTP → installed schema3 Store → current real Codex observations','checks':checks,'check_count':len(checks),'browser':browser.version,'native_text_matches':matches,'actors_rendered':len(ids),'plan_version':state['version'],'source_control_commands':0,'private_text_exported':False,'limitations':['Bounded installed acceptance, not a guarantee of all future provider formats or end-to-end token latency.','Third theme remains awaiting a confirmed distinct reference.']}
            output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
        finally:browser.close()

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('data',type=Path);a.add_argument('output',type=Path);args=a.parse_args()
    try:run(args.data,args.output)
    except Exception as error:
        # Do not export exceptions that may contain the private navigation URL.
        print(json.dumps({'status':'FAIL','error_type':type(error).__name__,'diagnostic':str(error).split('Call log:')[0][:800],'reason':'Inspect locally; private URL and text suppressed'}));raise SystemExit(1)
