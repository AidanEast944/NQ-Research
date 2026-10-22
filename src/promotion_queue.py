"""
Promotion queue with a human gate (research_log.md Entry 73).

For each strategy it checks the written gate for the next stage (registry/promotion_queue.json) against
real evidence: the paper track's forward results (decay monitor) and the research registry's recorded
verdicts. It prints exactly which requirements are met and which block promotion.

HARD LIMITS BY DESIGN:
  * `check` and `status` only read. `approve` only writes a timestamped approval record into the queue file.
  * Nothing here edits live_gate.py, an account file or a scheduled job, and nothing places a trade.
    Moving a strategy to micro_live is a manual edit by Aidan, even after an approval is recorded.
  * `approve` refuses while any gate requirement is unmet, unless --override "reason" is given, and an
    override is stored permanently on the record.

Usage:
  python3 src/promotion_queue.py status
  python3 src/promotion_queue.py check [STRATEGY]
  python3 src/promotion_queue.py attach STRATEGY TEST_ID      (link a registry test as supporting evidence)
  python3 src/promotion_queue.py approve STRATEGY --note "why" [--override "reason"]
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

QUEUE = "registry/promotion_queue.json"
REGISTRY = "registry/research_registry.json"
REPORT = "results/decay_report.json"


def load(path):
    with open(path) as f:
        return json.load(f)


def save_queue(q):
    tmp = QUEUE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(q, f, indent=2)
    os.replace(tmp, QUEUE)


def fresh_decay_report():
    subprocess.run([sys.executable, "src/decay_monitor.py"], capture_output=True, text=True)
    return {t["key"]: t for t in load(REPORT)["tracks"]}


def evaluate(name, spec, q, reg, tracks):
    gate = q["gates"]["paper_to_micro_live"]
    t = tracks.get(spec["track"], {})
    n = t.get("trades", 0)
    pf = t.get("net_profit_factor")
    net = t.get("net_dollars", 0)
    flags = [f for f in t.get("flags", []) if not f.startswith("MILESTONE")]
    tests = [reg["tests"].get(i, {}) for i in spec.get("supporting_tests", [])]
    supported = any(x.get("verdict") == "supported" for x in tests)
    rows = [
        (f"forward trades >= {gate['min_forward_trades']}", n >= gate["min_forward_trades"], f"{n} so far"),
        (f"forward net profit factor >= {gate['min_forward_net_profit_factor']}",
         pf is not None and pf >= gate["min_forward_net_profit_factor"], f"{pf if pf is not None else 'n/a'}"),
        (f"forward net dollars > {gate['min_forward_net_dollars']}", net > gate["min_forward_net_dollars"], f"${net:,.0f}"),
        ("no active decay flags", (not flags) or not gate["require_no_decay_flags"], "; ".join(flags) or "none"),
        ("at least one supporting pre-registered test with verdict 'supported'",
         supported or not gate["require_supported_test"],
         ", ".join(f"{i}={reg['tests'].get(i, {}).get('verdict', '?')}" for i in spec.get("supporting_tests", [])) or "none attached"),
    ]
    return rows


def show(name, spec, rows):
    ok = all(r[1] for r in rows)
    print(f"\n{name}  [stage: {spec['stage']}]  ->  {'ELIGIBLE FOR YOUR REVIEW' if ok else 'BLOCKED'}")
    for label, met, detail in rows:
        print(f"   [{'x' if met else ' '}] {label}   ({detail})")
    if spec.get("approvals"):
        last = spec["approvals"][-1]
        print(f"   last approval: {last['at']} - {last['note']}" + (f" (OVERRIDE: {last['override']})" if last.get("override") else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    c = sub.add_parser("check"); c.add_argument("strategy", nargs="?")
    at = sub.add_parser("attach"); at.add_argument("strategy"); at.add_argument("test_id")
    ap_ = sub.add_parser("approve"); ap_.add_argument("strategy"); ap_.add_argument("--note", required=True)
    ap_.add_argument("--override", default="")
    a = ap.parse_args()

    q, reg = load(QUEUE), load(REGISTRY)
    if a.cmd in ("status", "check"):
        tracks = fresh_decay_report()
        names = [a.strategy] if getattr(a, "strategy", None) else list(q["strategies"])
        eligible = []
        for n in names:
            if n not in q["strategies"]:
                sys.exit(f"unknown strategy {n}")
            ok = show(n, q["strategies"][n], evaluate(n, q["strategies"][n], q, reg, tracks))
            if ok:
                eligible.append(n)
        print("\n" + (f"Eligible for your review: {', '.join(eligible)}" if eligible else
                      "Nothing is eligible for promotion. That is the expected state until forward evidence builds."))
    elif a.cmd == "attach":
        if a.strategy not in q["strategies"] or a.test_id not in reg["tests"]:
            sys.exit("unknown strategy or test id")
        s = q["strategies"][a.strategy]
        if a.test_id not in s["supporting_tests"]:
            s["supporting_tests"].append(a.test_id)
        save_queue(q)
        print(f"Attached {a.test_id} to {a.strategy} (its verdict is '{reg['tests'][a.test_id].get('verdict', 'unscored')}').")
    elif a.cmd == "approve":
        if a.strategy not in q["strategies"]:
            sys.exit("unknown strategy")
        s = q["strategies"][a.strategy]
        rows = evaluate(a.strategy, s, q, reg, fresh_decay_report())
        ok = show(a.strategy, s, rows)
        if not ok and not a.override:
            sys.exit("\nREFUSED: requirements unmet. Use --override \"reason\" only if you mean it; it is recorded permanently.")
        s["approvals"].append({"at": datetime.now().isoformat(timespec="seconds"), "note": a.note,
                               "override": a.override, "snapshot": [(r[0], r[1], r[2]) for r in rows]})
        save_queue(q)
        print("\nApproval RECORDED. Nothing else changed. To go to micro-live, you edit live_gate.py yourself.")


if __name__ == "__main__":
    main()
