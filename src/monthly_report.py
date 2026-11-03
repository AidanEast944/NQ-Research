"""
Monthly report: one markdown file, results/monthly_report_YYYY-MM.md, covering paper tracks (with change since the last report), decay
flags, the YM shadow ledger, the forward tracker for frozen daily candidates, trial budgets, and data/health. Read-only: touches no
account, strategy or live file, spends no trial. Scheduled for the 1st of each month 6:20 AM PT by launchd/com.nqresearch.monthlyreport.plist.
Run by hand: python3 src/monthly_report.py
"""
import contextlib
import glob
import io
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SNAP = "results/monthly_snapshots.json"


def _load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def balances(root="."):
    out = {}
    for f in sorted(glob.glob(os.path.join(root, "data/*_paper_account.json"))):
        d = _load(f, {})
        name = os.path.basename(f).replace("_paper_account.json", "")
        out[name] = {"balance": d.get("balance"), "closed": len(d.get("trade_history", [])), "open": len(d.get("positions", []))}
    return out


def build(root=".", today=None):
    today = today or date.today()
    cwd = os.getcwd()
    os.chdir(root)
    try:
        import status
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                status.main()
            except SystemExit:
                pass
        status_text = buf.getvalue().strip()
        bal = balances(".")
        snaps = _load(SNAP, {})
        prev = snaps[max(snaps)] if snaps else {}
        fwd = _load("results/forward_daily.json", {})
        L = [f"# nq-research monthly report - {today:%B %Y}", "",
             "Paper only; nothing here is validated for real capital. Generated automatically, read-only.", "",
             "## Paper tracks (change since last report)", "",
             "| track | closed | open | balance | change |", "|---|---|---|---|---|"]
        for k, v in bal.items():
            p = prev.get(k)
            ch = f"{v['balance'] - p['balance']:+,.0f} ({v['closed'] - p['closed']:+d} trades)" if p and v["balance"] is not None else "first report"
            L.append(f"| {k} | {v['closed']} | {v['open']} | {v['balance']:,.0f} | {ch} |" if v["balance"] is not None else f"| {k} | {v['closed']} | {v['open']} | - | {ch} |")
        L += ["", "## Forward tracker (frozen daily candidates; only days after the roster start are scored)", ""]
        if fwd.get("entries"):
            L += [f"Data through {fwd.get('data_last_date')}, forward start {fwd.get('forward_start')}.", "",
                  "| candidate | status | days | cum net | max DD | net Sharpe |", "|---|---|---|---|---|---|"]
            for k, r in fwd["entries"].items():
                if r.get("status") == "ok":
                    sh = f"{r['net_sharpe']:.2f}" if r.get("net_sharpe") is not None else "n/a (<60 days)"
                    L.append(f"| {k} | ok | {r['days']} | {r['cum_net']:+.2%} | {r['max_dd']:.2%} | {sh} |")
                else:
                    L.append(f"| {k} | {r.get('status')} | - | - | - | - |")
            L += ["", "A Sharpe is only shown after 60 forward days, and even then a few months of data cannot separate skill from luck."]
        else:
            L.append("Forward tracker has not run yet (python3 src/forward_daily.py).")
        L += ["", "## System status snapshot", "", "```", status_text, "```", "",
              "## Reading this report",
              "- Small samples dominate: compare tracks only at 50+ trades; the gap track's 50-trade decay check is due around early December 2026.",
              "- Forward days are the only evidence that is free and unbiased; they accumulate whether or not anyone is looking.", ""]
        text = "\n".join(L)
        os.makedirs("results", exist_ok=True)
        path = f"results/monthly_report_{today:%Y-%m}.md"
        with open(path, "w") as f:
            f.write(text)
        snaps[today.isoformat()] = bal
        with open(SNAP + ".tmp", "w") as f:
            json.dump(snaps, f, indent=2)
        os.replace(SNAP + ".tmp", SNAP)
        return path, text
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    p, _ = build()
    print(f"wrote {p}")
