"""
One-command overview. Read-only: touches no account, job or strategy file.
Run: python3 src/status.py
Shows: trial budget, open paper positions, per-track trade counts, decay flags, data freshness, backup age,
heartbeat age and problems, YM mini shadow numbers, and the lab queue.
"""
import glob
import json
import os
import sys
from datetime import date, datetime

sys.path.insert(0, "src")


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def age_hours(path):
    try:
        return (datetime.now().timestamp() - os.path.getmtime(path)) / 3600
    except OSError:
        return None


def fmt_age(h):
    if h is None:
        return "never"
    return f"{h:.0f}h ago" if h < 48 else f"{h/24:.0f}d ago"


def newest(pattern):
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


def main():
    print(f"nq-research status  {datetime.now():%Y-%m-%d %H:%M}\n")
    reg = load("registry/research_registry.json")
    if reg:
        used = reg["baseline_trials"] + sum(t["declared_trials"] for t in reg["tests"].values())
        print(f"TRIALS      {used} of {reg['trial_budget_total']} used, {reg['trial_budget_total'] - used} remain")
    print("\nPAPER ACCOUNTS (open positions / closed trades / balance)")
    for f in sorted(glob.glob("data/*_paper_account.json")):
        a = load(f, {})
        op = a.get("positions", [])
        flag = "  <-- OPEN" if op else ""
        name = os.path.basename(f).replace("_paper_account.json", "")
        print(f"   {name:<22} {len(op)} open / {len(a.get('trade_history', [])):>3} closed / ${a.get('balance', 0):>10,.2f}{flag}")
    d = load("results/decay_report.json")
    if d:
        flagged = [t for t in d["tracks"] if t.get("flags")]
        print(f"\nDECAY MONITOR  last run {d['generated'][:16]}, "
              f"{'no flags' if not flagged else str(len(flagged)) + ' track(s) flagged: ' + ', '.join(t['key'] for t in flagged)}")
    print("\nDATA ARCHIVES (newest file)")
    for sym in ("nq", "es", "ym", "rty"):
        n = newest(f"data/raw_{sym}_extended/*.csv")
        print(f"   {sym.upper():<4} {os.path.basename(n)[-14:-4] if n else 'none'}")
    hb = load("results/heartbeat.json")
    print("\nHEARTBEAT   " + (f"{'OK' if hb['ok'] else 'PROBLEMS'} ({fmt_age(age_hours('results/heartbeat.json'))}, "
                               f"{len(hb['jobs'])} jobs)" if hb else "not run yet"))
    if hb and not hb["ok"]:
        for p in hb["problems"]:
            print("   -", p)
    la = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/nq-research-backups")
    bdir = la if os.path.isdir(la) else os.path.expanduser("~/Backups/nq-research")
    b = newest(os.path.join(bdir, "state_*.tar.gz"))
    print(f"BACKUP      {os.path.basename(b) + ' (' + fmt_age(age_hours(b)) + ')' if b else 'none found in ' + bdir}")
    sh = load("results/ym_mini_shadow.json")
    if sh:
        print(f"\nYM MINI SHADOW  {sh['closed_trades']}/{sh['target_trades']} forward trades, net ${sh['net_dollars']:,.2f}, "
              f"PF {sh['net_pf']} (too few to conclude)")
    q = load("lab/state/queue.json", [])
    print("LAB QUEUE   " + (", ".join(f"{x['spec']['id']}[{x['status']}]" for x in q) or "empty"))


if __name__ == "__main__":
    main()
