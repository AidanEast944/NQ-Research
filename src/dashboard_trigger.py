"""
Small helper any resolve/check script can call after closing a trade, so the dashboard reflects
the new balance immediately instead of waiting for the scheduled daily refresh.
"""
import subprocess
import sys
import os

def refresh_dashboard():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        auto_script = os.path.join(script_dir, "generate_dashboard.py")
        subprocess.run([sys.executable, auto_script], check=False, timeout=30)
        print("(dashboard refreshed)")
    except Exception as e:
        print(f"(dashboard refresh failed, non-fatal: {e})")
