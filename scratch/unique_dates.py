import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for sub in ['plastic', 'onco', 'ped_surgery']:
    p = Path(f'final/{sub}/{sub}_all.csv')
    with open(p, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    dates = sorted(set(r.get('Exam_Date') for r in rows if r.get('Exam_Date')))
    print(f"=== {sub} unique dates ({len(dates)}) ===")
    print(dates)
