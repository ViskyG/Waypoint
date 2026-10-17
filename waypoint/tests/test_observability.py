"""Synthetic contract checks; these are not live Codex evidence."""
import copy
from pathlib import Path
import json
import pytest
from waypoint.domain import ContractError
from waypoint.observability import validate_profile, validate_observation, profile_schema


def profile_fixture():
    return {"schema": "waypoint.plan/1", "project_id": "synthetic", "title": "Synthetic contract",
        "x_observability": {"schema": "waypoint.observability/1", "algorithms": {}, "purpose": "Exercise contracts"},
        "nodes": {key: {"title": key, "parent": parent, "assignment": "Executor detail",
            "x_observability": {"intent": {"summary": key, "context": "Synthetic", "change": "Test"},
                "outputs": {"OUT": {"definition": "Prepared input", "revision": 1}}, "algorithm_refs": []}}
            for key, parent in [("A", None), ("B", None), ("CHILD", "B")]},
        "edges": {"NEEDS": {"from": "A", "to": "B", "x_observability": {
            "relation": "requires", "phase": "start", "target_scope": "subtree", "why": "Needs input",
            "condition": {"output_id": "OUT", "revision": 1, "workspace": "consumer"}}}}}


def observation_fixture():
    return {"event_id": "obs1", "source": "synthetic", "kind": "dependency.observation",
        "payload": {"edge_id": "NEEDS", "consumer_id": "B", "requirement_fingerprint": "a" * 64,
        "workspace_ref": "workspace-A", "availability": "available", "occurred_at": "2026-10-17T10:00:00Z",
        "basis": {"kind": "artifact", "ref": "synthetic-artifact", "explanation": "Synthetic test fixture"}}}


def test_unknown_extensions_preserved_and_executor_assignment_untouched():
    p = profile_fixture()
    p["x_unknown"] = {"private": [1, 2]}
    p["nodes"]["A"]["x_observability"]["new_extension"] = {"future": True}
    before = copy.deepcopy(p)
    assert validate_profile(p) == []
    assert p == before


def test_legacy_missing_intent_is_explicit_and_not_fabricated():
    p = profile_fixture()
    del p["x_observability"]
    for n in p["nodes"].values():
        del n["x_observability"]
    del p["edges"]["NEEDS"]["x_observability"]
    warnings = validate_profile(p)
    assert {w["code"] for w in warnings} == {"legacy_profile_missing", "intent_missing"}
    assert "x_observability" not in p["nodes"]["A"]


@pytest.mark.parametrize("change,code", [
    (lambda p: p["nodes"]["A"]["x_observability"].update(algorithm_refs=["MISSING"]), "missing_algorithm"),
    (lambda p: p["edges"]["NEEDS"]["x_observability"]["condition"].update(output_id="absent"), "missing_output"),
    (lambda p: p["edges"]["NEEDS"]["x_observability"]["condition"].update(revision=2), "output_revision_mismatch"),
    (lambda p: p["edges"]["NEEDS"]["x_observability"].update(relation="order"), "order_condition"),
    (lambda p: p["nodes"]["A"]["x_observability"]["outputs"]["OUT"].update(revision=True), "profile_revision"),
])
def test_claimed_profile_error_has_precise_path(change, code):
    p = profile_fixture()
    change(p)
    with pytest.raises(ContractError) as failure:
        validate_profile(p)
    assert failure.value.code == code
    assert failure.value.detail["path"]


def test_schema_constructor_matches_stage_profile():
    from jsonschema import Draft202012Validator
    schema = profile_schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    p = profile_fixture()
    validator.validate(p)
    root = Path(__file__).resolve().parents[2]
    stage = json.loads((root / "next-stage/roadmap/ROADMAP.plan.json").read_text())
    assert validate_profile(stage) == []
    validator.validate(stage)


def test_dependency_observation_validation_and_waiver_identity():
    event = observation_fixture()
    validate_observation(event)
    event["payload"].update(availability="waived")
    with pytest.raises(ContractError, match="waiver"):
        validate_observation(event)
    event["payload"]["basis"]["kind"] = "waiver"
    validate_observation(event)
    event["payload"]["basis"]["explanation"] = " "
    with pytest.raises(ContractError):
        validate_observation(event)


@pytest.mark.parametrize("field,value", [("requirement_fingerprint", "bad"), ("occurred_at", "2026-10-17")])
def test_observation_rejects_invalid_basis_fields(field, value):
    event = observation_fixture()
    event["payload"][field] = value
    with pytest.raises(ContractError):
        validate_observation(event)
