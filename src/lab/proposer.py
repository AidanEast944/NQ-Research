"""
Proposer for the diversified_lowturnover family. It is NOT a discovery engine: it walks a FIXED, pre-approved menu of six
canonical candidates in a FIXED order and drafts the next one that has not been drafted. It invents no parameters.

  python3 src/lab/proposer.py list            menu, order, and where each candidate stands
  python3 src/lab/proposer.py draft [--n 1]   write the next spec(s) to lab/proposals/ plus the thin test script, dry-run the guards
Drafting spends nothing. Submitting (orchestrator submit), approving, registering and running remain separate HUMAN steps; this
module never calls them, never edits policy/families/registry files, and never touches a live file.
Each candidate = 1 declared trial against the family's own budget (12). Six candidates leave 6 trials unspent on purpose.
The menu can only grow by a human editing this file, and any addition is a new pre-registered trial.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import specs
import guard

FAMILY = "diversified_lowturnover"
ORDER = [("tsmom", 12), ("xsmom", 12), ("tsmom", 6), ("xsmom", 6), ("tsmom", 3), ("xsmom", 3)]
KIND_TEXT = {
    "tsmom": "time-series momentum: long a market when its trailing return is positive, short when negative",
    "xsmom": "cross-sectional momentum: within each asset class, long the stronger half and short the weaker half",
}


def cand_id(kind, months):
    return f"dlt_{kind}_{months}m"


def build_spec(kind, months, fam):
    cid = cand_id(kind, months)
    uni = [s for syms in fam["universe"].values() for s in syms]
    per = fam["periods"]
    pass_text = {
        "conditions": "net Sharpe >= 0.3 in discovery AND net Sharpe >= 0.3 in validation AND validation cumulative net return > 0",
        "supported": "conditions met AND validation Deflated Sharpe Ratio >= 0.95",
        "inconclusive": "conditions met but the Deflated Sharpe Ratio is below 0.95",
        "not_supported": "any condition fails",
    }
    return {
        "id": cid, "family": FAMILY,
        "title": f"{KIND_TEXT[kind].split(':')[0].title()} {months}-month, 19 futures, monthly rebalance",
        "hypothesis": f"{KIND_TEXT[kind]}. Lookback {months} months skipping the most recent month, risk-scaled to equal volatility, "
                      f"rebalanced monthly. Classic, widely published rule; low turnover means the 1 bp + $4.50 cost model should "
                      f"matter far less than it does for the intraday gap rules.",
        "symbols": uni,
        "discovery_data": {"start": per["discovery"][0] if isinstance(per["discovery"], list) else per["discovery"]["start"],
                           "end": per["discovery"][1] if isinstance(per["discovery"], list) else per["discovery"]["end"]},
        "oos_data": {"start": per["validation"][0] if isinstance(per["validation"], list) else per["validation"]["start"],
                     "end": per["validation"][1] if isinstance(per["validation"], list) else per["validation"]["end"]},
        "rules": {
            "signal": f"score = sum of daily log returns over the lookback of {months} months excluding the last 21 trading days",
            "sizing": "weight per market = sign(score) (tsmom) or +1/-1 by within-class rank (xsmom), times 10% target vol / 60-day realized vol, "
                      "leverage capped at 3 per market, divided by number of active markets",
            "rebalance": "last trading day of each month; weights decided at the close earn returns from the NEXT day",
            "implementation": "src/research/dlt_engine.py (committed, canonical, no tunable values)",
        },
        "parameters": {"kind": kind, "months": months, "skip_days": 21, "vol_window": 60, "target_vol": 0.10, "max_leverage": 3.0},
        "declared_trials": 1,
        "cost_model": fam["cost_model"],
        "holdout_confirmation": False,
        "author": "claude-proposer",
        "disclosure": "Menu candidate from the fixed canonical list; not selected on any result. Daily data starts 2010-06-08, so the first "
                      "signal appears mid-2011 for a 12-month lookback. Roll-day returns are set to 0 (small understatement, see futures_daily.py).",
        "pass_criteria": pass_text,
    }


def script_text(kind, months):
    cid = cand_id(kind, months)
    return f'''"""
PRE-REGISTERED test {cid} (lab spec lab/proposals/{cid}.json, family {FAMILY}).
Thin wrapper: all rules are in dlt_engine.py and all procedure/pass criteria are in dlt_test.py (read its docstring).
Nothing here may be tuned after the run.
Run:  cd ~/nq-research && source venv/bin/activate && python3 src/research_runner.py run {cid}
"""
import dlt_test

CAND = {{"id": "{cid}", "kind": "{kind}", "months": {months}, "declared_trials": 1}}

if __name__ == "__main__":
    dlt_test.run(CAND)
'''


def status_of(cid, root):
    q = guard.load_json(os.path.join(root, "lab/state/queue.json"), [])
    for item in q:
        if item["spec"]["id"] == cid:
            return item["status"]
    if os.path.exists(os.path.join(root, "lab/proposals", f"{cid}.json")):
        return "drafted (not submitted)"
    return "not drafted"


def cmd_list(root):
    fam = guard.load_json(os.path.join(root, "registry/families.json"))["families"][FAMILY]
    print(f"family {FAMILY}: budget {fam['budget_trials']} trials, menu {len(ORDER)} candidates (1 trial each)\n")
    for i, (k, m) in enumerate(ORDER, 1):
        print(f"  {i}. {cand_id(k, m):16s} {status_of(cand_id(k, m), root)}")


def cmd_draft(root, n=1):
    policy = guard.load_json(os.path.join(root, "lab/policy.json"))
    fams = guard.load_json(os.path.join(root, "registry/families.json"))
    fam = fams["families"][FAMILY]
    registry = guard.load_json(os.path.join(root, "registry/research_registry.json"))
    queue = guard.load_json(os.path.join(root, "lab/state/queue.json"), [])
    done = 0
    for kind, months in ORDER:
        cid = cand_id(kind, months)
        if status_of(cid, root) != "not drafted":
            continue
        if done >= n:
            break
        spec = build_spec(kind, months, fam)
        problems = specs.validate_shape(spec, policy, fam)
        fam_probs, _ = guard.family_problems(spec, fams, registry, queue)
        problems += fam_probs
        if problems:
            print(f"{cid}: NOT drafted, guards would refuse: {problems}")
            return 1
        os.makedirs(os.path.join(root, "lab/proposals"), exist_ok=True)
        with open(os.path.join(root, "lab/proposals", f"{cid}.json"), "w") as f:
            json.dump(spec, f, indent=2)
        with open(os.path.join(root, "src/research", f"dlt_{kind}_{months}m_test.py"), "w") as f:
            f.write(script_text(kind, months))
        print(f"drafted {cid}: lab/proposals/{cid}.json + src/research/dlt_{kind}_{months}m_test.py (guards dry-run: clean)")
        print(f"  next (you): python3 src/lab/orchestrator.py submit lab/proposals/{cid}.json")
        done += 1
    if done == 0:
        print("nothing left to draft (every menu item is already drafted or queued).")
    return 0


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv or argv[0] not in ("list", "draft"):
        print(__doc__)
        return 2
    if argv[0] == "list":
        cmd_list(ROOT)
        return 0
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 1
    return cmd_draft(ROOT, n)


if __name__ == "__main__":
    sys.exit(main())
