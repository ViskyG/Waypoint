"""Focused real HTTP check for non-message inspector reader state, synthetic data."""
import copy
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.request import Request,urlopen
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
checks=[]
with tempfile.TemporaryDirectory(prefix='waypoint-details-') as temporary:
    data=Path(temporary)
    service=subprocess.Popen([sys.executable,'-m','waypoint','--data',str(data),'serve','--port','18774','--demo'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+12
        while not (data/'access.json').exists() and time.monotonic()<deadline:time.sleep(.05)
        tokens=json.loads((data/'access.json').read_text())
        def api(path,body=None):
            request=Request('http://127.0.0.1:18774'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+tokens['write' if body is not None else 'read'],'Content-Type':'application/json'})
            with urlopen(request,timeout=10) as response:return json.loads(response.read())
        while True:
            try:api('/api/health');break
            except OSError:
                if time.monotonic()>deadline:raise
                time.sleep(.05)
        def change(assignment):
            current=api('/api/p/demo/plan');plan=copy.deepcopy(current['plan']);plan['nodes']['W-02']['assignment']=assignment
            return api('/api/p/demo/plans',{'plan':plan,'base_version':current['version'],'request_id':uuid.uuid4().hex})
        assignment='Synthetic long assignment for stable detail reading.\n'*80
        change(assignment)
        with sync_playwright() as p:
            executable=next(str(path) for path in [Path('/usr/bin/chromium'),Path(p.chromium.executable_path),*sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'),reverse=True)] if path.exists())
            browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1660,'height':1050})
            page.goto('http://127.0.0.1:18774/#key='+tokens['read']);page.locator('[data-node="W-02"] .assignment').click();page.locator('#inspector-body .prose').first.wait_for()
            page.evaluate("""()=>{ window.__body=document.querySelector('#inspector-body');window.__prose=__body.querySelector('.prose');__body.scrollTop=200;const range=document.createRange();range.setStart(__prose.firstChild,0);range.setEnd(__prose.firstChild,25);getSelection().removeAllRanges();getSelection().addRange(range); }""")
            original=page.evaluate('getSelection().toString()');top=page.locator('#inspector-body').evaluate('e=>e.scrollTop')
            event={'event_id':uuid.uuid4().hex,'project_id':'demo','source':'details-fixture','kind':'node.status','agent_id':'A3','at':'2026-10-17T12:00:00Z','node_ids':['W-03'],'payload':{'status':'Synthetic unrelated status'}}
            api('/api/p/demo/events',{'events':[event]});page.wait_for_function("()=>document.querySelector('[data-node=W-03] .status-label')?.textContent==='Synthetic unrelated status'")
            assert page.evaluate("__prose===document.querySelector('#inspector-body .prose') && getSelection().toString()") == original
            checks.append('Unrelated event preserves assignment DOM and selection')
            changed=change(assignment+'Updated synthetic assignment.')
            page.wait_for_function('(version)=>waypointView().version===version',arg=changed['version'])
            assert page.evaluate("__prose===document.querySelector('#inspector-body .prose') && getSelection().toString()") == original
            checks.append('Relevant plan update is deferred while assignment text is selected')
            page.evaluate('getSelection().removeAllRanges()');page.wait_for_function("()=>document.querySelector('#inspector-body .prose')?.textContent.includes('Updated synthetic assignment')")
            assert page.locator('#inspector-body').evaluate('e=>e.scrollTop')==top
            checks.append('Assignment updates after selection clears and preserves scroll')
            page.locator('#close').click();page.locator('#diff').click();page.locator('.diff-row').first.wait_for();page.evaluate("window.__diff=document.querySelector('.diff-row')")
            event.update(event_id=uuid.uuid4().hex,payload={'status':'Synthetic second status'})
            api('/api/p/demo/events',{'events':[event]});page.wait_for_function("()=>document.querySelector('[data-node=W-03] .status-label')?.textContent==='Synthetic second status'")
            assert page.evaluate("__diff===document.querySelector('.diff-row')")
            checks.append('Unrelated event preserves structural diff inspector')
            browser.close()
        report={'status':'PASS','fixture':'SYNTHETIC','transport':'real localhost HTTP','live_codex_tested':False,'checks':checks,'check_count':len(checks)}
        (root/'evidence/browser-details-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:
        service.terminate();service.wait(timeout=20)
