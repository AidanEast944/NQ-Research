"""Research Reporter: deterministic weekly summary from lab logs. Writes lab/reports/weekly_YYYY-MM-DD.md.
Usage: python3 src/lab/reporter.py"""
import json
import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import guard
from orchestrator import ROOT, paths


def build(root, now=None):
    now = now or datetime.now()
    P = paths(root)
    reg, queue = guard.load_json(P["registry"]), guard.load_json(P["queue"], [])
    events = []
    if os.path.exists(P["log"]):
        with open(P["log"]) as f:
            events = [json.loads(l) for l in f if l.strip()]
    c = Counter(e["event"] for e in events)
    out = [f"# Lab weekly report {now.date()}", "",
           f"Trials: {guard.remaining_budget(reg)} remaining of {reg['trial_budget_total']}; "
           f"{guard.queued_trials(queue)} reserved by the lab queue.", "",
           "## Agent decision counts", ""]
    out += [f"- {k}: {v}" for k, v in sorted(c.items())] or ["- none yet"]
    out += ["", "## Queue", ""]
    out += [f"- {q['spec']['id']} [{q['status']}] {q['spec']['title']} (trials {q['spec']['declared_trials']})"
            for q in queue] or ["- empty"]
    out += ["", "## Rejections (failed ideas are kept on purpose)", ""]
    rej = [e for e in events if e["event"].startswith("rejected")]
    out += [f"- {e['ts']} {e['event']} {e.get('id', '')} {e.get('problems', e.get('duplicate_of', ''))}" for e in rej] or ["- none"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    text = build(ROOT)
    d = os.path.join(ROOT, "lab", "reports")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"weekly_{datetime.now().date()}.md")
    with open(p, "w") as f:
        f.write(text)
    print(text)
