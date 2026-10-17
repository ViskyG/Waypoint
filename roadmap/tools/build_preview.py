#!/usr/bin/env python3
"""Render the real roadmap using the supplied Waypoint viewer and disposable Store.

Only offline demo labels/project names are adjusted in the derived HTML. No
production file is edited, no native agent is created, no service is contacted.
"""
from pathlib import Path
import json
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
        versions=store.versions(plan['project_id'])
        data={'current':receipt['version'],'versions':versions,
              'states':{receipt['version']:store.state(plan['project_id'])}}
        assert not data['states'][receipt['version']]['agents']
        assert not data['states'][receipt['version']]['checks']
    finally:store.close()
html=(BASE/'waypoint/web/index.html').read_text(encoding='utf8')
css=(BASE/'waypoint/web/style.css').read_text(encoding='utf8')
js=(BASE/'waypoint/web/app.js').read_text(encoding='utf8')
old="const projects = demo ? [{ project_id: 'demo', title: 'Маршруты армий' }]"
new="const projects = demo ? [{ project_id: 'waypoint', title: 'Waypoint · дорожная карта реализации' }]"
assert old in js
js=js.replace(old,new,1)
assert 'Демо · вымышленные события' in js
js=js.replace('Демо · вымышленные события','Снимок плана · исполнение не запускалось')
js=js.replace("demo ? 'Демо' : 'Локально'", "demo ? 'План' : 'Локально'")
html=html.replace('<title>Waypoint · Карта работ</title>','<title>Waypoint · дорожная карта реализации</title>')
html=html.replace('<link rel="stylesheet" href="/static/style.css">','<style>'+css+'</style>')
payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
html=html.replace('<script src="/static/app.js" defer></script>',
 '<script>window.WAYPOINT_DEMO='+payload+';</script>\n<script>'+js+'</script>')
(ROOT/'PREVIEW.html').write_text(html,encoding='utf8')
print(json.dumps({'created':'PREVIEW.html','native_graph_nodes':len(plan['nodes']),
 'agents':0,'runtime_tests':0,'labels_only_override':True,'source_files_modified':False},ensure_ascii=False,indent=2))
