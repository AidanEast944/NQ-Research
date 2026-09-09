import subprocess
import sys

scripts = [
    ("Forward Test Summary", "src/forward_summary.py"),
    ("Risk Analysis", "src/risk_analysis.py"),
    ("Data Gap Check", "src/check_data_gaps.py"),
    ("Equity Curve", "src/equity_curve.py"),
]

for title, script in scripts:
    print("\n" + "=" * 60)
    print(title.upper())
    print("=" * 60)
    subprocess.run([sys.executable, script])

print("\nDashboard complete. Open results/equity_curve.png to see the chart.")