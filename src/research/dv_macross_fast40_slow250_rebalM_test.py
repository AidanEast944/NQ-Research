"""
PRE-REGISTERED test dv_macross_fast40_slow250_rebalM (lab spec lab/proposals/dv_macross_fast40_slow250_rebalM.json, family discovery_validation).
Thin wrapper: rules in discover.py, procedure and pass criteria in dv_test.py (read its docstring). Nothing here may be tuned.
Run:  cd ~/nq-research && source venv/bin/activate && python3 src/research_runner.py run dv_macross_fast40_slow250_rebalM
"""
import dv_test

CID = "macross_fast40_slow250_rebalM"

if __name__ == "__main__":
    dv_test.run(CID)
