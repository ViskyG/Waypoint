"""Additive authored observability contracts; never infer evidence from status.

Schema constructors below also feed the portable contract generator. Unknown keys
are deliberately preserved; validation does not normalize or mutate the plan.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .domain import ContractError, ID


def _object(properties: dict, required=(), **limits) -> dict:
    return {"type": "object", "properties": properties, "required": list(required),
            "additionalProperties": True, **limits}


def _text(maximum=50_000):
    return {"type": "string", "minLength": 1, "maxLength": maximum}


def _array(items, maximum=1000, **extra):
    return {"type": "array", "items": items, "maxItems": maximum, **extra}


def _records(item, maximum=20_000):
    return {"type": "object", "maxProperties": maximum,
            "propertyNames": {"type": "string", "pattern": ID.pattern}, "additionalProperties": item}


def profile_schema() -> dict:
    """Full-plan additive profile schema, generated from the runtime field specs."""
    revision = {"type": "integer", "minimum": 1}
    ref = _object({"path": _text(2000), "symbol": _text(1000)}, ["path"])
    implementation = _object({"repository": _text(2000), "revision": _text(1000),
                              "refs": _array(ref, minItems=1)}, ["repository", "revision", "refs"])
    implementation["type"] = ["object", "null"]
    strings = _array(_text())
    algorithm = _object({"id": _text(200), "title": _text(500), "purpose": _text(),
        **{key: strings for key in ("inputs", "outputs", "steps", "invariants", "edge_cases", "resource_risks")},
        "definition_revision": revision, "implementation": implementation,
        "testability": _object({"strategy": _text(), "test_refs": _array(ref),
                                 "missing_cases": strings}, ["strategy", "test_refs", "missing_cases"])},
        ["id", "title", "purpose", "inputs", "outputs", "steps", "invariants", "edge_cases",
         "definition_revision", "implementation", "testability", "resource_risks"])
    intent = _object({key: _text() for key in ("summary", "context", "change", "scope")},
                     ["summary", "context", "change"])
    # An entirely empty object explicitly represents legacy/incomplete intent.
    node = _object({"x_observability": _object({
        "intent": {"anyOf": [intent, {"const": {}}]},
        "outputs": _records(_object({"definition": _text(), "revision": revision}, ["definition", "revision"])),
        "algorithm_refs": _array({"type": "string", "pattern": ID.pattern}, uniqueItems=True)})})
    relation = _object({"relation": {"enum": ["requires", "order"]},
        "phase": {"enum": ["start", "finish"]}, "target_scope": {"enum": ["node", "subtree"]},
        "why": _text(), "condition": _object({"output_id": {"type": "string", "pattern": ID.pattern},
            "revision": revision, "workspace": {"enum": ["consumer", "project"]}},
            ["output_id", "revision", "workspace"])}, ["relation", "phase", "target_scope", "why"])
    # Conditional constraints are shared by the runtime's semantic pass below.
    relation["allOf"] = [
        {"if": {"properties": {"relation": {"const": "requires"}}}, "then": {"required": ["condition"]}},
        {"if": {"properties": {"relation": {"const": "order"}}}, "then": {"not": {"required": ["condition"]}}}]
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Waypoint observability profile 1",
        **_object({"x_observability": _object({"schema": {"const": "waypoint.observability/1"},
            "purpose": _text(), "algorithms": _records(algorithm, 5000)}, ["schema", "algorithms"]),
            "nodes": _records(node), "edges": _records(_object({"x_observability": relation}), 100_000)})}


def _fail(code, path, message):
    raise ContractError(code, f"{path}: {message}", {"path": path})


def _validate(value: Any, schema: dict, path: str):
    """Small validator for our constructor vocabulary, no optional runtime deps."""
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            try:
                _validate(value, option, path)
                return
            except ContractError:
                pass
        _fail("profile_type", path, "does not match the supported field shape")
    if "const" in schema and value != schema["const"]:
        _fail("profile_value", path, "unsupported value")
    if "enum" in schema and value not in schema["enum"]:
        _fail("profile_value", path, "unsupported value")
    kind = schema.get("type")
    kinds = kind if isinstance(kind, list) else [kind]
    if value is None and "null" in kinds:
        return
    if "object" in kinds:
        if not isinstance(value, dict):
            _fail("profile_type", path, "must be an object")
        if len(value) > schema.get("maxProperties", 100_000):
            _fail("profile_bound", path, "too many properties")
        for required in schema.get("required", []):
            if required not in value:
                _fail("profile_required", path + "/" + required, "required field is missing")
        for key, item in value.items():
            if "propertyNames" in schema:
                _validate(key, schema["propertyNames"], path + " key")
            child = schema.get("properties", {}).get(key, schema.get("additionalProperties"))
            if isinstance(child, dict):
                _validate(item, child, path + "/" + str(key))
    elif kind == "array":
        if not isinstance(value, list):
            _fail("profile_type", path, "must be an array")
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", 1000):
            _fail("profile_bound", path, "invalid array length")
        if schema.get("uniqueItems") and len(set(map(repr, value))) != len(value):
            _fail("profile_duplicate", path, "duplicate entries")
        for i, item in enumerate(value):
            _validate(item, schema["items"], f"{path}/{i}")
    elif kind == "string":
        if not isinstance(value, str) or not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 2_000_000):
            _fail("profile_text", path, "must be bounded text")
        if schema.get("minLength") and not value.strip():
            _fail("profile_text", path, "must contain non-whitespace text")
        if "pattern" in schema and not ID.fullmatch(value):
            _fail("invalid_id", path, "invalid identifier")
    elif kind == "integer" and (type(value) is not int or value < schema.get("minimum", 0)):
        _fail("profile_revision", path, "must be a positive integer")


def validate_profile(plan: dict) -> list[dict]:
    _validate(plan, profile_schema(), "plan")
    warnings = []
    profile = plan.get("x_observability", {})
    if not profile:
        warnings.append({"code": "legacy_profile_missing", "message": "No authored observability profile"})
    algorithms = profile.get("algorithms", {})
    for key, definition in algorithms.items():
        if definition["id"] != key:
            _fail("algorithm_id_mismatch", f"algorithms/{key}/id", "must equal its dictionary key")
    for key, node in plan["nodes"].items():
        x = node.get("x_observability", {})
        if not x.get("intent"):
            warnings.append({"code": "intent_missing", "node_id": key,
                             "message": "Human intent is legacy or incomplete"})
        for ref in x.get("algorithm_refs", []):
            if ref not in algorithms:
                _fail("missing_algorithm", f"nodes/{key}/algorithm_refs", f"unknown algorithm {ref}")
    for key, edge in plan.get("edges", {}).items():
        spec = edge.get("x_observability")
        if spec is None:
            continue
        if spec["relation"] == "order":
            if "condition" in spec:
                _fail("order_condition", f"edges/{key}", "order must not declare a condition")
            continue
        condition = spec.get("condition")
        if condition is None:
            _fail("condition_required", f"edges/{key}", "requires must declare an output condition")
        producer = plan["nodes"].get(edge.get("from"))
        if producer is None or edge.get("to") not in plan["nodes"]:
            _fail("missing_endpoint", f"edges/{key}", "unknown endpoint")
        output = producer.get("x_observability", {}).get("outputs", {}).get(condition["output_id"])
        if output is None:
            _fail("missing_output", f"edges/{key}/condition", "producer does not declare this output")
        if output["revision"] != condition["revision"]:
            _fail("output_revision_mismatch", f"edges/{key}/condition/revision", "does not match the output revision")
    # Legacy cyclic arrows remain diagnostics in the native validator. Newly
    # declared hard cycles, including hidden subtree self-dependencies, are errors.
    from .dependencies import expanded_cycles
    cycles = expanded_cycles(plan)
    if cycles:
        raise ContractError("typed_dependency_cycle", "Expanded hard dependency graph contains a cycle", {"nodes": cycles})
    return warnings


def dependency_observation_schema() -> dict:
    return _object({"edge_id": {"type": "string", "pattern": ID.pattern},
        "consumer_id": {"type": "string", "pattern": ID.pattern},
        "requirement_fingerprint": _text(64), "workspace_ref": _text(2000),
        "availability": {"enum": ["available", "missing", "waived"]},
        "basis": _object({"kind": {"enum": ["artifact", "test", "executor_attestation", "waiver"]},
            "ref": _text(2000), "revision": _text(2000), "explanation": _text()},
            ["kind", "ref", "explanation"]), "occurred_at": {"type": "string", "format": "date-time"},
        "supersedes": _array({"type": "string", "pattern": ID.pattern}, uniqueItems=True)},
        ["edge_id", "consumer_id", "requirement_fingerprint", "workspace_ref", "availability", "basis", "occurred_at"])


def validate_observation(event: dict) -> None:
    if event.get("kind") != "dependency.observation":
        return
    p = event.get("payload")
    _validate(p, dependency_observation_schema(), "payload")
    fingerprint = p["requirement_fingerprint"]
    if len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint):
        _fail("requirement_fingerprint", "payload/requirement_fingerprint", "expected SHA-256 hex")
    try:
        ts = datetime.fromisoformat(p["occurred_at"].replace("Z", "+00:00"))
        if ts.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        _fail("timestamp", "payload/occurred_at", "expected ISO8601 timestamp with timezone")
    if p["availability"] == "waived":
        if p["basis"]["kind"] != "waiver" or not event.get("source"):
            _fail("waiver_identity", "payload/basis", "waiver requires author identity and waiver basis")
    elif p["basis"]["kind"] == "waiver":
        _fail("waiver_availability", "payload/basis", "waiver basis requires waived availability")
    if event.get("event_id") in p.get("supersedes", []):
        _fail("self_supersedes", "payload/supersedes", "observation cannot supersede itself")
