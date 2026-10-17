"""Pure synthetic prerequisite regressions, shared across all consumers."""
import copy
import pytest
from waypoint.domain import ContractError
from waypoint.dependencies import (effective_requirements, effective_relations, condition_fingerprint,
    evaluate_availability, expanded_cycles, prerequisite_view)
from waypoint.observability import validate_profile
from test_observability import profile_fixture


def observation(requirement, *, availability="available", source="synthetic", seq=1, workspace="base1", **extra):
    return {"event_id": f"{source}-{seq}", "source": source, "seq": seq,
        "edge_id": requirement["edge_id"], "consumer_id": requirement["consumer_id"],
        "requirement_fingerprint": requirement["requirement_fingerprint"], "workspace_ref": workspace,
        "availability": availability, "basis": {"ref": "synthetic-result", "explanation": "Synthetic receipt"}, **extra}


def test_one_resolver_inherits_actual_ancestor_and_preserves_true_endpoints():
    p = profile_fixture()
    r = effective_requirements(p, "CHILD")[0]
    assert (r["producer_id"], r["declared_target_id"], r["consumer_id"], r["inherited"]) == ("A", "B", "CHILD", True)
    assert prerequisite_view(p, "CHILD", [], "base1")["start"][0]["requirement_fingerprint"] == r["requirement_fingerprint"]
    p["edges"]["NEEDS"]["x_observability"]["target_scope"] = "node"
    assert effective_requirements(p, "CHILD") == []
    p["nodes"]["B.dot"] = {"title": "ID is not ancestry", "parent": None}
    assert effective_requirements(p, "B.dot") == []


def test_order_is_visible_but_not_a_hard_requirement_and_finish_is_separate():
    p = profile_fixture()
    edge = p["edges"]["NEEDS"]["x_observability"]
    edge["phase"] = "finish"
    assert effective_requirements(p, "CHILD", "start") == []
    assert len(effective_requirements(p, "CHILD", "finish")) == 1
    edge["relation"] = "order"
    del edge["condition"]
    assert effective_requirements(p, "CHILD", "finish") == []
    assert effective_relations(p, "CHILD", "finish")[0]["classification"] == "order"


def test_legacy_ancestor_context_is_unknown_and_status_never_satisfies():
    p = profile_fixture()
    p["nodes"]["A"]["status"] = "done"
    r = effective_requirements(p, "CHILD")[0]
    assert evaluate_availability(r, [], "base1")["state"] == "unknown"
    del p["edges"]["NEEDS"]["x_observability"]
    r = effective_requirements(p, "CHILD")[0]
    assert r["classification"] == "legacy_unknown"
    assert evaluate_availability(r, [], "base1")["reason"] == "unclassified_legacy_edge"


def test_definition_changes_invalidate_but_whitespace_layout_and_intent_do_not():
    p = profile_fixture()
    first = condition_fingerprint(p, "NEEDS", "CHILD")
    p["nodes"]["A"]["layout"] = {"x": 90, "y": 400}
    p["nodes"]["A"]["x_observability"]["intent"]["summary"] = "Another explanation"
    p["edges"]["NEEDS"]["x_observability"]["why"] = "Another reason"
    output = p["nodes"]["A"]["x_observability"]["outputs"]["OUT"]
    output["definition"] = "Prepared \n input  "
    assert first == condition_fingerprint(p, "NEEDS", "CHILD")
    old = effective_requirements(p, "CHILD")[0]
    output["definition"] = "Different required meaning"
    r = effective_requirements(p, "CHILD")[0]
    state = evaluate_availability(r, [observation(old)], "base1")
    assert state["state"] == "unknown"
    assert state["stale_receipts"][0]["reason"] == "requirement_changed"


def test_workspace_basis_is_explicit_and_project_policy_has_its_own_scope():
    p = profile_fixture()
    r = effective_requirements(p, "CHILD")[0]
    o = observation(r)
    assert evaluate_availability(r, [o], "base2")["state"] == "unknown"
    assert evaluate_availability(r, [o], None)["reason"] == "consumer_workspace_unknown"
    assert evaluate_availability(r, [o], {"consumer": "base1", "project": "project1"})["state"] == "satisfied"
    p["edges"]["NEEDS"]["x_observability"]["condition"]["workspace"] = "project"
    r = effective_requirements(p, "CHILD")[0]
    o = observation(r, workspace="project1")
    assert evaluate_availability(r, [o], {"consumer": "base2", "project": "project1"})["state"] == "satisfied"
    assert evaluate_availability(r, [o], {"consumer": "base2"})["state"] == "unknown"


def test_reporters_conflict_until_explicit_reconciliation_not_clock_wins():
    r = effective_requirements(profile_fixture(), "CHILD")[0]
    a = observation(r, source="one", seq=1)
    b = observation(r, source="two", seq=2, availability="missing")
    result = evaluate_availability(r, [a, b], "base1")
    assert result["state"] == "conflict"
    assert result["receipts"] == ["one-1", "two-2"]
    c = observation(r, source="one", seq=3, supersedes=["two-2"])
    result = evaluate_availability(r, [a, b, c], "base1")
    assert result["state"] == "satisfied"
    assert result["receipts"] == ["one-3"]
    assert {o["reason"] for o in result["stale_receipts"]} == {"replaced_by_reporter", "explicitly_superseded"}


def test_same_reporter_replaces_statement_by_receipt_and_waiver_is_explicit():
    r = effective_requirements(profile_fixture(), "CHILD")[0]
    old = observation(r, seq=1)
    new = observation(r, seq=2, availability="missing", at="1900-01-01T00:00:00Z")
    assert evaluate_availability(r, [old, new], "base1")["state"] == "missing"
    waived = observation(r, seq=3, availability="waived")
    assert evaluate_availability(r, [old, new, waived], "base1")["state"] == "waived"
    waived["basis"]["explanation"] = " "
    with pytest.raises(ContractError):
        evaluate_availability(r, [waived], "base1")


def test_envelope_evidence_and_foreign_consumer_isolation():
    r = effective_requirements(profile_fixture(), "CHILD")[0]
    flat = observation(r)
    envelope = {"payload": {k: v for k, v in flat.items() if k not in {"source", "seq", "event_id"}},
                "source": "synthetic", "seq": 1, "event_id": "synthetic-1"}
    assert evaluate_availability(r, [envelope], "base1")["state"] == "satisfied"
    envelope["payload"]["consumer_id"] = "B"
    assert evaluate_availability(r, [envelope], "base1")["state"] == "unknown"


def test_expanded_hidden_self_cycle_rejected_but_no_parent_completion_invented():
    p = profile_fixture()
    assert expanded_cycles(p) == []
    assert {r["producer_id"] for r in effective_requirements(p, "CHILD")} == {"A"}
    p["edges"]["NEEDS"]["from"] = "CHILD"
    assert expanded_cycles(p) == ["CHILD"]
    with pytest.raises(ContractError) as failure:
        validate_profile(p)
    assert failure.value.code == "typed_dependency_cycle"


def test_cycle_members_exclude_downstream_and_legacy_cycle_remains_displayable():
    p = profile_fixture()
    p["edges"]["BACK"] = copy.deepcopy(p["edges"]["NEEDS"])
    p["edges"]["BACK"].update({"from": "B", "to": "A"})
    assert expanded_cycles(p) == ["A", "B"]
    for edge in p["edges"].values():
        del edge["x_observability"]
    assert expanded_cycles(p) == []
    assert validate_profile(p) == []


def test_frontier_uses_exact_resolver_and_explicit_receipts_never_completion_status():
    import importlib.util
    from pathlib import Path
    script = Path(__file__).resolve().parents[2] / "roadmap/tools/roadmap.py"
    spec = importlib.util.spec_from_file_location("roadmap_tool", script)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    p = profile_fixture()
    for n in p["nodes"].values():
        n["x_roadmap"] = {"kind": "packet"}
    r = effective_requirements(p, "CHILD")[0]
    assert "CHILD" not in tool.frontier(p, ["A"])["ready"]
    assert "CHILD" in tool.frontier(p, observations=[observation(r)], workspace_ref="base1")["ready"]
    wait = next(row for row in tool.frontier(p)["waiting"] if row["id"] == "CHILD")
    assert wait["prerequisites"][0]["requirement_fingerprint"] == r["requirement_fingerprint"]
    for node in p['nodes'].values():
        node.update(acceptance={}, tests={})
    text = tool.block_text(p, 'CHILD')
    assert 'A / OUT' in text and 'унаследовано через B' in text
