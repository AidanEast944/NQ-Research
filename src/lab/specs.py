"""Experiment spec schema, validation and fingerprints. Pure functions, no I/O."""
import hashlib
import json

REQUIRED = ["id", "title", "hypothesis", "symbols", "discovery_data", "oos_data",
            "rules", "parameters", "declared_trials", "cost_model", "author"]


def _norm(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).lower()


def family_hash(spec):
    """Same idea (symbols + rules), ignoring parameter values."""
    return hashlib.sha256(_norm({"s": sorted(spec["symbols"]), "r": spec["rules"]}).encode()).hexdigest()[:16]


def fingerprint(spec):
    """Exact duplicate detector: symbols + rules + parameters + data windows."""
    payload = {"s": sorted(spec["symbols"]), "r": spec["rules"], "p": spec["parameters"],
               "d": spec["discovery_data"], "o": spec["oos_data"]}
    return hashlib.sha256(_norm(payload).encode()).hexdigest()[:16]


def spec_hash(spec):
    return hashlib.sha256(_norm(spec).encode()).hexdigest()[:16]


def validate_shape(spec, policy):
    """Return a list of problems (empty = ok)."""
    problems = []
    for k in REQUIRED:
        if k not in spec:
            problems.append(f"missing field: {k}")
    if problems:
        return problems
    if not isinstance(spec["symbols"], list) or not spec["symbols"]:
        problems.append("symbols must be a non-empty list")
    if not isinstance(spec["declared_trials"], int) or spec["declared_trials"] < 1:
        problems.append("declared_trials must be an integer >= 1")
    for w in ("discovery_data", "oos_data"):
        d = spec[w]
        if not (isinstance(d, dict) and "start" in d and "end" in d):
            problems.append(f"{w} needs start and end")
        elif d["start"] >= d["end"]:
            problems.append(f"{w}: start must be before end")
    if not problems:
        if spec["discovery_data"]["end"] >= spec["oos_data"]["start"]:
            problems.append("discovery_data must end before oos_data starts (no overlap)")
        cm, req = spec["cost_model"], policy["required_cost_model"]
        if (cm.get("slippage_points") != req["slippage_points"]
                or cm.get("commission_round_trip") != req["commission_round_trip"]):
            problems.append(f"cost_model must equal the project default {req}")
        if not spec["rules"]:
            problems.append("rules must be explicit and non-empty")
    return problems
