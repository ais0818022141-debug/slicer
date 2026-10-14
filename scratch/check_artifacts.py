import sys
import csv
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

csv_path = Path(r"final\optho\optho_all.csv")
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

found = False
for idx, r in enumerate(rows, start=1):
    for col, val in r.items():
        if val and any(err in val for err in ['#NAME?', '#REF!', '#VALUE!', '#DIV/0!', '#N/A']):
            print(f"Row {idx} [{r.get('Question_ID')}]: column '{col}' has formula error: {val}")
            found = True
        elif val and val.startswith('='):
            print(f"Row {idx} [{r.get('Question_ID')}]: column '{col}' starts with '=': {val[:30]}")
            found = True

if not found:
    print("No formula errors found!")
