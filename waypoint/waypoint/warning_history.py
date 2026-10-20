"""Group repeated observations of one unresolved-input basis, retain raw history."""
import copy
import json
from .domain import digest


def _append(groups, warning):
    requirements = warning.get('requirements', [])
    key = sorted((r.get('edge_id'), r.get('requirement_fingerprint'),
                  r.get('availability'), digest(r.get('workspace_ref')),
                  tuple(sorted(r.get('receipts', [])))) for r in requirements)
    identity = digest([warning.get('node_id'), key])
    created = not groups or groups[-1]['basis_identity'] != identity
    if created:
        groups.append({'incident_id': 'dependency-' + digest([identity, warning['seq']])[:20],
            'basis_identity': identity, 'first_seq': warning['seq'],
            'first_observed_at': warning.get('observed_at'),
            'requirements': requirements, 'receipt_count': 0, 'agent_ids': [],
            'meaning': 'Consecutive observations of the same unresolved input and evidence basis; not a count of independent starts.'})
    group = groups[-1]
    group.update(last_seq=warning['seq'], last_observed_at=warning.get('observed_at'))
    group['receipt_count'] += 1
    if warning.get('agent_id') and warning['agent_id'] not in group['agent_ids']:
        group['agent_ids'].append(warning['agent_id'])
    return created

def dependency_incidents(warnings):
    groups = []
    for warning in sorted(warnings, key=lambda value: value['seq']):
        _append(groups, warning)
    return list(reversed(groups))


def dependency_history(store, project, node):
    """Incremental metadata summary; bounded response, raw ledger remains intact.

    First access streams the derived history in pages. Later state/packet reads
    inspect one indexed watermark and decode only newly appended warnings.
    Rebuild explicitly invalidates this per-Store cache.
    """
    cache = getattr(store, '_dependency_history_cache', None)
    if cache is None:
        store._dependency_history_cache = cache = {}
    latest = store.db.execute('SELECT seq FROM dependency_starts WHERE project=? AND node=? ORDER BY seq DESC LIMIT 1', (project, node)).fetchone()
    watermark = latest[0] if latest else 0
    key = (project, node)
    current = cache.get(key)
    if current is None or watermark < current['seq']:
        current = cache[key] = {'seq': 0, 'count': 0, 'periods': 0, 'groups': [], 'raw': []}
    while current['seq'] < watermark:
        rows = store.db.execute('SELECT body FROM dependency_starts WHERE project=? AND node=? AND seq>? ORDER BY seq LIMIT 200', (project, node, current['seq'])).fetchall()
        if not rows:
            break
        for row in rows:
            warning = json.loads(row[0])
            current['periods'] += int(_append(current['groups'], warning))
            current['groups'] = current['groups'][-20:]
            current['raw'] = [*current['raw'][-19:], warning]
            current['count'] += 1
            current['seq'] = warning['seq']
    return copy.deepcopy({'dependency_warnings': list(reversed(current['raw'])),
        'dependency_incidents': list(reversed(current['groups'])),
        'dependency_warning_count': current['count'],
        'dependency_incident_count': current['periods'],
        'dependency_incidents_has_more': current['periods'] > len(current['groups'])})
