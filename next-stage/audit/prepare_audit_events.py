#!/usr/bin/env python3
"""Prepare explicit audit results; submission remains a separate reviewed step."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'waypoint'))
from waypoint.dependencies import effective_requirements
from waypoint.domain import digest, now, validate_event
from waypoint.read_models import workspace_basis
from prepare_fix_plan import FIXES

def prepare(document, actor):
    plan, version = document['plan'], document['version']
    ref = 'next-stage/audit/CONFORMANCE_RU.md'
    revision = 'sha256:' + hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()
    events = []
    timestamp = now()
    def add(kind, nodes, payload, source='conformance-audit'):
        events.append(validate_event({
            'event_id': 'audit-' + digest([version, revision, kind, nodes, payload])[:40],
            'project_id': plan['project_id'], 'agent_id': actor, 'source': source,
            'kind': kind, 'at': timestamp, 'node_ids': nodes, 'payload': payload}))
    for nid, parent, title, findings, owned, tests in FIXES:
        add('node.status', [parent], {'status': 'Требуются исправления',
            'explanation': 'Аудит: ' + ', '.join(findings) + '. Рабочие части и прежние проверки сохранены; полная приёмка открыта.'})
        add('node.result', [parent], {'summary': 'Аудит выявил расхождения; ремонт: ' + nid,
            'evidence_ref': ref, 'evidence_revision': revision, 'plan_version': version,
            'audit_findings': findings, 'full_acceptance': 'remediation_required',
            'prior_results_retained_in_ledger': True})
        add('node.status', [nid], {'status': 'not_started', 'explanation': 'Ремонт запланирован по аудиту; реализация не начиналась.'})
        add('node.result', [nid], {'summary': 'Подтверждены находки ' + ', '.join(findings) + '; исправления ещё не реализованы.',
            'evidence_ref': ref, 'evidence_revision': revision, 'plan_version': version,
            'implementation_state': 'PLANNED_NOT_EXECUTED'})
    add('node.status', ['WPT-NEXT'], {'status': 'Частичная приёмка; требуется ремонт',
        'explanation': 'Открыты шесть FIX и N09. Сохранённые зелёные критерии не означают полноту контрактов.'})
    for node, test, basis in [
        ('WPT-N04-FIX', 'T01', 'SYNTHETIC actual HTTP/Chromium: CONTRACT-F01; corrected msg-5 omitted by API, retained by old browser window.'),
        ('WPT-N02-FIX', 'T01', 'SYNTHETIC actual HTTP/Chromium: CONTRACT-F02; raw ORDER exists, shared projection/Plan omit order context.'),
        ('WPT-N02-FIX', 'T02', 'SYNTHETIC actual HTTP: CONTRACT-F03; requested override-base, response basis.consumer=plan-default.'),
        ('WPT-N03-FIX', 'T01', 'SYNTHETIC actual HTTP: CONTRACT-F04; connected from 2020 remains connected in catalogue.'),
        ('WPT-N07-FIX', 'T01', 'ACTUAL historical SQLite receipts/current file bytes: WF-04; N07 artifact SHA256 differs from current unsuperseded receipt.')]:
        add('test.result', [node], {'test_id': test, 'run_id': 'conformance-20261017',
            'outcome': 'failed', 'freshness': 'current',
            'basis': basis + ' See ' + ref + '; source commit d547e2a93ac5aabd6395f9b8072d0ab63d7e5c8a. Audit registration, not a remediation run.'})
    # Do not invalidate availability merely because a producer has a non-done
    # status. These two specific full/pinned claims lack their required part.
    for consumer in plan['nodes']:
        for phase in ('start', 'finish'):
            for req in effective_requirements(plan, consumer, phase):
                if req['classification'] != 'requires' or req['producer_id'] not in {'WPT-N07', 'WPT-N08'}:
                    continue
                workspace = workspace_basis(plan, consumer).get(req['workspace_policy'])
                if not workspace:
                    raise ValueError('Explicit workspace required')
                explanation = ('N07 current pinned proof does not match artifact bytes; reviewed immutable replacement is missing.'
                    if req['producer_id'] == 'WPT-N07' else
                    'N08 full target acceptance is missing because CONTRACT-F01–F07 remain open.')
                add('dependency.observation', [consumer], {'edge_id': req['edge_id'],
                    'consumer_id': consumer, 'requirement_fingerprint': req['requirement_fingerprint'],
                    'workspace_ref': workspace, 'availability': 'missing',
                    'basis': {'kind': 'artifact', 'ref': ref, 'revision': revision,
                        'explanation': explanation + ' Existing source files remain present. Reviewed correction of stage2 acceptance, not inferred from status.'},
                    'occurred_at': timestamp}, source='stage2-acceptance')
    return {'events': events}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, required=True)
    parser.add_argument('--actor', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    bundle = prepare(json.loads(args.export.read_text()), args.actor)
    with args.out.open('x') as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
        f.write('\n')
    args.out.chmod(0o600)
    print(json.dumps({'prepared_events': len(bundle['events']), 'submitted': False}))
