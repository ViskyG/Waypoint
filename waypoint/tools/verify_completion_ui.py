#!/usr/bin/env python3
"""Read-only installed Chromium check for completion colors and evidence access."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from waypoint.client import Client
from playwright.sync_api import sync_playwright, expect

def run(data,output):
    client=Client(data,timeout=8);state=client.call('GET','/api/p/waypoint/state');checks=[]
    baseline=client.call('GET','/api/p/waypoint/items?node=WPT-N00&deep=false&limit=1')['items']
    assert not baseline,'Choose an actually empty block for this check'
    with sync_playwright() as pw:
        choices=[Path('/usr/bin/chromium'),Path(pw.chromium.executable_path),*sorted(Path.home().glob('.cache/ms-playwright/chromium-*/chrome-linux64/chrome'),reverse=True)]
        browser=pw.chromium.launch(executable_path=next(str(p) for p in choices if p.exists()),headless=True,args=['--no-sandbox'])
        try:
            page=browser.new_page(viewport={'width':1500,'height':1050});errors=[]
            page.on('pageerror',lambda e:errors.append(type(e).__name__))
            page.goto(client.url+'/#project=waypoint&node=WPT-N00&key='+client.tokens['read'],wait_until='domcontentloaded')
            page.locator('.node[data-node=WPT-N00]').wait_for();page.locator('#close').click()
            for theme in ['obsidian','terracotta']:
                page.select_option('#theme',theme)
                card=page.locator('.node[data-node=WPT-N00]')
                colors=card.evaluate("""(node)=>{const ref=document.createElement('span');ref.style.color='var(--pass)';document.body.append(ref);const pass=getComputedStyle(ref).color;ref.style.background='var(--pass-soft)';const soft=getComputedStyle(ref).backgroundColor;ref.remove();return {pass,soft,header:getComputedStyle(node.querySelector('.test-row')).backgroundColor,border:getComputedStyle(node).borderLeftColor,badge:getComputedStyle(node.querySelector('.status-label')).color}}""")
                # Selection keeps its outer shadow; the completion border stays green.
                expect(card).to_have_css('border-left-color',colors['pass'])
                assert colors['badge']==colors['pass'] and colors['header']==colors['soft'], colors
                assert 'Готово' in card.locator('.status-label').inner_text()
                expected=sum(c['outcome']=='passed' for c in state['checks'] if c['node_id']=='WPT-N00')
                assert card.locator('.test-count').inner_text()==f"{expected}/{len(state['plan']['nodes']['WPT-N00']['tests'])}"
                assert 'Нет привязанных сообщений' in card.locator('.messages').inner_text()
                checks.append(theme+': saved completion color, Russian label and actual check count')
                card.locator('.node-result-link').click()
                assert state['node_views']['WPT-N00']['status']['result']['evidence_ref'] in page.locator('#inspector-body').inner_text()
                page.locator('#tabs').get_by_role('button',name='Тесты',exact=True).click()
                assert page.locator('#inspector-body .checkline').count()==len(state['plan']['nodes']['WPT-N00']['tests'])
                assert 'Результат внесён из сохранённых доказательств' in page.locator('#inspector-body').inner_text()
                assert 'Основание проверки' in page.locator('#inspector-body').inner_text()
                checks.append(theme+': result and per-check evidence visible without synthetic chat')
                page.locator('#close').click();page.locator('[data-view=plan]').click()
                row=page.locator('.plan-row[data-node=WPT-N00]');row.wait_for()
                assert row.get_attribute('data-status')=='done'
                assert 'Готово' in row.locator('.plan-status').inner_text()
                assert row.locator('.plan-checks').inner_text()==f"Подтверждено проверок: {expected}/{len(state['plan']['nodes']['WPT-N00']['tests'])}"
                assert page.locator('.plan-row[data-node=WPT-N09]').get_attribute('data-status')!='done'
                checks.append(theme+': Plan distinguishes done and awaiting reference')
                page.locator('[data-view=map]').click()
                card.screenshot(path=str(output.parent/f'completion-{theme}.png'))
            assert not errors
            assert client.call('GET','/api/p/waypoint/items?node=WPT-N00&deep=false&limit=1')['items']==baseline
            result={'status':'PASS','fixture':False,'method':'Actual installed Chromium → HTTP → current Store, read-only','checks':checks,'browser':browser.version,'reported_checks':len(state['checks']),'empty_block_stayed_empty':True,'page_errors':0,'private_text_exported':False,'screenshots':'N00 only: authored plan and proof labels; no conversation bodies'}
            output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
        finally:browser.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('data',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    try:run(a.data,a.output)
    except Exception as error:
        print(json.dumps({'status':'FAIL','error_type':type(error).__name__,'assertion':str(error) if isinstance(error,AssertionError) else '', 'reason':'Private navigation URL and source text suppressed'}));raise SystemExit(1)
