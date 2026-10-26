"""Policy guards: holdout, budget, weekly allowance. Deterministic; reads, never edits, the registry."""
import json
import os
from datetime import datetime, timedelta


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def holdout_problems(spec, policy):
    problems = []
    syms = [s.upper() for s in spec["symbols"]]
    held = [s for s in syms if s in policy["holdout_symbols"]]
    if held and not spec.get("holdout_confirmation"):
        problems.append(f"{held} is sealed holdout data; discovery specs may not use it. "
                        "Declare holdout_confirmation=true for the single final confirmation run.")
    if spec.get("holdout_confirmation") and not set(syms) <= set(policy["holdout_symbols"]):
        problems.append("a holdout_confirmation spec may name holdout symbols only")
    bad = [s for s in syms if s not in policy["holdout_symbols"] and s not in policy["discovery_symbols_allowed"]]
    if bad:
        problems.append(f"symbols not allowed by policy: {bad}")
    return problems


def remaining_budget(registry):
    used = registry["baseline_trials"] + sum(t["declared_trials"] for t in registry["tests"].values())
    return registry["trial_budget_total"] - used


def queued_trials(queue):
    return sum(q["spec"]["declared_trials"] for q in queue if q["status"] in ("queued", "approved"))


def week_start(now):
    d = now - timedelta(days=now.weekday())
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def weekly_used(queue, now):
    ws = week_start(now)
    return sum(q["spec"]["declared_trials"] for q in queue
               if q["status"] in ("queued", "approved", "registered")
               and datetime.fromisoformat(q["submitted_at"]) >= ws)


def budget_problems(spec, registry, queue, policy, now=None):
    now = now or datetime.now()
    problems = []
    n = spec["declared_trials"]
    rem = remaining_budget(registry) - queued_trials(queue)
    if n > rem:
        problems.append(f"declared_trials {n} exceeds remaining unreserved budget {rem}")
    cap = policy["weekly_trial_allowance"]
    used = weekly_used(queue, now)
    if used + n > cap:
        problems.append(f"weekly lab allowance {cap}: {used} already submitted this week, +{n} refused")
    return problems


def inside_proposals(path, root):
    """Specs must live under <root>/lab/proposals."""
    base = os.path.realpath(os.path.join(root, "lab", "proposals"))
    return os.path.realpath(path).startswith(base + os.sep)


def family_problems(spec, families, registry, queue):
    """Family must exist, be un-frozen and human-approved, have budget left, use only its universe, and stay out of the
    sealed holdout unless the spec is its declared one-time holdout confirmation."""
    fams = (families or {}).get("families", {})
    name = spec.get("family")
    fam = fams.get(name)
    if fam is None:
        return [f"unknown family '{name}'. Known: {sorted(fams)}"], None
    if fam.get("status") == "frozen":
        return [f"family '{name}' is FROZEN: {fam.get('reason', '')}"], fam
    if not fam.get("approved_by_human"):
        return [f"family '{name}' is not approved by a human yet (set approved_by_human=true in registry/families.json "
                f"after deciding its budget)"], fam
    problems = []
    used = sum(t["declared_trials"] for t in registry["tests"].values() if t.get("family") == name)
    reserved = sum(q["spec"]["declared_trials"] for q in queue
                   if q["spec"].get("family") == name and q["status"] in ("queued", "approved"))
    left = None if fam.get("budget_trials") is None else fam["budget_trials"] - used - reserved
    if left is not None and spec["declared_trials"] > left:
        problems.append(f"family '{name}' budget: {spec['declared_trials']} requested, {left} left "
                        f"({used} used + {reserved} reserved of {fam['budget_trials']})")
    universe = {m for ms in fam.get("universe", {}).values() for m in ms}
    outside = [m for m in spec["symbols"] if universe and m not in universe]
    if outside:
        problems.append(f"symbols outside the family universe: {outside}")
    ho = fam.get("periods", {}).get("sealed_holdout")
    if ho and not spec.get("holdout_confirmation"):
        if spec["oos_data"]["end"] >= ho[0] or spec["discovery_data"]["end"] >= ho[0]:
            problems.append(f"spec data windows reach into the sealed holdout (from {ho[0]}); "
                            "only a declared holdout_confirmation may")
    return problems, fam
