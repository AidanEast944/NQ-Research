"""
Research Director (deterministic). Usage, from the repo root:
  python3 src/lab/orchestrator.py status
  python3 src/lab/orchestrator.py submit lab/proposals/SPEC.json
  python3 src/lab/orchestrator.py queue
  python3 src/lab/orchestrator.py approve SPEC_ID --note "why"     (HUMAN decision; runs nothing)
  python3 src/lab/orchestrator.py reject SPEC_ID --note "why"
  python3 src/lab/orchestrator.py validate RESULT.json
Never imports or edits live_gate.py, risk_limits.py, paper accounts, or the trial registry.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import specs
import guard
import validator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def paths(root):
    st = os.path.join(root, "lab", "state")
    return {"policy": os.path.join(root, "lab", "policy.json"),
            "registry": os.path.join(root, "registry", "research_registry.json"),
            "families": os.path.join(root, "registry", "families.json"),
            "queue": os.path.join(st, "queue.json"),
            "hyp": os.path.join(st, "hypotheses.jsonl"),
            "log": os.path.join(st, "agent_log.jsonl")}


def git_commit(root):
    try:
        r = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def log_event(root, event, **fields):
    p = paths(root)["log"]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    rec = {"ts": datetime.now().isoformat(timespec="seconds"), "event": event,
           "code_commit": git_commit(root), **fields}
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_hyp(root):
    p = paths(root)["hyp"]
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def append_hyp(root, rec):
    p = paths(root)["hyp"]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def save_queue(root, q):
    p = paths(root)["queue"]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(q, f, indent=2)
    os.replace(tmp, p)


def submit(root, spec_path, now=None):
    """Returns (accepted: bool, messages: list[str])."""
    now = now or datetime.now()
    P = paths(root)
    policy = guard.load_json(P["policy"])
    registry = guard.load_json(P["registry"])
    queue = guard.load_json(P["queue"], [])
    if not guard.inside_proposals(spec_path, root):
        log_event(root, "rejected_path", path=spec_path)
        return False, ["spec must live under lab/proposals/"]
    with open(spec_path) as f:
        spec = json.load(f)
    families = guard.load_json(P["families"], {"families": {}})
    fam = families.get("families", {}).get(spec.get("family"))
    problems = specs.validate_shape(spec, policy, fam)
    if problems:
        log_event(root, "rejected_invalid", id=spec.get("id"), problems=problems)
        return False, problems
    fp, fh, sh = specs.fingerprint(spec), specs.family_hash(spec), specs.spec_hash(spec)
    prior = read_hyp(root)
    dup = [h for h in prior if h["fingerprint"] == fp]
    if dup:
        log_event(root, "rejected_duplicate", id=spec["id"], duplicate_of=dup[0]["id"], fingerprint=fp)
        return False, [f"duplicate of {dup[0]['id']} (status {dup[0]['status']}): same rules, parameters and data windows"]
    if any(q["spec"]["id"] == spec["id"] for q in queue):
        return False, [f"id {spec['id']} already used"]
    fam_probs, fam = guard.family_problems(spec, families, registry, queue)
    problems = list(fam_probs)
    own_budget = fam is not None and fam.get("budget_trials") is not None
    if not (fam and fam.get("periods")):
        problems += guard.holdout_problems(spec, policy)       # legacy sealed-symbol rule (RTY) for families without periods
    if own_budget:
        # the family has its own trial budget (checked in family_problems); only the weekly allowance is shared
        cap, used_w = policy["weekly_trial_allowance"], guard.weekly_used(queue, now)
        if used_w + spec["declared_trials"] > cap:
            problems.append(f"weekly lab allowance {cap}: {used_w} already submitted this week, "
                            f"+{spec['declared_trials']} refused")
    else:
        own = {n for n, f in families.get("families", {}).items() if f.get("budget_trials") is not None}
        global_queue = [q for q in queue if q["spec"].get("family") not in own]
        problems += guard.budget_problems(spec, registry, global_queue, policy, now)
    if problems:
        log_event(root, "rejected_policy", id=spec["id"], problems=problems)
        return False, problems
    msgs = []
    same_family = [h["id"] for h in prior if h["family"] == fh]
    if same_family:
        msgs.append(f"WARNING: same rules as {same_family}, only parameters differ - a parameter sweep. "
                    "Declared_trials should count every variant.")
    queue.append({"status": "queued", "submitted_at": now.isoformat(timespec="seconds"),
                  "spec": spec, "fingerprint": fp, "family": fh, "spec_hash": sh})
    save_queue(root, queue)
    append_hyp(root, {"id": spec["id"], "fingerprint": fp, "family": fh, "status": "queued",
                      "submitted_at": now.isoformat(timespec="seconds")})
    log_event(root, "queued", id=spec["id"], fingerprint=fp, spec_hash=sh,
              declared_trials=spec["declared_trials"], author=spec["author"])
    return True, msgs + [f"queued {spec['id']} (fingerprint {fp})"]


def decide(root, spec_id, decision, note):
    P = paths(root)
    queue = guard.load_json(P["queue"], [])
    for q in queue:
        if q["spec"]["id"] == spec_id and q["status"] == "queued":
            q["status"] = decision
            q["decision_note"] = note
            q["decided_at"] = datetime.now().isoformat(timespec="seconds")
            save_queue(root, queue)
            append_hyp(root, {"id": spec_id, "fingerprint": q["fingerprint"], "family": q["family"],
                              "status": decision})
            log_event(root, decision, id=spec_id, note=note, decided_by="human")
            return True, f"{spec_id} -> {decision}"
    return False, f"{spec_id} not found in queued state"


def mark_registered(root, spec_id, registry_id):
    """Called after the human/runner registered the approved spec in research_registry.json, so the lab
    stops double-counting its reserved trials. Does not touch the registry itself."""
    P = paths(root)
    queue = guard.load_json(P["queue"], [])
    for q in queue:
        if q["spec"]["id"] == spec_id and q["status"] == "approved":
            q["status"], q["registry_id"] = "registered", registry_id
            save_queue(root, queue)
            log_event(root, "registered", id=spec_id, registry_id=registry_id)
            return True
    return False


def status(root):
    P = paths(root)
    policy, reg = guard.load_json(P["policy"]), guard.load_json(P["registry"])
    queue = guard.load_json(P["queue"], [])
    rem = guard.remaining_budget(reg)
    lines = [f"Registry trials remaining: {rem} of {reg['trial_budget_total']}",
             f"Reserved by lab queue: {guard.queued_trials(queue)}",
             f"Lab trials submitted this week: {guard.weekly_used(queue, datetime.now())} of {policy['weekly_trial_allowance']}",
             f"Queue: " + (", ".join(f"{q['spec']['id']}[{q['status']}]" for q in queue) or "empty")]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("queue")
    s = sub.add_parser("submit"); s.add_argument("spec")
    for c in ("approve", "reject"):
        d = sub.add_parser(c); d.add_argument("id"); d.add_argument("--note", default="")
    m = sub.add_parser("mark-registered"); m.add_argument("id"); m.add_argument("--registry-id", required=True)
    v = sub.add_parser("validate"); v.add_argument("result")
    a = ap.parse_args()
    if a.cmd == "status":
        print(status(ROOT))
    elif a.cmd == "queue":
        for q in guard.load_json(paths(ROOT)["queue"], []):
            print(f"{q['spec']['id']:<28} {q['status']:<9} trials={q['spec']['declared_trials']} {q['spec']['title']}")
    elif a.cmd == "submit":
        ok, msgs = submit(ROOT, os.path.abspath(a.spec))
        print("ACCEPTED" if ok else "REFUSED"); print("\n".join(" - " + m for m in msgs)); sys.exit(0 if ok else 1)
    elif a.cmd in ("approve", "reject"):
        ok, m = decide(ROOT, a.id, "approved" if a.cmd == "approve" else "rejected", a.note); print(m); sys.exit(0 if ok else 1)
    elif a.cmd == "mark-registered":
        print("ok" if mark_registered(ROOT, a.id, a.registry_id) else "not found in approved state")
    elif a.cmd == "validate":
        with open(a.result) as f:
            res = json.load(f)
        pol = guard.load_json(paths(ROOT)["policy"])
        out = validator.check_many(res, pol, guard.load_json(paths(ROOT)["families"], {"families": {}}))
        log_event(ROOT, "validated", result=a.result, verdicts=out)
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
