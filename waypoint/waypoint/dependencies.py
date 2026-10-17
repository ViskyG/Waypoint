"""The common, pure prerequisite resolver used by packets, views and authoring.

Availability is reported evidence, never permission to run and never node status.
"""
from __future__ import annotations

from .domain import ContractError, digest


def ancestry(plan: dict, node_id: str) -> list[str]:
    chain, seen = [], set()
    while node_id is not None:
        if node_id in seen:
            raise ContractError("parent_cycle", "Nesting cycle", {"node_id": node_id})
        if node_id not in plan["nodes"]:
            raise ContractError("missing_parent", "Unknown block or parent", {"node_id": node_id})
        seen.add(node_id)
        chain.append(node_id)
        node_id = plan["nodes"][node_id].get("parent")
    return chain


def condition_fingerprint(plan: dict, edge_id: str, consumer_id: str) -> str:
    edge = plan["edges"][edge_id]
    spec = edge["x_observability"]
    condition = spec["condition"]
    output = plan["nodes"][edge["from"]].get("x_observability", {}).get("outputs", {}).get(condition["output_id"])
    if output is None:
        raise ContractError("missing_output", "Required producer output is not declared", {"edge_id": edge_id})
    if output["revision"] != condition["revision"]:
        raise ContractError("output_revision_mismatch", "Required output revision does not match", {"edge_id": edge_id})
    # Hash semantics, not explanatory text, rendering or unknown extension keys.
    return digest({"from": edge["from"], "declared_target": edge["to"], "consumer": consumer_id,
        "phase": spec["phase"], "target_scope": spec["target_scope"],
        "condition": {key: condition[key] for key in ("output_id", "revision", "workspace")},
        "definition": " ".join(output["definition"].split())})


def effective_relations(plan: dict, node_id: str, phase: str = "start") -> list[dict]:
    """Retain true endpoints and order/legacy context alongside hard requirements."""
    if phase not in {"start", "finish"}:
        raise ContractError("invalid_phase", "Phase must be start or finish")
    chain = set(ancestry(plan, node_id))
    result = []
    for edge_id, edge in sorted(plan.get("edges", {}).items()):
        if edge["to"] not in chain:
            continue
        spec = edge.get("x_observability")
        inherited = edge["to"] != node_id
        base = {"edge_id": edge_id, "producer_id": edge["from"], "declared_target_id": edge["to"],
                "consumer_id": node_id, "phase": phase, "inherited": inherited}
        if spec is None:
            # Unknown inheritance is visible context, never implicit readiness.
            result.append({**base, "classification": "legacy_unknown", "requirement_fingerprint": None})
            continue
        if spec["phase"] != phase or (inherited and spec["target_scope"] != "subtree"):
            continue
        record = {**base, "classification": spec["relation"], "target_scope": spec["target_scope"], "why": spec["why"]}
        if spec["relation"] == "requires":
            condition = spec["condition"]
            record.update(output_id=condition["output_id"], condition_revision=condition["revision"],
                workspace_policy=condition["workspace"],
                requirement_fingerprint=condition_fingerprint(plan, edge_id, node_id))
        else:
            record["requirement_fingerprint"] = None
        result.append(record)
    return result


def effective_requirements(plan: dict, node_id: str, phase: str = "start") -> list[dict]:
    return [record for record in effective_relations(plan, node_id, phase) if record["classification"] != "order"]


def expanded_cycles(plan: dict) -> list[str]:
    """Actual cycle members after subtree expansion (not downstream bystanders)."""
    adjacency = {node: set() for node in plan["nodes"]}
    reverse = {node: set() for node in plan["nodes"]}
    for node in plan["nodes"]:
        for phase in ("start", "finish"):
            for requirement in effective_requirements(plan, node, phase):
                if requirement["classification"] == "requires":
                    producer = requirement["producer_id"]
                    adjacency[producer].add(node)
                    reverse[node].add(producer)
    seen, finished = set(), []
    # Iterative Kosaraju avoids recursion limits on deeply nested authored plans.
    for root in adjacency:
        if root in seen:
            continue
        stack = [(root, False)]
        while stack:
            node, done = stack.pop()
            if done:
                finished.append(node)
                continue
            if node in seen:
                continue
            seen.add(node)
            stack.append((node, True))
            stack.extend((target, False) for target in adjacency[node] if target not in seen)
    seen, cyclic = set(), set()
    for root in reversed(finished):
        if root in seen:
            continue
        component, pending = set(), [root]
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            component.add(node)
            pending.extend(reverse[node] - seen)
        if len(component) > 1 or root in adjacency[root]:
            cyclic.update(component)
    return sorted(cyclic)


def _observation(record: dict) -> dict:
    if "payload" not in record:
        return record
    return {**record["payload"], **{key: record.get(key) for key in ("event_id", "source", "seq", "at", "agent_id")}}


def evaluate_availability(requirement: dict, observations: list[dict], workspace_ref=None) -> dict:
    """Evaluate receipt-ordered reporter statements under an explicit workspace.

    workspace_ref may be a single explicit ref or a mapping with consumer/project
    refs. No known consumer base means unknown. Supersession refers only to earlier
    applicable receipts; different current reporters do not use timestamp-wins.
    """
    result = {"state": "unknown", "availability": "unknown", "reason": "no_current_matching_evidence",
              "receipts": [], "stale_receipts": []}
    fingerprint = requirement.get("requirement_fingerprint")
    if not fingerprint:
        result["reason"] = "unclassified_legacy_edge"
        return result
    policy = requirement.get("workspace_policy", "consumer")
    workspace = workspace_ref.get(policy) if isinstance(workspace_ref, dict) else workspace_ref
    candidates, stale = [], []
    for raw in observations:
        observation = _observation(raw)
        if observation.get("consumer_id") != requirement["consumer_id"]:
            continue
        if observation.get("edge_id") not in {None, requirement["edge_id"]}:
            continue
        reason = None
        if observation.get("requirement_fingerprint") != fingerprint:
            reason = "requirement_changed"
        elif not workspace:
            reason = "consumer_workspace_unknown" if policy == "consumer" else "project_workspace_unknown"
        elif observation.get("workspace_ref") != workspace:
            reason = "workspace_changed"
        if reason:
            stale.append({"event_id": observation.get("event_id"), "source": observation.get("source"),
                          "seq": observation.get("seq"), "reason": reason})
        else:
            candidates.append(observation)
    if not workspace:
        result["reason"] = "consumer_workspace_unknown" if policy == "consumer" else "project_workspace_unknown"
    current_by_source = {}
    by_id = {o["event_id"]: o for o in candidates}
    superseded = set()
    for observation in candidates:
        if not observation.get("basis", {}).get("ref") or not observation.get("source") or type(observation.get("seq")) is not int:
            raise ContractError("dependency_evidence", "Evidence needs basis, reporter and durable receipt sequence")
        if observation.get("availability") not in {"available", "missing", "waived"}:
            raise ContractError("invalid_availability", "Invalid dependency availability")
        if observation["availability"] == "waived" and not observation["basis"].get("explanation", "").strip():
            raise ContractError("waiver_needs_reason", "A waiver needs author identity and an explanation")
        for event_id in observation.get("supersedes", []):
            if event_id in by_id and by_id[event_id]["seq"] < observation["seq"]:
                superseded.add(event_id)
    for observation in sorted(candidates, key=lambda o: (o["seq"], o["event_id"])):
        if observation["event_id"] in superseded:
            stale.append({"event_id": observation["event_id"], "source": observation["source"],
                          "seq": observation["seq"], "reason": "explicitly_superseded"})
            continue
        previous = current_by_source.get(observation["source"])
        if previous:
            stale.append({"event_id": previous["event_id"], "source": previous["source"],
                          "seq": previous["seq"], "reason": "replaced_by_reporter"})
        current_by_source[observation["source"]] = observation
    current = list(current_by_source.values())
    result["stale_receipts"] = sorted(stale, key=lambda o: (o.get("seq") or 0, o.get("event_id") or ""))
    if current:
        claims = {o["availability"] for o in current}
        result["receipts"] = sorted(o["event_id"] for o in current)
        result["state"] = {"available": "satisfied", "missing": "missing", "waived": "waived"}[next(iter(claims))] if len(claims) == 1 else "conflict"
        result["availability"] = result["state"]
        result["reason"] = "matched_evidence" if len(claims) == 1 else "contradictory_reporters"
    return result


def prerequisite_view(plan: dict, node_id: str, observations: list[dict], workspace_ref=None) -> dict:
    """Shared composition convenience; all consumers receive identical records."""
    view = {"start": [], "finish": [], "order": []}
    for phase in ("start", "finish"):
        for requirement in effective_relations(plan, node_id, phase):
            if requirement["classification"] == "order":
                view["order"].append(requirement)
            else:
                view[phase].append({**requirement, **evaluate_availability(requirement, observations, workspace_ref)})
    return view
