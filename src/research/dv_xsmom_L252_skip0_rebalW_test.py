"""
PRE-REGISTERED test dv_xsmom_L252_skip0_rebalW (lab spec lab/proposals/dv_xsmom_L252_skip0_rebalW.json, family discovery_validation).
Thin wrapper: rules in discover.py, procedure and pass criteria in dv_test.py (read its docstring). Nothing here may be tuned.
Run:  cd ~/nq-research && source venv/bin/activate && python3 src/research_runner.py run dv_xsmom_L252_skip0_rebalW
"""
import dv_test

CID = "xsmom_L252_skip0_rebalW"

if __name__ == "__main__":
    dv_test.run(CID)
