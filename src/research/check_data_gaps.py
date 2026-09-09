import glob
import os
import re
from datetime import date, timedelta

DATA_FOLDER = "data/raw"

files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))

if not files:
    print("No archive files found.")
    exit()

found_dates = []
for f in files:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", f)
    if match:
        found_dates.append(date.fromisoformat(match.group(1)))

found_dates = sorted(found_dates)
start_date = found_dates[0]
end_date = found_dates[-1]

print(f"Archive spans {start_date} to {end_date}")
print(f"Files found: {len(found_dates)}\n")

missing_weekdays = []
current = start_date
while current <= end_date:
    if current.weekday() < 5:  # Monday=0 ... Friday=4
        if current not in found_dates:
            missing_weekdays.append(current)
    current += timedelta(days=1)

if missing_weekdays:
    print(f"WARNING: {len(missing_weekdays)} weekday(s) missing from archive:")
    for d in missing_weekdays:
        print(f"  - {d} ({d.strftime('%A')})")
    print("\nNote: some of these may be legitimate market holidays, not real gaps.")
else:
    print("No missing weekdays found - archive looks complete.")

file_sizes = [(f, os.path.getsize(f)) for f in files]
tiny_files = [f for f, size in file_sizes if size < 500]

if tiny_files:
    print(f"\nWARNING: {len(tiny_files)} suspiciously small file(s) (possible incomplete data):")
    for f in tiny_files:
        print(f"  - {f}")