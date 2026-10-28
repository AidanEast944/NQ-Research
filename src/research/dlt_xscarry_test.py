"""
PRE-REGISTERED test dlt_xscarry (lab spec lab/proposals/dlt_xscarry.json, family diversified_lowturnover).
Thin wrapper: all rules are in dlt_engine.py and all procedure/pass criteria are in dlt_test.py (read its docstring).
Nothing here may be tuned after the run.
Run:  cd ~/nq-research && source venv/bin/activate && python3 src/research_runner.py run dlt_xscarry
"""
import dlt_test

CAND = {"id": "dlt_xscarry", "kind": "xscarry", "months": 0, "declared_trials": 1}

if __name__ == "__main__":
    dlt_test.run(CAND)
