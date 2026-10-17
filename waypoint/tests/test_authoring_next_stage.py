"""Portable authoring and bounded migration tests; do not write a live service."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from waypoint.domain import validate_plan

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('prepare_authoring_revision',ROOT/'next-stage/tools/prepare_authoring_revision.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_second_project_template_roundtrip_and_policy():
    plan=json.loads((ROOT/'next-stage/authoring/PROJECT.plan.json').read_text())
    actual,warnings=validate_plan(plan)
    assert actual==plan
    assert actual['project_id']!='waypoint'
    assert actual['x_roadmap']['resource_policy']=='UNSELECTED'
    assert all(not key.startswith('WPT-') for key in actual['nodes'])
    assert not actual['x_observability']['algorithms']
    assert actual['edges']['E-01']['x_observability']['condition']['output_id']=='DELIVERABLE'


def test_backfill_preserves_history_fields_and_existing_intent():
    plan=json.loads((ROOT/'roadmap/ROADMAP.plan.json').read_text())
    plan['x_foreign']={'unknown':['keep']}
    plan['nodes']['WPT-C01']['x_observability']={'intent':{'summary':'Owner text','context':'Keep context','change':'Keep change'}}
    original=copy.deepcopy(plan)
    result=module.prepare({'plan':plan,'version':'v-fixture'})
    assert plan==original
    assert result['base_version']=='v-fixture'
    assert result==module.prepare({'plan':plan,'version':'v-fixture'})
    assert result['plan']['x_foreign']==original['x_foreign']
    for key,node in original['nodes'].items():
        assert result['plan']['nodes'][key]['assignment']==node['assignment']
        assert result['plan']['nodes'][key].get('layout')==node.get('layout')
        assert result['plan']['nodes'][key]['x_observability']['intent']
    assert result['plan']['nodes']['WPT-C01']['x_observability']['intent']['summary']=='Owner text'
    expected=(set(original.get('x_observability',{}).get('algorithms',{}))-set(module.ALIASES))|set(module.ALIASES.values())
    assert set(result['plan']['x_observability']['algorithms'])==expected
    assert not set(module.ALIASES)&set(result['plan']['x_observability']['algorithms'])
    validate_plan(result['plan'])
    assert 'events' not in result and 'status' not in result['plan']['x_observability']


def test_curated_inventory_carries_no_fake_run_or_installed_claim():
    for definition in module.inventory(ROOT).values():
        assert definition['implementation']['revision'].startswith('worktree-sha256:')
        assert 'correctness' not in definition and 'measurement' not in definition
        assert 'installed' not in definition
        assert definition['testability']['test_refs']


def test_supplied_algorithm_identities_reconciled_and_aliases_deduplicated():
    plan=json.loads((ROOT/'next-stage/roadmap/ROADMAP.plan.json').read_text())
    supplied=copy.deepcopy(plan['x_observability']['algorithms'])
    # Reproduce the accidentally imported helper revision, with genuine unrelated
    # and unknown extension data that must survive the bounded correction.
    plan['x_observability']['algorithms'].update(module._legacy_inventory(ROOT))
    plan['x_observability']['algorithms']['ALG-MERGE']['x_owner']={'keep':'unknown'}
    plan['x_observability']['algorithms']['ALG-MERGE']['implementation']['x_source']='keep nested'
    plan['x_observability']['algorithms']['ALG-MERGE']['implementation']['refs'][0]['x_ref']='keep ref'
    plan['x_observability']['algorithms']['UNRELATED']=copy.deepcopy(supplied['ALG-MERGE'])
    plan['x_observability']['algorithms']['UNRELATED']['id']='UNRELATED'
    plan['nodes']['WPT-N05']['x_observability']['algorithm_refs']=['ALG-MERGE','plan-three-way-merge','ALG-READ','anchored-message-reconciliation','UNRELATED']
    original=copy.deepcopy(plan)
    result=module.prepare({'plan':plan,'version':'v-duplicate-fixture'})['plan']
    actual=result['x_observability']['algorithms']
    assert plan==original
    assert set(actual)=={'ALG-MERGE','ALG-DEPS','ALG-PAGE','ALG-READ','UNRELATED'}
    assert actual['UNRELATED']==original['x_observability']['algorithms']['UNRELATED']
    for aid in module.ALIASES.values():
        assert actual[aid]['id']==aid
        assert actual[aid]['title']==supplied[aid]['title']
        assert actual[aid]['purpose']==supplied[aid]['purpose']
        assert actual[aid]['definition_revision']==2
        assert actual[aid]['x_authoring_reconciliation']['from_revision']==1
        assert actual[aid]['x_authoring_reconciliation']['to_revision']==2
    assert actual['ALG-MERGE']['x_owner']=={'keep':'unknown'}
    assert actual['ALG-MERGE']['implementation']['x_source']=='keep nested'
    assert actual['ALG-MERGE']['implementation']['refs'][0]['x_ref']=='keep ref'
    refs=result['nodes']['WPT-N05']['x_observability']['algorithm_refs']
    assert len(refs)==len(set(refs))
    assert not set(refs)&set(module.ALIASES)
    assert 'UNRELATED' in refs
    # A fresh export of the corrected unchanged source is idempotent, including
    # definition revisions and recorded reconciliation provenance.
    again=module.prepare({'plan':result,'version':'v-corrected-fixture'})['plan']
    assert again==result
    validate_plan(result)


def test_non_helper_alias_is_not_silently_deleted():
    plan=json.loads((ROOT/'next-stage/roadmap/ROADMAP.plan.json').read_text())
    aliases=module._legacy_inventory(ROOT)
    aliases['plan-three-way-merge']['purpose']='Owner changed this alias meaning'
    plan['x_observability']['algorithms'].update(aliases)
    import pytest
    with pytest.raises(ValueError,match='non-helper changes'):
        module.prepare({'plan':plan,'version':'v-owner-fixture'})


def test_skill_candidates_are_bounded_source_preserving():
    manifest=json.loads((ROOT/'next-stage/skills/candidates/STAGING.json').read_text())
    assert manifest['state']=='PREPARED_NOT_PUBLISHED_NOT_INSTALLED'
    assert len(manifest['files'])==7
    for entry in manifest['files']:
        candidate=ROOT/'next-stage/skills/candidates'/entry['repository']/entry['path']
        assert candidate.exists()
        section_file=next(e['section'] for e in json.loads((ROOT/'next-stage/skills/EDITS.json').read_text())['edits'] if e['path']==entry['path'])
        section=(ROOT/'next-stage/skills'/section_file).read_text().strip()
        assert candidate.read_text().count(section)==1
        if entry['repository']=='Waypoint':
            # Historical0.2 proposals stay pinned to supplied0.1 sources, not mutable project drafts.
            relative=Path(entry['path']).relative_to('waypoint/skills')
            source=(ROOT/'next-stage/sources/project-skills'/relative).read_text()
            import hashlib
            raw=source.encode()
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==entry['base_blob']
            marker=('version: "'+entry['version_from']+'"') if entry['path'].endswith('/SKILL.md') else 'версии '+entry['version_from']
            replacement=('version: "'+entry['version_to']+'"') if entry['path'].endswith('/SKILL.md') else 'версии '+entry['version_to']
            restored=candidate.read_text().replace(section,'').rstrip()+'\n'
            assert restored==source.replace(marker,replacement).rstrip()+'\n'
