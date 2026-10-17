#!/usr/bin/env python3
"""Side-effect-free structure/derived-view checks. Not target acceptance."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reference'))
from legacy_domain import validate_plan
from contract_model import validate_profile

def main():
    checks=[]
    def check(name,ok):
        if not ok:raise AssertionError(name)
        checks.append(name)
    manifest=ROOT/'MANIFEST.json'
    if manifest.exists():
        for name,expected in json.loads(manifest.read_text())['files'].items():
            q=(ROOT/name).resolve()
            check('safe path '+name,q.is_relative_to(ROOT.resolve()))
            check('hash '+name,q.is_file() and hashlib.sha256(q.read_bytes()).hexdigest()==expected)
    plan=json.loads((ROOT/'roadmap/ROADMAP.plan.json').read_text())
    normalized,warnings=validate_plan(plan)
    check('native plan round-trip',normalized==plan and not warnings)
    check('profile and effective acyclic graph',validate_profile(plan)==[])
    schema_checks='not available (jsonschema absent)'
    if importlib.util.find_spec('jsonschema'):
        import jsonschema
        for file in ['contracts/native-plan.schema.json','contracts/observability-profile.schema.json']:
            schema=json.loads((ROOT/file).read_text());jsonschema.validators.validator_for(schema).check_schema(schema)
            jsonschema.validate(plan,schema)
        second=json.loads((ROOT/'contracts/examples/PROJECT.plan.json').read_text())
        jsonschema.validate(second,json.loads((ROOT/'contracts/observability-profile.schema.json').read_text()))
        schema_checks='native + profile + second-project schemas passed'
    check('all owner requirements have packet links',all(json.loads((ROOT/'design/TRACEABILITY.json').read_text()).values()))
    for node_id,n in plan['nodes'].items():
        if n.get('x_roadmap',{}).get('kind')!='packet':continue
        check('packet exists '+node_id,(ROOT/'roadmap/packets'/f'{node_id}.md').is_file())
        for ref in n['x_roadmap']['read_set']:
            path,_,anchor=ref.partition('#');q=ROOT/path
            check('read-set file '+ref,q.is_file())
            if anchor:check('read-set anchor '+ref,('id="'+anchor+'"') in q.read_text())
        check('acceptance '+node_id,bool(n['acceptance']))
        check('human intent '+node_id,bool(n['x_observability']['intent']['context']))
    check('native reference blob matches inspected',hashlib.sha1(('blob '+str((ROOT/'reference/legacy_domain.py').stat().st_size)+'\0').encode()+(ROOT/'reference/legacy_domain.py').read_bytes()).hexdigest()=='80b26ecb4d87933ac031c7c75d4c16522fbd71fc')
    subprocess.run([sys.executable,str(ROOT/'tools/render_roadmap.py'),'--check'],check=True,capture_output=True,text=True)
    check('all generated views agree with one graph',True)
    for e in json.loads((ROOT/'skills/EDITS.json').read_text())['edits']:
        check('skill amendment '+e['section'],(ROOT/'skills'/e['section']).is_file())
        check('skill expected blob '+e['path'],len(e['expected_git_blob'])==40)
    print(json.dumps({'status':'PASS','structural_checks':len(checks),'nodes':len(plan['nodes']),'edges':len(plan['edges']),'packets':sum(n.get('x_roadmap',{}).get('kind')=='packet' for n in plan['nodes'].values()),'schema_checks':schema_checks,'target_execution_started':False,'meaning':'Design/package consistency only; no target runtime acceptance.'},ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except (AssertionError,ValueError,OSError,subprocess.CalledProcessError,KeyError) as exc:print('CHECK_FAILED:',exc,file=sys.stderr);sys.exit(1)
