#!/usr/bin/env python3
"""Build an offline saved-plan view from exact current Waypoint UI assets.

Uses only the approved plan and supplied source-delivery declarations in a
throwaway Store. No production data, agent, runtime result or service is created.
"""
from pathlib import Path
import json
import re
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'waypoint'
sys.path.insert(0,str(BASE))
from waypoint.store import Store

plan=json.loads((ROOT/'ROADMAP.plan.json').read_text(encoding='utf8'))
events=json.loads((ROOT/'INITIAL_SOURCE_EVIDENCE.json').read_text(encoding='utf8'))['events']
with tempfile.TemporaryDirectory(prefix='waypoint-map-preview-') as tmp:
    store=Store(Path(tmp)/'preview.sqlite')
    try:
        receipt=store.import_plan(plan,None,'roadmap-preview-only')
        store.ingest(events,project=plan['project_id'])
        state=store.state(plan['project_id'])
        assert not state['agents'] and not state['checks'] and not state['items']
        data={'current':receipt['version'],'versions':store.versions(plan['project_id']),
              'states':{receipt['version']:state},'label_key':'shell.plan',
              'notice_key':'app.savedPlanNotice',
              'projects':[{'project_id':plan['project_id'],'title':plan['title'],
                  'purpose':plan.get('x_observability',{}).get('purpose') or 'Утверждённая дорожная карта Waypoint · сохранённая структура',
                  'distinct_active_agents':None,'distinct_active_blocks':None,'source_health':'Снимок исходной поставки, не живое подключение'}]}
    finally:store.close()
html=(BASE/'waypoint/web/index.html').read_text(encoding='utf8')
html=html.replace('<title>Waypoint · Карта работ</title>','<title>Waypoint · дорожная карта реализации</title>')
html=html.replace('<link rel="stylesheet" href="/static/style.css">','<style>'+(BASE/'waypoint/web/style.css').read_text(encoding='utf8')+'</style>')
payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
html=html.replace('</head>','<script>window.WAYPOINT_DEMO='+payload+';</script></head>')
modules=('i18n','themes','projects','plan','filters','algorithm_panel','app')
for name in modules:
    tag=f'<script src="/static/{name}.js" defer></script>'
    if tag not in html:raise RuntimeError(f'Missing declared script {name}')
    script=(BASE/'waypoint/web'/f'{name}.js').read_text(encoding='utf8').replace('</script','<\\/script')
    html=html.replace(tag,'<script>'+script+'</script>')
if re.search(r'<script[^>]+src=',html) or '<link rel="stylesheet"' in html:
    raise RuntimeError('Offline view contains unresolved script or stylesheet')
(ROOT/'PREVIEW.html').write_text(html,encoding='utf8')
print(json.dumps({'created':'roadmap/PREVIEW.html','native_graph_nodes':len(plan['nodes']),
    'agents':0,'runtime_tests':0,'source_claim_events':len(events),'script_modules':list(modules),
    'source_files_modified':False,'production_data_read':False},ensure_ascii=False,indent=2))
