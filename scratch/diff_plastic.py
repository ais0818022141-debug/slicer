# -*- coding: utf-8 -*-
import csv
import glob

with open('final/plastic/plastic_all.csv', 'r', encoding='utf-8-sig') as f:
    curr_rows = list(csv.DictReader(f))

backups = sorted(glob.glob('final/plastic/.backup/plastic_all_*.csv'))
latest_bak = backups[-1] if backups else None
print('Comparing against:', latest_bak)

if latest_bak:
    with open(latest_bak, 'r', encoding='utf-8-sig') as f:
        bak_rows = list(csv.DictReader(f))
    
    print(f'Curr: {len(curr_rows)} rows, Bak: {len(bak_rows)} rows')
    diff_count = 0
    for idx, (c, b) in enumerate(zip(curr_rows, bak_rows), 1):
        diffs = [k for k in c if c[k] != b.get(k)]
        if diffs:
            diff_count += 1
            qid = c.get('Question_ID')
            print(f'Row {idx} ({qid}): {diffs}')
            for k in diffs:
                if k != 'Chapter_or_Section':
                    print(f'   {k}: {repr(b.get(k)[:60])} -> {repr(c[k][:60])}')
    print(f'Total rows with differences: {diff_count}')
