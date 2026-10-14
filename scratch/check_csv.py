import sys
import csv
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for sub in ['plastic', 'onco', 'ped_surgery']:
    p = Path(f'final/{sub}/{sub}_all.csv')
    with open(p, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f'=== {sub} ({len(rows)} rows) ===')
    topics = {}
    for r in rows:
        t = r.get('Chapter_or_Section')
        d = r.get('Exam_Date')
        topics.setdefault(t, []).append(d)
    for t, dates in topics.items():
        print(f'  Topic: {t} ({len(dates)} questions)')
        print(f'    First 5 dates: {dates[:5]}')
        if len(dates) > 5:
            print(f'    Last 3 dates: {dates[-3:]}')
