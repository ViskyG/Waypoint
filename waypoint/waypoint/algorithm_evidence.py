"""Read-only, revision-aware algorithm evidence. Never executes linked code."""
from __future__ import annotations

import copy
import math

from .domain import ContractError, canonical, descendants, ident


def algorithm_observation_schema() -> dict:
    """Portable payload contract matching validation below; unknown keys survive.

    JSON cannot represent NaN/infinity; runtime additionally rejects them in
    Python-origin measurements. Cross-revision comparability is a read projection.
    """
    from .domain import ID
    def obj(properties, required=()):
        return {'type':'object','properties':properties,'required':list(required),'additionalProperties':True}
    def text(maximum=16000):
        return {'type':'string','minLength':1,'maxLength':maximum,'pattern':r'\S'}
    def array(items, maximum=100):
        return {'type':'array','items':items,'maxItems':maximum}
    identity={'type':'string','pattern':ID.pattern}
    reference=obj({'path':text(2000),'symbol':text(500)},['path','symbol'])
    implementation=obj({'repository':text(2000),'revision':text(500),'refs':array(reference)},['repository','revision','refs'])
    correctness=obj({'outcome':{'enum':['passed','failed','not_run']},'evidence_refs':array(text(4000))},['outcome','evidence_refs'])
    correctness['allOf']=[{'if':{'properties':{'outcome':{'enum':['passed','failed']}}},
                           'then':{'properties':{'evidence_refs':{'minItems':1}}}}]
    measurement=obj({**{key:text(2000) for key in ('metric','unit','statistic','method','environment_ref','dataset_ref','workload_ref','semantic_revision')},
        'n':{'type':'integer','minimum':1},'value':{'type':'number'},'direction':{'enum':['lower','higher']}},
        ['metric','unit','statistic','method','environment_ref','dataset_ref','workload_ref','semantic_revision','n','value','direction'])
    comparison=obj({'baseline_observation_id':identity,'candidate_observation_id':identity,
                    'constraints':{'anyOf':[{'type':'object'},{'type':'array'}]},'claim':text()},
                   ['baseline_observation_id','candidate_observation_id','constraints','claim'])
    return obj({'algorithm_id':identity,'definition_revision':{'type':'integer','minimum':1},
                'implementation_ref':{'anyOf':[{'type':'null'},text(500),implementation]},
                'observation_kind':text(100),'correctness':correctness,
                'measurement':{'anyOf':[{'type':'null'},measurement]},
                'comparison':{'anyOf':[{'type':'null'},comparison]},'note':{'type':'string','maxLength':16000}},
               ['algorithm_id','definition_revision','observation_kind','correctness'])


def _fail(code, message):
    raise ContractError(code, message)


def _text(value, field, maximum=16000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        _fail('algorithm_observation', 'Invalid ' + field)


def validate_algorithm_observation(event: dict) -> dict:
    """Validate immutable payload; envelope validation remains in domain."""
    if event.get('kind') != 'algorithm.observation':
        return event
    p = event.get('payload', {})
    ident(p.get('algorithm_id'), 'algorithm_id')
    if type(p.get('definition_revision')) is not int or p['definition_revision'] < 1:
        _fail('algorithm_revision', 'definition_revision must be a positive integer')
    impl = p.get('implementation_ref')
    if impl is not None:
        if isinstance(impl, str):
            _text(impl, 'implementation_ref', 500)
        elif isinstance(impl, dict):
            _text(impl.get('repository'), 'implementation repository', 2000)
            _text(impl.get('revision'), 'implementation revision', 500)
            refs = impl.get('refs')
            if not isinstance(refs, list) or len(refs) > 100:
                _fail('algorithm_refs', 'Invalid implementation refs')
            for ref in refs:
                if not isinstance(ref, dict):
                    _fail('algorithm_refs', 'Invalid implementation reference')
                _text(ref.get('path'), 'path', 2000)
                _text(ref.get('symbol'), 'symbol', 500)
        else:
            _fail('algorithm_ref', 'Invalid implementation_ref')
    _text(p.get('observation_kind'), 'observation_kind', 100)
    c = p.get('correctness')
    if not isinstance(c, dict) or c.get('outcome') not in {'passed', 'failed', 'not_run'}:
        _fail('algorithm_correctness', 'Invalid correctness outcome')
    refs = c.get('evidence_refs')
    if not isinstance(refs, list) or len(refs) > 100 or any(not isinstance(r, str) or not r.strip() or len(r) > 4000 for r in refs):
        _fail('algorithm_evidence', 'Invalid correctness evidence refs')
    if c['outcome'] != 'not_run' and not refs:
        _fail('algorithm_evidence', 'Passed/failed correctness requires real evidence references')
    m = p.get('measurement')
    if m is not None:
        _validate_measurement(m)
    comparison = p.get('comparison')
    if comparison is not None:
        if not isinstance(comparison, dict):
            _fail('algorithm_comparison', 'comparison must be an object')
        for key in ('baseline_observation_id', 'candidate_observation_id'):
            ident(comparison.get(key), key)
        if not isinstance(comparison.get('constraints'), (dict, list)):
            _fail('algorithm_comparison', 'Comparison constraints must be recorded')
        _text(comparison.get('claim'), 'comparison claim')
    if not isinstance(p.get('note', ''), str) or len(p.get('note', '')) > 16000:
        _fail('algorithm_note', 'Invalid note')
    return copy.deepcopy(event)


def _validate_measurement(m):
    if not isinstance(m, dict):
        _fail('algorithm_measurement', 'measurement must be an object')
    for key in ('metric', 'unit', 'statistic', 'method', 'environment_ref', 'dataset_ref', 'workload_ref', 'semantic_revision'):
        _text(m.get(key), key, 2000)
    if type(m.get('n')) is not int or m['n'] < 1:
        _fail('algorithm_measurement', 'Sample count must be positive')
    if type(m.get('value')) not in (int, float) or not math.isfinite(m['value']):
        _fail('algorithm_measurement', 'Measurement must be finite')
    if m.get('direction') not in {'lower', 'higher'}:
        _fail('algorithm_measurement', 'Invalid measurement direction')


def compare_measurements(baseline: dict | None, candidate: dict | None, constraints=None) -> dict:
    """Compare one metric under identical recorded conditions, without global claims.

    Inputs are measurements plus a correctness string, or observation payloads.
    Environment compatibility is deliberately exact, rather than inferred.
    """
    def unpack(value):
        if value and 'measurement' in value:
            return {**(value.get('measurement') or {}), 'correctness': value.get('correctness', {}).get('outcome')}
        return value
    a, b = unpack(baseline), unpack(candidate)
    if not a or not b or 'value' not in a or 'value' not in b:
        return {'state': 'not_measured', 'reasons': ['measurement_absent']}
    # Validate structural values before they can participate in arithmetic.
    for m in (a, b):
        _validate_measurement(m)
    fields = ('metric', 'unit', 'statistic', 'method', 'environment_ref', 'dataset_ref', 'workload_ref', 'semantic_revision', 'direction')
    mismatch = [field for field in fields if a.get(field) != b.get(field)]
    if mismatch:
        return {'state': 'not_comparable', 'reasons': mismatch}
    if a.get('correctness') != 'passed' or b.get('correctness') != 'passed':
        return {'state': 'not_established', 'reasons': ['correctness_not_confirmed']}
    # Constraints are explicit observations, not executable predicates or prose parsing.
    if isinstance(constraints, dict):
        degraded = [str(key) for key, value in constraints.items() if value in ('failed', 'regressed', False)]
        if degraded:
            return {'state': 'regressed', 'reasons': ['constraint:' + key for key in degraded]}
        uncertain = [str(key) for key, value in constraints.items() if value not in ('passed', 'unchanged', True)]
        if uncertain:
            return {'state': 'not_established', 'reasons': ['constraint_unknown:' + key for key in uncertain]}
    elif constraints:
        return {'state': 'not_established', 'reasons': ['constraint_results_not_recorded']}
    av, bv = a['value'], b['value']
    better = bv < av if b['direction'] == 'lower' else bv > av
    return {'state': 'unchanged' if av == bv else 'improved' if better else 'regressed',
            'reasons': [], 'baseline': av, 'candidate': bv, 'unit': b['unit'],
            'n': {'baseline': a['n'], 'candidate': b['n']},
            'note': 'Single metric under matching recorded conditions; uncertainty not quantified; no claim of overall optimality.'}


def _freshness(definition, payload):
    reasons = []
    if payload.get('definition_revision') != definition.get('definition_revision'):
        reasons.append('definition_revision_changed')
    impl = definition.get('implementation')
    reference = payload.get('implementation_ref')
    same = canonical(impl) == canonical(reference)
    if isinstance(reference, str) and isinstance(impl, dict):
        same = reference == impl.get('revision')
    if not same:
        reasons.append('implementation_changed')
    return reasons


def algorithm_views(plan: dict, observations, node: str | None = None, deep: bool = False) -> list[dict]:
    definitions = plan.get('x_observability', {}).get('algorithms', {})
    nodes = plan.get('nodes', {})
    selected = (descendants(plan, node) | {node}) if node and deep else {node} if node else set(nodes)
    refs = {}
    for node_id in sorted(selected):
        for aid in nodes.get(node_id, {}).get('x_observability', {}).get('algorithm_refs', []):
            refs.setdefault(aid, []).append({'node_id': node_id, 'direct': node is None or node_id == node})
    events = [e for e in observations if e.get('kind') == 'algorithm.observation']
    result = []
    for aid, definition in sorted(definitions.items()):
        if node and aid not in refs:
            continue
        evidence = []
        for event in events:
            p = event.get('payload', {})
            if p.get('algorithm_id') != aid:
                continue
            reasons = _freshness(definition, p)
            evidence.append({k: copy.deepcopy(event[k]) for k in ('event_id', 'source', 'at', 'seq', 'payload') if k in event} |
                            {'freshness': 'stale' if reasons else 'current', 'stale_reasons': reasons})
        evidence.sort(key=lambda e: (e.get('seq', 0), e.get('at', ''), e['event_id']))
        current = [e for e in evidence if e['freshness'] == 'current']
        correctness = [e['payload']['correctness']['outcome'] for e in current if e['payload']['correctness']['outcome'] != 'not_run']
        # Contradictory results remain visible and never imply current success.
        tested = 'failed' if 'failed' in correctness else 'passed' if correctness else 'not_run'
        by_id = {e['event_id']: e for e in evidence}
        comparisons = []
        for event in evidence:
            cmp = event['payload'].get('comparison')
            if not cmp:
                continue
            a, b = by_id.get(cmp['baseline_observation_id']), by_id.get(cmp['candidate_observation_id'])
            if not a or not b:
                projection = {'state': 'not_comparable', 'reasons': ['observation_not_found']}
            else:
                # Old and new code are legitimate benchmark bases. Retain their exact
                # historical revisions; a compatible comparison is not a fresh test
                # of the current implementation merely because it is viewable.
                projection = compare_measurements(a['payload'], b['payload'], cmp.get('constraints'))
            comparisons.append({'event_id': event['event_id'], 'claim': cmp['claim'],
                                'freshness': event['freshness'],
                                'baseline_freshness': a['freshness'] if a else 'unknown',
                                'candidate_freshness': b['freshness'] if b else 'unknown', **projection})
        result.append({'id': aid, 'definition': copy.deepcopy(definition), 'associations': refs.get(aid, []),
                       'implemented': definition.get('implementation') is not None, 'tested': tested,
                       'measured': any(e['payload'].get('measurement') is not None for e in current),
                       'installed': any(e['payload'].get('observation_kind') == 'integration' and e['payload']['correctness']['outcome'] == 'passed' for e in current),
                       'evidence': evidence, 'comparisons': comparisons})
    return result
