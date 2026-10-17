#!/usr/bin/env python3
"""Actual local Waypoint + selected Codex projections in Chromium; no transcript export."""
import json
import os
from pathlib import Path
import sys
import uuid
from playwright.sync_api import sync_playwright
from waypoint.client import Client
from waypoint.domain import now


def run(data, output):
    client=Client(data); project='waypoint';base='/api/p/'+project
    actor='codex/'+os.environ['CODEX_THREAD_ID']
    state=client.call('GET',base+'/state')
    checks=[];errors=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    with sync_playwright() as p:
        choices=[Path('/usr/bin/chromium'),Path(p.chromium.executable_path),*sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'),reverse=True)]
        executable=next((str(x) for x in choices if x.exists()),None)
        browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
        try:
            page=browser.new_page(viewport={'width':1660,'height':1050})
            page.on('pageerror',lambda e:errors.append(type(e).__name__))
            page.goto(client.url+'/#key='+client.tokens['read'],wait_until='domcontentloaded')
            page.wait_for_selector('.agent-card')
            if page.locator('#project').input_value()!=project:page.select_option('#project',project)
            page.wait_for_function('(id)=>document.querySelectorAll(".agent-card").length>0',arg=actor)
            check('read capability removed from address', 'key=' not in page.url)
            check('actual selected family represented',page.locator('.agent-card').count()>=len(state['agents']))
            page.locator('.agent-card').filter(has=page.locator('.agent-code')).first.wait_for()
            page.locator('.agent-card[title^="'+actor+'"]').click()
            page.wait_for_selector('#inspector-body .message-text')
            items=client.call('GET',base+'/items?agent='+actor+'&limit=100')['items']
            matches=0
            for item in reversed(items):
                if item.get('source','').startswith('codex-ipc/') and item.get('text') and not item.get('truncated'):
                    # Native IDs are opaque; compare properties without constructing executable code.
                    found=page.locator('#inspector-body .message').evaluate_all('(nodes,id)=>nodes.filter(n=>n.dataset.item===id).map(n=>n.querySelector(".message-text").textContent)',item['id'])
                    if found and found[0]==item['text']:matches+=1
                    if matches>=3:break
            check('original native message text reaches browser exactly',matches>=1)
            page.locator('#close').click()
            page.locator('#search').fill('WPT-C07');page.locator('#search').press('Enter')
            page.get_by_role('button',name='Статус',exact=True).click()
            status='Проверяю конечный пользовательский цикл'
            client.call('POST',base+'/events',{'events':[{'event_id':uuid.uuid4().hex,'project_id':project,'agent_id':actor,'source':'agent-signal','kind':'node.status','at':now(),'node_ids':['WPT-C07'],'payload':{'status':status,'explanation':'Actual integration acceptance in progress'}}]})
            page.wait_for_function('(text)=>document.querySelector("#inspector-body").textContent.includes(text)',arg=status,timeout=15000)
            check('actual checkpoint event refreshes open status inspector',True)
            check('browser contains real revised plan head',page.locator('#version option').count()>=2)
            check('no browser application errors',not errors)
            result={'status':'PASS','fixture':False,'transport':'actual Chromium → localhost HTTP → current Store → real selected Codex projections','browser':browser.version,'checks':checks,'exact_native_text_matches':matches,'actors_rendered':page.locator('.agent-card').count(),'page_error_count':len(errors),'no_transcript_export':True,'limitations':['This bounded test does not measure end-to-end token latency or all client versions.']}
        finally:browser.close()
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    try:run(Path(sys.argv[1]),Path(sys.argv[2]))
    except Exception as exc:
        # Browser errors can embed the private navigation URL; never print it.
        print(json.dumps({'status':'FAIL','error_type':type(exc).__name__,'reason':'Inspect locally; private URLs and source texts suppressed'}));raise SystemExit(1)
