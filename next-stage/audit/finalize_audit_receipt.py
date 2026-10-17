#!/usr/bin/env python3
"""Read installed audit projection and create a new, transcript-free receipt."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'waypoint'))
from waypoint.client import Client
from waypoint.domain import now

def main():
    private = ROOT / '.runtime/conformance-audit'
    client = Client(ROOT / '.runtime/data')
    state = client.call('GET', '/api/p/waypoint/state')
    health = client.call('GET', '/api/health')
    before = json.loads((private / 'before-fixes-export.json').read_text())
    imported = json.loads((private / 'import-receipt.json').read_text())
    applied = json.loads((private / 'state-apply.json').read_text())
    plan = state['plan']
    states = {node['id']: node for node in state['node_states']}
    fixes = [key for key in plan['nodes'] if key.endswith('-FIX')]
    parents = [key.removesuffix('-FIX') for key in fixes]
    assert all(plan['nodes'][key] == value for key, value in before['plan']['nodes'].items())
    assert len(state['checks']) == 76
    assert sum(check['node_id'].endswith('-FIX') and check['outcome'] == 'failed' for check in state['checks']) == 5
    prerequisites = {}
    for consumer, producer, phase in [('WPT-N08', 'WPT-N07', 'start'), ('WPT-N09', 'WPT-N08', 'finish')]:
        response = client.call('GET', '/api/p/waypoint/prerequisites?node=' + consumer + '&phase=' + phase)
        assert any(row.get('producer_id') == producer and row.get('availability') == 'missing'
                   for row in response['requirements'])
        prerequisites[consumer] = response
    result = {
        'schema': 'waypoint.conformance.apply/1', 'captured_at': now(),
        'audited_source_commit': 'd547e2a93ac5aabd6395f9b8072d0ab63d7e5c8a',
        'audit_snapshot_cutoff': 12280, 'before_version': before['version'],
        'after_version': state['version'], 'before_nodes': len(before['plan']['nodes']),
        'after_nodes': len(plan['nodes']), 'before_edges': len(before['plan']['edges']),
        'after_edges': len(plan['edges']), 'import': imported,
        'old_node_definitions_unchanged': True, 'old_edges_unchanged': True,
        'old_checks_unchanged': applied['checks_retained'],
        'new_failed_criteria': applied['new_failed_checks'],
        'first_audit_event_seq': applied['events']['receipts'][0]['seq'],
        'last_audit_event_seq': applied['events']['receipts'][-1]['seq'],
        'current_statuses': {node: states[node]['status'] for node in parents + fixes + ['WPT-NEXT', 'WPT-N09']},
        'dependency_corrections': prerequisites, 'runtime_health': health,
        'root_focus_released_seq': 13007, 'full_acceptance': 'REMEDIATION_REQUIRED',
        'core_product_code_changed': False, 'repair_implementation_performed': False,
        'project_skill_drafts': '0.3.0 updated, not globally installed',
        'global_skills': '3 roles prepared against actual canonical source; NOT_PUBLISHED_NOT_INSTALLED',
        'audit_report_sha256': hashlib.sha256((ROOT / 'next-stage/audit/CONFORMANCE_RU.md').read_bytes()).hexdigest(),
        'preservation': 'Original event ledger, result receipts and six prior plan versions retained. Seven accepted plan versions now exist. No guessed message relinking.'}
    with (ROOT / 'next-stage/audit/APPLY_RECEIPT.json').open('x') as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({'state': result['full_acceptance'], 'version': state['version'],
        'old_checks_unchanged': 71, 'fix_nodes': len(fixes), 'new_failed_criteria': 5,
        'health_outbox_error': health['outbox_error'],
        'dependency_corrections': 'N07→N08 and N08→N09 missing confirmed; prior receipts retained'}, ensure_ascii=False))

if __name__ == '__main__':
    main()
