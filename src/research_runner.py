"""
Research runner (research_log.md Entry 73). Runs ONLY tests that were pre-registered, and keeps the
trial ledger honest so nobody has to remember to.

What it enforces:
  * a test must be registered with a script path and a declared trial count BEFORE it can run
  * the script must be committed to git and unmodified since (so criteria cannot be edited after the fact)
  * registering is refused if it would push the total trial count past registry/research_registry.json
    "trial_budget_total" (baseline_trials + every registered test's declared_trials)
  * each test runs once; rerunning needs --rerun and is recorded as a rerun
  * every run is appended to results/research_runs.jsonl with the script's git commit, exit code and output file
It never writes a verdict by itself and never creates tests. A human scores the output against the criteria in
the script's docstring, then records the verdict with the `verdict` command.

Usage:
  python3 src/research_runner.py list
  python3 src/research_runner.py budget
  python3 src/research_runner.py register ID --script PATH --trials N --desc "text"
  python3 src/research_runner.py run ID [--rerun]
  python3 src/research_runner.py verdict ID supported|not_supported|inconclusive --entry N [--note "text"]
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

REGISTRY = "registry/research_registry.json"
RUNS_LOG = "results/research_runs.jsonl"
FAMILIES = "registry/families.json"


def load():
    with open(REGISTRY) as f:
        return json.load(f)


def save(reg):
    tmp = REGISTRY + ".tmp"
    with open(tmp, "w") as f:
        json.dump(reg, f, indent=2)
    os.replace(tmp, REGISTRY)


def used_trials(reg):
    """Global ledger. Tests registered under a family with its own budget (--family) count against that family, not here.
    Every test registered before families existed has no 'family' key, so this is unchanged for all of them."""
    return reg["baseline_trials"] + sum(t["declared_trials"] for t in reg["tests"].values() if not t.get("family"))


def load_families():
    if not os.path.exists(FAMILIES):
        return {"families": {}}
    with open(FAMILIES) as f:
        return json.load(f)


def family_used(reg, name):
    return sum(t["declared_trials"] for t in reg["tests"].values() if t.get("family") == name)


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def script_is_frozen(path):
    """True and the commit hash only if the script is tracked, committed and has no local changes."""
    if not os.path.exists(path):
        return False, f"script not found: {path}"
    tracked = git("ls-files", "--error-unmatch", path)
    if tracked.returncode != 0:
        return False, "script is not tracked by git - commit it first"
    status = git("status", "--porcelain", "--", path).stdout.strip()
    if status:
        return False, f"script has uncommitted changes ({status}) - commit it first so the criteria are frozen"
    commit = git("log", "-1", "--format=%H", "--", path).stdout.strip()
    return True, commit


def cmd_list(reg, _):
    for tid, t in reg["tests"].items():
        print(f"{tid:<24} {t['status']:<10} verdict={t.get('verdict','-'):<14} trials={t['declared_trials']:<3} "
              f"entry={t.get('log_entry','-')}  {t['description']}")


def cmd_budget(reg, _):
    used = used_trials(reg)
    print(f"Trials used: {used} of {reg['trial_budget_total']} "
          f"(baseline {reg['baseline_trials']} + registered {used - reg['baseline_trials']})")
    print(f"Remaining: {reg['trial_budget_total'] - used}")
    for name, fam in load_families()["families"].items():
        if fam.get("budget_trials") is not None:
            st = "APPROVED" if fam.get("approved_by_human") else "NOT APPROVED (no trials may be spent)"
            print(f"Family {name}: {family_used(reg, name)} of {fam['budget_trials']} used, {st}")
        elif fam.get("status") == "frozen":
            print(f"Family {name}: FROZEN")


def cmd_register(reg, a):
    if a.id in reg["tests"]:
        sys.exit(f"{a.id} is already registered.")
    ok, info = script_is_frozen(a.script)
    if not ok:
        sys.exit(f"REFUSED: {info}")
    if a.family:
        fam = load_families()["families"].get(a.family)
        if fam is None:
            sys.exit(f"REFUSED: unknown family '{a.family}' (see {FAMILIES}).")
        if fam.get("status") == "frozen":
            sys.exit(f"REFUSED: family '{a.family}' is FROZEN: {fam.get('reason', '')}")
        if not fam.get("approved_by_human") or fam.get("budget_trials") is None:
            sys.exit(f"REFUSED: family '{a.family}' has no human-approved budget yet (edit {FAMILIES} deliberately).")
        if family_used(reg, a.family) + a.trials > fam["budget_trials"]:
            sys.exit(f"REFUSED: {a.trials} more trials would exceed family '{a.family}' budget "
                     f"({family_used(reg, a.family)} used of {fam['budget_trials']}).")
    elif used_trials(reg) + a.trials > reg["trial_budget_total"]:
        sys.exit(f"REFUSED: {a.trials} more trials would exceed the budget "
                 f"({used_trials(reg)} used of {reg['trial_budget_total']}). Raising the budget is a deliberate edit "
                 f"of {REGISTRY}, with a reason in research_log.md.")
    reg["tests"][a.id] = {"script": a.script, "declared_trials": a.trials, "description": a.desc,
                          "status": "registered", "registered_at": datetime.now().isoformat(timespec="seconds"),
                          "script_commit": info}
    if a.family:
        reg["tests"][a.id]["family"] = a.family
    save(reg)
    if a.family:
        print(f"Registered {a.id} ({a.trials} trials, family {a.family}, script commit {info[:8]}). "
              f"Family now at {family_used(reg, a.family)}; global ledger unchanged at {used_trials(reg)} of {reg['trial_budget_total']}.")
    else:
        print(f"Registered {a.id} ({a.trials} trials, script commit {info[:8]}). "
              f"Now at {used_trials(reg)} of {reg['trial_budget_total']}.")


def cmd_run(reg, a):
    t = reg["tests"].get(a.id)
    if t is None:
        sys.exit(f"{a.id} is not registered. The runner only runs pre-registered tests.")
    if t["status"] != "registered" and not a.rerun:
        sys.exit(f"{a.id} already has status '{t['status']}'. Use --rerun to run again (it is logged as a rerun).")
    ok, info = script_is_frozen(t["script"])
    if not ok:
        sys.exit(f"REFUSED: {info}")
    if t.get("script_commit") and t["script_commit"] != info:
        sys.exit(f"REFUSED: {t['script']} changed since registration "
                 f"(registered at {t['script_commit'][:8]}, now {info[:8]}). A changed test is a new test - register it.")
    os.makedirs("results", exist_ok=True)
    out_path = f"results/{a.id}_output.txt"
    started = datetime.now().isoformat(timespec="seconds")
    print(f"Running {a.id} ({t['script']} @ {info[:8]}). Output also saved to {out_path}\n")
    with open(out_path, "w") as out:
        proc = subprocess.Popen([sys.executable, "-u", t["script"]], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            sys.stdout.write(line)
            out.write(line)
        code = proc.wait()
    rec = {"id": a.id, "started": started, "finished": datetime.now().isoformat(timespec="seconds"),
           "script": t["script"], "script_commit": info, "exit_code": code, "output": out_path,
           "rerun": bool(a.rerun), "declared_trials": t["declared_trials"]}
    with open(RUNS_LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    t["status"] = "ran" if code == 0 else "failed"
    t["output"] = out_path
    t["last_run"] = rec["finished"]
    save(reg)
    print(f"\nFinished with exit code {code}. Trials used: {used_trials(reg)} of {reg['trial_budget_total']}.")
    if code == 0:
        print("NEXT (human): score the output against the criteria in the script docstring, write the "
              "research_log.md entry, then record it:\n"
              f"  python3 src/research_runner.py verdict {a.id} supported|not_supported|inconclusive --entry N")


def cmd_verdict(reg, a):
    t = reg["tests"].get(a.id)
    if t is None:
        sys.exit(f"{a.id} is not registered.")
    if t["status"] not in ("ran", "scored"):
        sys.exit(f"{a.id} has not been run (status '{t['status']}'); nothing to score.")
    t["verdict"] = a.verdict
    t["log_entry"] = a.entry
    t["status"] = "scored"
    if a.note:
        t["verdict_note"] = a.note
    t["scored_at"] = datetime.now().isoformat(timespec="seconds")
    save(reg)
    print(f"Recorded: {a.id} -> {a.verdict} (log entry {a.entry}).")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("budget")
    r = sub.add_parser("register")
    r.add_argument("id"); r.add_argument("--script", required=True)
    r.add_argument("--trials", type=int, required=True); r.add_argument("--desc", required=True)
    r.add_argument("--family", default=None, help="count against this family's own budget (registry/families.json)")
    u = sub.add_parser("run")
    u.add_argument("id"); u.add_argument("--rerun", action="store_true")
    v = sub.add_parser("verdict")
    v.add_argument("id"); v.add_argument("verdict", choices=["supported", "not_supported", "inconclusive"])
    v.add_argument("--entry", type=int, required=True); v.add_argument("--note", default="")
    a = ap.parse_args()
    reg = load()
    {"list": cmd_list, "budget": cmd_budget, "register": cmd_register,
     "run": cmd_run, "verdict": cmd_verdict}[a.cmd](reg, a)


if __name__ == "__main__":
    main()
