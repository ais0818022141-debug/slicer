import csv
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('final/onco/onco_all.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

for idx, r in enumerate(rows, 1):
    if 'سرطان الدرق اللبي' in r.get('Question_Text', ''):
        print(f"Row {idx}: ID={r.get('Question_ID')}")
        print("Text:", r.get('Question_Text'))
        print("Explanation:")
        print(repr(r.get('Explanation')))
        print("Raw explanation:")
        print(r.get('Explanation'))
