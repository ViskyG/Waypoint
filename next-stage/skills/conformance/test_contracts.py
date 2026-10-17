"""Bounded candidate/CLI contract proof; no service or native source operations."""
import difflib
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'waypoint'))
from waypoint.cli import parser,signals


def manifest():
    return json.loads((HERE/'STAGING.json').read_text())


def test_global_candidates_exact_current_source_and_bounded_patches():
    m=manifest()
    assert m['state']=='PREPARED_NOT_PUBLISHED_NOT_INSTALLED'
    assert m['canonical_checkout_modified'] is False and m['global_installation'] is False
    entries=[e for e in m['files']if e['repository']=='agent-skills']
    assert {e['role']for e in entries}=={'execute','roadmap','audit'}
    for e in entries:
        src=(HERE/e['base_snapshot']).read_text()
        assert hashlib.sha256(src.encode()).hexdigest()==e['source_sha256']
        assert Path(e['canonical_source']).read_text()==src
        actual=(HERE/e['candidate']).read_text()
        expected=src.replace('version: "2.0.0"','version: "2.0.1"',1).replace('## Canonical navigation',e['addition']+'## Canonical navigation')
        assert actual==expected
        assert hashlib.sha256(actual.encode()).hexdigest()==e['candidate_sha256']
        patch=''.join(difflib.unified_diff(src.splitlines(True),actual.splitlines(True),fromfile='a/'+e['path'],tofile='b/'+e['path']))
        assert (HERE/e['patch']).read_text()==patch
        if e['prior_observability_section']:
            old=(ROOT/'next-stage/skills/sections'/e['prior_observability_section']).read_text().strip()
            assert actual.count(old)==1
        assert (HERE/e['ru_amendment_only']).is_file()


def test_project_drafts_preserve_prior_candidate_and_status():
    for e in manifest()['files']:
        if e['repository']!='Waypoint':continue
        old=(ROOT/e['prior_candidate']).read_text()
        if e['language']=='en':
            expected=old.replace('version: "0.2.0"','version: "0.3.0"',1)
        else:
            expected=old.replace('версии 0.2.0','версии 0.3.0',1)
        section=(HERE/e['new_section']).read_text().strip()
        actual=(ROOT/e['path']).read_text()
        assert actual==expected.rstrip()+'\n\n'+section+'\n'
        assert e['status']=='draft-candidate'and e['installation']=='NOT_INSTALLED'
        if e['language']=='en':assert 'status: "draft-candidate"'in actual
        assert hashlib.sha256(actual.encode()).hexdigest()==e['candidate_sha256']


def test_all_documented_cli_commands_parse_existing_grammar():
    commands=[line for line in (HERE/'WAYPOINT_WORKFLOW.md').read_text().splitlines()if line.startswith('wp ')]
    assert len(commands)>=11
    parsed=[parser().parse_args(shlex.split(command)[1:])for command in commands]
    assert {'bind','packet','focus','status','test','done','emit','plan-export','plan-import'}<={p.command for p in parsed}
    assert not {'start','resume','stop','approve'}&{p.command for p in parsed}
    plan_import=next(p for p in parsed if p.command=='plan-import')
    assert plan_import.base=='CAPTURED_BASE_VERSION'and plan_import.merge and plan_import.request_id=='STABLE_REQUEST_ID'


def test_manual_freshness_and_explicit_release_walkthrough():
    args=['--project','policy-fixture','--agent','codex/verified-fixture']
    focus=signals(parser().parse_args(args+['focus','EXISTING-NODE']))
    check=signals(parser().parse_args(args+['test','EXISTING-NODE','TEST-NEGATIVE','not_run','--run','run-recorded','--basis','Not executed; honest remaining obligation']))
    manual=signals(parser().parse_args(args+['test','EXISTING-NODE','TEST-REAL','passed','--run','run-recorded','--basis','Immutable executed proof','--current']))
    complete=signals(parser().parse_args(args+['done','EXISTING-NODE','--result','Partial delivered','--diff','Required negative-case proof still missing; linked FIX']))
    release=signals(parser().parse_args(args+['focus']))
    assert focus[0]['kind']=='scope.set'and focus[0]['node_ids']==['EXISTING-NODE']
    assert check[0]['payload']['outcome']=='not_run'and check[0]['payload']['freshness']=='unknown'
    assert manual[0]['payload']['freshness']=='current'
    assert [e['kind']for e in complete]==['node.status','node.result']
    assert not any(e['kind']=='scope.set'for e in complete)
    assert release[0]['kind']=='scope.set'and release[0]['node_ids']==[]


def test_retrospective_receipt_keeps_explicit_registration_basis(tmp_path):
    event={'schema':'waypoint.event/1','event_id':'policy-fixture-retrospective','project_id':'policy-fixture','agent_id':'codex/verified-fixture','source':'evidence-registration','kind':'test.result','at':'2026-10-17T11:08:03+00:00','node_ids':['EXISTING-NODE'],'edge_ids':[],'payload':{'test_id':'EXISTING-TEST','run_id':'historical-run','outcome':'passed','freshness':'unknown','plan_version':'recorded-capture-version','evidence_levels':['source_inspection'],'evidence_refs':['immutable/historical-proof.json'],'registered_from_existing_evidence':True,'registration_method':'Retrospective registration; no new run or invented past timestamp'}}
    f=tmp_path/'events.json';f.write_text(json.dumps({'events':[event]}))
    emitted=signals(parser().parse_args(['--project','policy-fixture','emit',str(f)]))
    assert datetime.fromisoformat(emitted[0]['at'])==datetime.fromisoformat(event['at'])
    assert emitted[0]['payload']==event['payload']
    assert emitted[0]['payload']['evidence_levels']==['source_inspection']
