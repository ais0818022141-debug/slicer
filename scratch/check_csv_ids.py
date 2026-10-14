import csv
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for s in ['plastic', 'onco', 'ped_surgery']:
    p = f'final/{s}/{s}_all.csv'
    with open(p, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    ids = [r.get('Question_ID') for r in rows]
    print(f"{s}: rows={len(rows)}, first_id={ids[0]}, last_id={ids[-1]}, unique_ids={len(set(ids))}")
    print(f"  sample IDs: {ids[:10]}")
