"""Remaining roadmap scenarios: actual Chromium→HTTP→disposable Store.

All messages, algorithm observations and checks are explicitly SYNTHETIC.
No route interception, set_content, production DB or Codex provider contact.
Each invocation requires a new output directory and preserves failed receipts.
"""
from __future__ import annotations

import argparse
import copy
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
sys.path[:0] = [str(ROOT/'waypoint'), str(ROOT/'waypoint/tests')]
from stage2_http_browser_check import plan, TOKENS
from waypoint.domain import now

CASES = ('reader', 'defaults', 'nested_default', 'algorithms', 'provenance', 'warnings')
SOURCE_PATHS = ('waypoint/waypoint/web/app.js', 'waypoint/waypoint/web/filters.js', 'waypoint/waypoint/web/style.css',
                'waypoint/waypoint/web/algorithm_panel.js', 'waypoint/waypoint/web/plan.js',
                'waypoint/waypoint/store.py', 'waypoint/waypoint/read_models.py',
                'waypoint/waypoint/server.py', 'waypoint/waypoint/warning_history.py',
                'waypoint/tests/remaining_browser_check.py')


def source_hashes():
    return {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
            for path in SOURCE_PATHS if (ROOT/path).exists()}


def run(output: Path, port: int, cases, diagnostic_selection=False):
    from playwright.sync_api import sync_playwright
    output.mkdir(parents=True, exist_ok=False)
    base = f'http://127.0.0.1:{port}'
    project = 'remaining-synthetic'
    result = {'started_at': now(), 'status': 'RUNNING', 'checks': [], 'metrics': {},
              'scope': 'SYNTHETIC fixtures; real Chromium → loopback HTTP → disposable schema3 Store',
              'live_codex_tested': False, 'production_data_modified': False,
              'api_routes_mocked': False, 'cases_requested': list(cases),
              'browser_errors': [], 'source_hashes_at_start': source_hashes(),
              'limitations': ['This script proves controlled application scenarios, not native Codex observations.',
                              'Native source, production restart and historical artifact review are separate evidence.']}
    browser = page = service = None
    current = 'setup'

    def api(path, body=None):
        req = Request(base+path, data=json.dumps(body).encode() if body is not None else None,
                      headers={'Authorization':'Bearer '+TOKENS['write' if body is not None else 'read'],
                               'Content-Type':'application/json'})
        with urlopen(req, timeout=10) as response:
            return json.load(response)

    def event(kind, payload, nodes=None, actor='actor', at=None):
        return {'event_id': uuid.uuid4().hex, 'project_id': project, 'source':'synthetic-remaining',
                'kind':kind, 'agent_id':actor, 'at':at or now(), 'node_ids':nodes or [],
                'edge_ids':[], 'payload':payload}

    def emit(kind, payload, nodes=None, actor='actor', at=None):
        return api('/api/p/'+project+'/events', {'events':[event(kind,payload,nodes,actor,at)]})

    def check(label, condition=True, **detail):
        nonlocal current
        current = label
        result['checks'].append({'name':label, 'passed':bool(condition), **detail})
        if not condition:
            raise AssertionError(label)

    def wait_count(selector, number):
        page.wait_for_function('(v)=>document.querySelectorAll(v.selector).length===v.number',
                               arg={'selector':selector,'number':number}, timeout=8000)

    def click_control(locator):
        # Actual Playwright mouse click. Sticky reader controls retain the old
        # viewport while the browser performs focus/default pointer actions.
        locator.click()

    def open_project(context):
        nonlocal page
        page = context.new_page()
        page.set_viewport_size({'width':1660,'height':1050})
        page.on('pageerror', lambda error: result['browser_errors'].append(str(error)))
        page.goto(base+'/#key='+TOKENS['read'])
        page.locator('.project-card[data-project="'+project+'"] button').click()
        page.locator('.node[data-node="ROOT"]').wait_for()
        return page

    def open_messages(node='ROOT'):
        if page.locator('#close').is_visible():
            page.locator('#close').click()
        page.locator('.node[data-node="'+node+'"] .assignment').click()
        page.locator('#tabs').get_by_text('Сообщения', exact=True).click()
        page.locator('.reader-filter summary').wait_for()
        click_control(page.locator('.reader-filter summary'))

    def filter_button(label):
        return page.locator('#inspector-body .type-filter').get_by_text(label, exact=True)

    def reader_items():
        return page.locator('#inspector-body .message').evaluate_all('(xs)=>xs.map(x=>x.dataset.item)')

    def anchor():
        return page.locator('#inspector-body').evaluate('''(body)=>{
            const top=body.getBoundingClientRect().top;
            const controls=body.querySelector('.reader-controls');
            const visibleTop=controls ? Math.max(top,controls.getBoundingClientRect().bottom) : top;
            const box=[...body.querySelectorAll('.message')].find(x=>x.getBoundingClientRect().bottom>visibleTop);
            return box ? {item:box.dataset.item,offset:box.getBoundingClientRect().top-top} : null;
        }''')

    def anchor_offset(saved):
        return page.locator('#inspector-body').evaluate('''(body,item)=>{
            const box=[...body.querySelectorAll('.message')].find(x=>x.dataset.item===item);
            return box ? box.getBoundingClientRect().top-body.getBoundingClientRect().top : null;
        }''', saved['item'])

    def scroll_to_item(item):
        page.locator('#inspector-body').evaluate('''(body,item)=>{
            const box=[...body.querySelectorAll('.message')].find(x=>x.dataset.item===item);
            const top=body.getBoundingClientRect().top;const controls=body.querySelector('.reader-controls');
            const visibleTop=controls ? Math.max(top,controls.getBoundingClientRect().bottom) : top;
            body.scrollTop+=box.getBoundingClientRect().top-visibleTop-2;
            body.dispatchEvent(new Event('scroll'));
        }''', item)

    def select_item(item):
        page.locator('#inspector-body .message[data-item="'+item+'"] .message-text').evaluate('''(element)=>{
            const range=document.createRange();range.setStart(element.firstChild,0);
            range.setEnd(element.firstChild,Math.min(element.firstChild.length,36));
            const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
        }''')
        return page.evaluate('getSelection().toString()')

    def selected_query():
        return page.locator('#inspector-body .type-filter').evaluate('''(field)=>({
            selected:[...field.querySelectorAll('input[data-category]:checked')].map(x=>x.dataset.category),
            errors:[...field.querySelectorAll('label')].find(x=>x.textContent.includes('Только ошибки')).querySelector('input').checked
        })''')

    def error_checkbox():
        return page.locator('#inspector-body .type-filter label').filter(has_text='Только ошибки').locator('input')

    def fixture():
        p=plan(project)
        p['x_observability']['workspace_ref']='synthetic-workspace'
        p['nodes']['OTHER']['x_observability']['outputs']={'OUT':{'definition':'Synthetic required artifact','revision':1}}
        p['edges']['NEEDS']={'from':'OTHER','to':'ROOT','x_observability':{
            'relation':'requires','phase':'start','target_scope':'node','why':'Synthetic missing input history',
            'condition':{'output_id':'OUT','revision':1,'workspace':'consumer'}}}
        initial=api('/api/p/'+project+'/plans',{'plan':p,'request_id':'remaining-initial'})
        events=[event('agent.upsert',{'name':'Synthetic acceptance actor'})]
        for node in ['OTHER','LEAF']:
            events += [event('item.upsert',{'item_id':node+'-message','type':'agentMessage',
                        'text':node+' visible ordinary synthetic message','state':'completed'},[node]),
                       event('item.upsert',{'item_id':node+'-failed','type':'commandExecution',
                        'text':node+' explicit synthetic failure','state':'failed'},[node])]
        events += [event('item.upsert',{'item_id':f'msg-{index}','type':'agentMessage',
                    'text':f'Original message {index}. '+('Bounded reader original text. '*12),
                    'state':'completed'},['ROOT']) for index in range(330)]
        api('/api/p/'+project+'/events',{'events':events})
        observations=[]
        for index in range(237):
            correctness='failed' if index==0 else 'passed' if index==1 else 'not_run'
            payload={'algorithm_id':'merge','definition_revision':1,'implementation_ref':'synthetic-r1',
                     'observation_kind':'integration' if index==1 else 'correctness',
                     'correctness':{'outcome':correctness,'evidence_refs':['fixture:remaining'] if correctness!='not_run' else []},
                     'measurement':None,'comparison':None,'note':'Synthetic observed history; not a real algorithm run'}
            observations.append(event('algorithm.observation',payload,['ROOT'],actor='algorithm-fixture'))
        api('/api/p/'+project+'/events',{'events':observations})
        return p,initial['version']

    try:
        with tempfile.TemporaryDirectory(prefix='waypoint-remaining-browser-') as temporary:
            log_path=Path(temporary)/'service.log'
            with log_path.open('w') as log:
                service=subprocess.Popen([sys.executable,str(ROOT/'waypoint/tests/stage2_http_browser_check.py'),
                    '--serve',temporary,'--port',str(port)],stdout=log,stderr=log,cwd=ROOT)
                try:
                    for _ in range(100):
                        try:
                            api('/api/health');break
                        except Exception:
                            if service.poll() is not None:
                                raise RuntimeError(log_path.read_text()[-3000:])
                            time.sleep(.05)
                    else:
                        raise RuntimeError('Disposable service did not start')
                    p,initial_version=fixture()
                    with sync_playwright() as pw:
                        choices=[Path('/usr/bin/chromium'),Path(pw.chromium.executable_path),
                                 *sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'),reverse=True)]
                        browser=pw.chromium.launch(executable_path=str(next(path for path in choices if path.exists())),
                                                  headless=True,args=['--no-sandbox'])
                        result['browser']=browser.version
                        if 'reader' in cases:
                            current='N04 reader setup';context=browser.new_context();open_project(context);open_messages()
                            page.locator('#inspector-body .message[data-item="msg-329"]').wait_for()
                            check('N04 initial reader uses bounded latest100',len(reader_items())==100)
                            scroll_to_item('msg-250'); saved=anchor(); selected=select_item(saved['item'])
                            old_offset=saved['offset']
                            emit('item.upsert',{'item_id':'msg-230','type':'agentMessage',
                                'text':'Changed height above viewport. '+('Expanded synthetic source text. '*120),
                                'state':'completed'},['ROOT'])
                            page.wait_for_function('''()=>document.querySelector('#inspector-body .message[data-item="msg-230"] .message-text')?.textContent.startsWith('Changed height')''',timeout=8000)
                            check('N04 correction height above viewport preserves item and pixel anchor',
                                  abs(anchor_offset(saved)-old_offset)<3,anchor=saved,offset_after=anchor_offset(saved))
                            check('N04 source correction preserves selected original text',page.evaluate('getSelection().toString()')==selected)
                            click_control(page.locator('#inspector-body .older-messages'))
                            wait_count('#inspector-body .message',200)
                            check('N04 prepend preserves selected item anchor with200-row limit',
                                  abs(anchor_offset(saved)-old_offset)<3 and page.evaluate('getSelection().toString()')==selected,
                                  offset_after=anchor_offset(saved))
                            original_window=reader_items()
                            result['metrics']['selection_before_filters']=page.evaluate('getSelection().toString()')
                            if diagnostic_selection:
                                result['metrics']['external_selection']=page.evaluate('''()=>{
                                    const s=getSelection();
                                    const point=(node,offset)=>{const box=node.parentElement.closest('.message');
                                        const range=document.createRange();range.selectNodeContents(box);range.setEnd(node,offset);
                                        const prefix=range.toString();let remaining=prefix.length,leaf,target;
                                        const walker=document.createTreeWalker(box,NodeFilter.SHOW_TEXT);
                                        while((leaf=walker.nextNode())){if(remaining<=leaf.length){target={node:leaf,offset:remaining};break;}remaining-=leaf.length;}
                                        return {key:box.dataset.itemKey,offset:prefix.length,prefix,
                                            native_node_text:node.textContent,native_offset:offset,
                                            walker_node_text:target?.node.textContent,walker_offset:target?.offset,
                                            target};};
                                    const a=point(s.anchorNode,s.anchorOffset),b=point(s.focusNode,s.focusOffset);
                                    const range=document.createRange();range.setStart(a.target.node,a.target.offset);range.setEnd(b.target.node,b.target.offset);
                                    const sameDOM=range.toString();delete a.target;delete b.target;
                                    return {anchor:a,focus:b,text:s.toString(),same_dom_reconstruction:sameDOM};
                                }''')
                            click_control(filter_button('Ничего'));wait_count('#inspector-body .message',0)
                            click_control(page.locator('#inspector-body input[data-category="message"]'))
                            page.locator('#inspector-body .message[data-item="msg-329"]').wait_for()
                            click_control(filter_button('Все'))
                            page.wait_for_function('(ids)=>JSON.stringify([...document.querySelectorAll("#inspector-body .message")].map(x=>x.dataset.item))===JSON.stringify(ids)',arg=original_window)
                            check('N04 filter roundtrip restores exact old window rather than latest100',reader_items()==original_window)
                            actual_selected=page.evaluate('getSelection().toString()')
                            if diagnostic_selection:
                                result['metrics']['external_selection_after_return']=page.evaluate('''saved=>{
                                    const point=v=>{const box=[...document.querySelectorAll('#inspector-body .message')].find(x=>x.dataset.itemKey===v.key);
                                        if(!box)return null;let remaining=v.offset,node;const walker=document.createTreeWalker(box,NodeFilter.SHOW_TEXT);
                                        while((node=walker.nextNode())){if(remaining<=node.length)return [node,remaining];remaining-=node.length;}return null;};
                                    const a=point(saved.anchor),b=point(saved.focus);const actual=getSelection().toString();
                                    if(a&&b)getSelection().setBaseAndExtent(...a,...b);
                                    return {actual_before_external_restore:actual,external_restored_text:getSelection().toString(),endpoints_found:!!a&&!!b};
                                }''',result['metrics']['external_selection'])
                            check('N04 filter roundtrip restores anchor and selection',
                                  abs(anchor_offset(saved)-old_offset)<3 and actual_selected==selected,
                                  offset_after=anchor_offset(saved),selected_expected=selected,selected_actual=actual_selected)
                            page.evaluate('getSelection().removeAllRanges()')
                            scroll_to_item('msg-150'); cap_anchor=anchor()
                            click_control(page.locator('#inspector-body .older-messages'))
                            page.locator('#inspector-body .message[data-item="msg-30"]').wait_for()
                            check('N04 repeated prepend stays capped at200 and preserves retained anchor',
                                  len(reader_items())==200 and abs(anchor_offset(cap_anchor)-cap_anchor['offset'])<3)
                            # Return to a message-only old window for F01 negative corrections.
                            click_control(filter_button('Ничего'));wait_count('#inspector-body .message',0)
                            click_control(page.locator('#inspector-body input[data-category="message"]'))
                            page.locator('#inspector-body .message[data-item="msg-329"]').wait_for()
                            click_control(page.locator('#inspector-body .older-messages'));wait_count('#inspector-body .message',200)
                            scroll_to_item('msg-240')
                            emit('item.upsert',{'item_id':'msg-210','type':'commandExecution','text':'Corrected out of message-only filter','state':'completed'},['ROOT'])
                            wait_count('#inspector-body .message[data-item="msg-210"]',0)
                            check('F01 corrected-out item leaves an older filtered window while neighbors remain',
                                  page.locator('#inspector-body .message[data-item="msg-211"]').count()==1)
                            emit('item.link',{'item_id':'msg-212'},['OTHER'])
                            wait_count('#inspector-body .message[data-item="msg-212"]',0)
                            check('F01 moved-scope item leaves an older filtered window while neighbors remain',
                                  page.locator('#inspector-body .message[data-item="msg-213"]').count()==1)
                            page.screenshot(path=str(output/'reader.png'));context.close();page=None
                        if 'defaults' in cases:
                            for variant in ['all','none','errors']:
                                current='N04 default '+variant;context=browser.new_context();open_project(context);open_messages()
                                page.locator('#inspector-body .message').first.wait_for()
                                click_control(filter_button('Ничего' if variant=='none' else 'Все'))
                                if variant=='errors':click_control(error_checkbox())
                                expected=selected_query()
                                click_control(page.locator('#inspector-body .reader-save-default'))
                                open_messages('OTHER')
                                expected_count=0 if variant=='none' else 1 if variant=='errors' else len(api('/api/p/'+project+'/items?node=OTHER&deep=true&limit=100')['items'])
                                wait_count('#inspector-body .message',expected_count)
                                check('N04 new reader inherits global '+variant+' default',selected_query()==expected)
                                check('N04 existing map-card reader stays independent from global '+variant+' default',
                                      page.locator('.node[data-node="ROOT"] .messages .message').count()>1)
                                context.close();page=None
                            # Merely opening an All reader creates an existing preference;
                            # a later global seed must not silently overwrite it on reload.
                            context=browser.new_context();open_project(context);open_messages('OTHER')
                            untouched=selected_query()
                            open_messages('ROOT');click_control(error_checkbox());click_control(page.locator('#inspector-body .reader-save-default'))
                            open_messages('OTHER')
                            check('N04 untouched existing All reader stays independent from later default',selected_query()==untouched)
                            page.reload();page.locator('.node[data-node="ROOT"]').wait_for();open_messages('OTHER')
                            check('N04 untouched existing All reader survives reload after later default',selected_query()==untouched)
                            context.close();page=None
                            # A per-reader saved preference precedes a later global default.
                            context=browser.new_context();open_project(context);open_messages('OTHER')
                            click_control(filter_button('Ничего'));wait_count('#inspector-body .message',0)
                            open_messages('ROOT');click_control(error_checkbox());click_control(page.locator('#inspector-body .reader-save-default'))
                            open_messages('OTHER');wait_count('#inspector-body .message',0)
                            check('N04 existing reader preference survives a later global default',len(selected_query()['selected'])==0)
                            page.reload();page.locator('.node[data-node="ROOT"]').wait_for();open_messages('OTHER')
                            wait_count('#inspector-body .message',0)
                            check('N04 saved per-reader preference overrides global seed after reload',len(selected_query()['selected'])==0)
                            page.screenshot(path=str(output/'defaults.png'));context.close();page=None
                        if 'nested_default' in cases:
                            current='N04 nested default';context=browser.new_context();open_project(context);open_messages('ROOT')
                            click_control(error_checkbox());click_control(page.locator('#inspector-body .reader-save-default'))
                            page.locator('#close').click()
                            page.locator('.node[data-node="ROOT"]').get_by_role('button',name='Раскрыть ROOT',exact=True).click()
                            page.locator('.node[data-node="LEAF"]').wait_for();open_messages('LEAF')
                            wait_count('#inspector-body .message',1)
                            check('N04 new nested reader inherits global errors without changing saved readers',selected_query()['errors'] is True)
                            page.screenshot(path=str(output/'nested-default.png'));context.close();page=None
                        if 'algorithms' in cases:
                            current='N05 algorithm pages';context=browser.new_context();open_project(context)
                            page.locator('#project-views button[data-view="algorithms"]').click()
                            page.locator('#algorithms-view .algorithm-card').wait_for()
                            check('N05 registry shows whole-history count with no evidence DOM',
                                  page.locator('#algorithms-view .algorithm-evidence').count()==0 and '237' in page.locator('#algorithms-view').inner_text())
                            check('N05 registry correctness includes failure outside last100',
                                  'есть неуспешная проверка' in page.locator('#algorithms-view .algorithm-status').inner_text())
                            page.locator('#algorithms-view .algorithm-title').click()
                            wait_count('#inspector-body .algorithm-evidence',100)
                            def ids():
                                return [text.split(' · ')[0] for text in page.locator('#inspector-body .algorithm-evidence summary').all_text_contents()]
                            observed=[];pages=[]
                            for index,size in enumerate([100,100,37]):
                                if index:
                                    old_ids=ids();click_control(page.locator('#inspector-body .algorithm-older'))
                                    page.wait_for_function('(before)=>JSON.stringify([...document.querySelectorAll("#inspector-body .algorithm-evidence summary")].map(x=>x.textContent.split(" · ")[0]))!==JSON.stringify(before)',arg=old_ids)
                                    wait_count('#inspector-body .algorithm-evidence',size)
                                values=ids();pages.append(values);observed+=values
                                check('N05 page '+str(index+1)+' is bounded with full summary',
                                      len(values)==size and '237' in page.locator('#inspector-body').inner_text() and
                                      'есть неуспешная проверка' in page.locator('#inspector-body .algorithm-status').inner_text())
                            expected_ids={row['event_id'] for row in api('/api/p/'+project+'/algorithms/merge?limit=500')['algorithm']['evidence']}
                            check('N05 all237 immutable observations reachable without duplicate pages',len(observed)==237 and len(set(observed))==237 and set(observed)==expected_ids)
                            for index in [1,0]:
                                click_control(page.locator('#inspector-body .algorithm-newer'))
                                page.wait_for_function('(expected)=>JSON.stringify([...document.querySelectorAll("#inspector-body .algorithm-evidence summary")].map(x=>x.textContent.split(" · ")[0]))===JSON.stringify(expected)',arg=pages[index])
                                check('N05 newer navigation returns exact prior page '+str(index+1),ids()==pages[index] and len(ids())<=100)
                            result['metrics']['algorithm_page_sizes']=[len(values) for values in pages]
                            page.screenshot(path=str(output/'algorithms.png'));context.close();page=None
                        if 'provenance' in cases:
                            current='N07 evidence provenance'
                            registered_at=now()
                            receipt=emit('test.result',{'test_id':'T','run_id':'synthetic-prior-run-42','outcome':'passed',
                                'freshness':'unknown','plan_version':initial_version,'basis':'Synthetic saved report at immutable fixture path; not a new execution',
                                'evidence_refs':['fixture:immutable-saved-report'], 'registered_from_existing_evidence':True,
                                'registration_method':'Late registration for UI contract fixture'},['ROOT'],at=registered_at)
                            changed=copy.deepcopy(p);changed['title']='Synthetic changed current plan'
                            current_version=api('/api/p/'+project+'/plans',{'plan':changed,'base_version':initial_version,'request_id':'remaining-provenance-version'})['version']
                            context=browser.new_context();open_project(context)
                            page.locator('.node[data-node="ROOT"] .assignment').click();page.locator('#tabs').get_by_text('Тесты',exact=True).click()
                            text=page.locator('#inspector-body').inner_text()
                            check('N07 test inspector separates actual run registration and receipt',
                                  all(value in text for value in ['synthetic-prior-run-42',registered_at,'Receipt: '+str(receipt['receipts'][0]['seq'])]))
                            check('N07 test inspector exposes current and registered plan versions',initial_version in text and current_version in text and current_version!=initial_version)
                            check('N07 late registration and declared freshness do not imply new execution',
                                  'это не новый запуск теста' in text and 'ручная декларация' in text and 'актуальность не подтверждена' in text)
                            result['metrics']['synthetic_test_receipt']={'seq':receipt['receipts'][0]['seq'],'registered_at':registered_at,'check_plan':initial_version,'current_plan':current_version}
                            page.screenshot(path=str(output/'provenance.png'));context.close();page=None
                        if 'warnings' in cases:
                            current='N08 grouped warnings'
                            requirement=api('/api/p/'+project+'/prerequisites?node=ROOT')['requirements'][0]
                            for _ in range(3):emit('scope.set',{},['ROOT'],actor='warning-actor')
                            def dependency(availability):
                                return {'edge_id':'NEEDS','consumer_id':'ROOT',
                                    'requirement_fingerprint':requirement['requirement_fingerprint'],'workspace_ref':'synthetic-workspace',
                                    'availability':availability,'occurred_at':now(),
                                    'basis':{'kind':'artifact','ref':'fixture:reviewed-'+availability,
                                             'revision':'synthetic-r1','explanation':'Synthetic explicit observation; no physical artifact claim'}}
                            emit('dependency.observation',dependency('missing'),['ROOT'],actor='warning-reviewer')
                            for _ in range(2):emit('scope.set',{},['ROOT'],actor='warning-actor')
                            emit('dependency.observation',dependency('available'),['ROOT'],actor='warning-reviewer')
                            packet=api('/api/p/'+project+'/packet/ROOT')
                            check('N08 API groups repeated starts by exact unresolved basis and retains five raw records',
                                  packet['dependency_warning_count']==5 and len(packet['dependency_incidents'])==2 and
                                  sorted(group['receipt_count'] for group in packet['dependency_incidents'])==[2,3] and len(packet['dependency_warnings'])==5)
                            context=browser.new_context();open_project(context)
                            page.locator('.node[data-node="ROOT"] .assignment').click()
                            wait_count('#inspector-body .dependency-incident',2)
                            check('N08 UI shows grouped incidents after later availability instead of five independent starts',
                                  'записей журнала: 5' in page.locator('#inspector-body').inner_text())
                            raw=page.locator('#inspector-body .dependency-warning-raw');click_control(raw.locator('summary'))
                            check('N08 UI retains expandable raw warning history',raw.locator('.dependency-record').count()==5)
                            result['metrics']['dependency_incidents']={'groups':2,'raw_records':5,'counts':[group['receipt_count'] for group in packet['dependency_incidents']]}
                            page.screenshot(path=str(output/'warnings.png'));context.close();page=None
                        check('No uncaught browser application errors',not result['browser_errors'])
                        browser.close();browser=None
                finally:
                    if service and service.poll() is None:
                        service.terminate()
                        try:service.wait(timeout=5)
                        except subprocess.TimeoutExpired:service.kill();service.wait()
        check('Source stayed frozen during acceptance',source_hashes()==result['source_hashes_at_start'])
        result['status']='PASS'
    except Exception:
        result['status']='FAIL';result['failed_at']=current;result['failure']=traceback.format_exc()
        if page:
            try:page.screenshot(path=str(output/'failure.png'))
            except Exception:pass
    finally:
        if browser:
            try:browser.close()
            except Exception:pass
        result['finished_at']=now();result['source_hashes_at_finish']=source_hashes()
        result['check_count']=len(result['checks'])
        (output/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'checks':result['check_count'],'output':str(output),
                      'failed_at':result.get('failed_at'),'failure':result.get('failure')},ensure_ascii=False))
    return int(result['status']!='PASS')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--port',type=int,default=18785)
    parser.add_argument('--diagnostic-selection',action='store_true',help='Record external DOM range serialization; never bypasses the actual selection assertion')
    parser.add_argument('--cases',default=','.join(CASES),help='Comma-separated bounded cases; use a fresh output directory for each run')
    args=parser.parse_args();requested=tuple(value.strip() for value in args.cases.split(',') if value.strip())
    if not requested or any(value not in CASES for value in requested):parser.error('Unknown or empty cases')
    sys.exit(run(args.output,args.port,requested,args.diagnostic_selection))
