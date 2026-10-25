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
