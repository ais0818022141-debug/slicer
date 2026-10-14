import sys
import csv
from itertools import groupby

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('final/general_surgery/general_surgery_all.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

for k, g in groupby(rows, key=lambda r: r['Chapter_or_Section']):
    items = list(g)
    print(f"'{k}': {len(items)} items (IDs: {items[0]['Question_ID']} .. {items[-1]['Question_ID']})")
