#!/usr/bin/env python3
"""Bounded real local CLI→HTTP→Store→CLI check. Does not connect to Codex.
Creates one temporary service/data directory and removes it in finally.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'waypoint'
checks=[]
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
with tempfile.TemporaryDirectory(prefix='waypoint-roadmap-cli-') as directory:
    tmp=Path(directory)
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    env={**os.environ,'PYTHONPATH':str(BASE)}
    process=subprocess.Popen([sys.executable,'-m','waypoint','--data',str(tmp/'data'),'serve','--port',str(port)],cwd=str(BASE),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def cmd(*args):
        p=subprocess.run([sys.executable,'-m','waypoint','--data',str(tmp/'data'),'--project','waypoint',*args],cwd=str(BASE),env=env,capture_output=True,text=True,timeout=8)
        if p.returncode:raise RuntimeError('Command failed: '+args[0]+'; '+p.stderr[-500:])
        return json.loads(p.stdout)
    try:
        deadline=time.monotonic()+8
        while True:
            if process.poll() is not None:raise RuntimeError('Disposable service failed at startup')
            try:
                if (tmp/'data/connection.json').exists():cmd('projects');break
            except RuntimeError:pass
            if time.monotonic()>deadline:raise TimeoutError('Disposable service startup')
            time.sleep(.08)
        first=cmd('plan-import',str(ROOT/'INITIAL_IMPORT.json'))
        check('native_cli_import_success',bool(first.get('version')))
        repeated=cmd('plan-import',str(ROOT/'INITIAL_IMPORT.json'))
        check('native_cli_import_retry_same_receipt',first==repeated)
        p=cmd('packet','WPT-C05')
        check('native_cli_packet_correct',p['node_id']=='WPT-C05' and len(p['children'])==4 and p['plan_version']==first['version'])
        cmd('plan-export',str(tmp/'export.json'))
        exported=json.loads((tmp/'export.json').read_text())
        expected=json.loads((ROOT/'ROADMAP.plan.json').read_text())
        check('native_cli_export_all_fields_equal',exported['plan']==expected and exported['base_version']==first['version'])
        cmd('emit',str(ROOT/'INITIAL_SOURCE_EVIDENCE.json'))
        check('native_cli_seed_retry_idempotent',all(not r['created'] for r in cmd('emit',str(ROOT/'INITIAL_SOURCE_EVIDENCE.json'))['receipts']))
        state=cmd('state')
        check('no_agent_or_future_test_created',not state['agents'] and not state['checks'])
        check('baseline_group_is_not_planned_work',next(s for s in state['node_states'] if s['id']=='WPT-BASE')['status']=='Исходники поставлены')
    finally:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
result={'status':'PASS','checks':checks,'check_count':len(checks),
        'scope':'real CLI and disposable loopback HTTP service using delivered implementation; no browser network, no native Codex, no owner installation',
        'cleanup':'own service stopped; temporary data and credentials removed'}
(ROOT/'evidence/CLI_IMPORT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
