#!/usr/bin/env python3
"""Prepare bounded, reviewed skill amendments; never publish/install/change input roots.

The supplied execution-skill base is newer than this machine's checked-out source.
Its adaptation is explicit and pinned to the exact inspected local blob below.
"""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
import subprocess
from pathlib import Path
from stage_skill_edits import blob, transform

ROOT = Path(__file__).resolve().parents[1]
# Exact base inspected at local agent-skills HEAD 8ce882054346cfbec7cc12046c4d09b74e7a44a9.
EXECUTION_PATH = 'skills/codex/execute-roadmap-efficiently/SKILL.md'


def prepare(project_root, skills_root, out):
    manifest = json.loads((ROOT/'skills/EDITS.json').read_text())
    reconciliation = json.loads((ROOT/'skills/RECONCILED_BASE.json').read_text())
    if out.exists(): raise ValueError('Output must be a new directory')
    roots = {'Waypoint': project_root.resolve(), 'agent-skills': skills_root.resolve()}
    for source_root in roots.values():
        if out.resolve() == source_root or source_root.is_relative_to(out.resolve()):
            raise ValueError('Output must not contain source repositories')
    staged = []
    for original in manifest['edits']:
        edit = dict(original)
        if edit['path'] == EXECUTION_PATH:
            edit.update(reconciliation['override'])
        source = (roots[edit['repository']]/edit['path']).resolve()
        if not source.is_relative_to(roots[edit['repository']]): raise ValueError('Source escapes root')
        if out.resolve() == source or source.is_relative_to(out.resolve()): raise ValueError('Output contains source')
        raw = source.read_bytes()
        if blob(raw) != edit['expected_git_blob']:
            raise ValueError('Base changed; review required: ' + str(source))
        old = raw.decode()
        new = transform(old, edit, (ROOT/'skills'/edit['section']).read_text())
        # The delta must be precisely supplied section plus one version substitution.
        if edit.get('insert_before') and new.count((ROOT/'skills'/edit['section']).read_text().strip()) != 1:
            raise ValueError('Section insertion mismatch')
        staged.append((edit, old, new))
    out.mkdir(parents=True)
    files = []
    for edit, old, new in staged:
        target = out/edit['repository']/edit['path']; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(new)
        patch = ''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+edit['path'],tofile='b/'+edit['path']))
        dest = out/'patches'/(edit['repository']+'__'+edit['path'].replace('/','__')+'.patch'); dest.parent.mkdir(exist_ok=True); dest.write_text(patch)
        files.append({'repository':edit['repository'],'path':edit['path'],'base_blob':blob(old.encode()),'candidate_blob':blob(new.encode()),'version_from':edit['version_from'],'version_to':edit['version_to']})
    report = {'state':'PREPARED_NOT_PUBLISHED_NOT_INSTALLED','source_repositories_modified':False,'reconciliation':reconciliation,'files':files,
              'translation_scope':'Global RU files are amendment fragments only; absent full translations remain absent. Project complete EN/RU candidates updated in pairs.',
              'runtime_activation':'Use new contracts only after /api/health advertises corresponding implemented capabilities.'}
    (out/'STAGING.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-root',type=Path,required=True);p.add_argument('--skills-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try: print(json.dumps(prepare(a.project_root,a.skills_root,a.out),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as e:p.exit(2,str(e)+'\n')
