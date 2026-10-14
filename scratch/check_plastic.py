import csv
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('final/plastic/plastic_all.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

seen = []
for idx, r in enumerate(rows, 1):
    t = r.get('Chapter_or_Section')
    if not seen or seen[-1] != t:
        seen.append(t)
        print(f"{idx:2d}. {t} (Exam: {r.get('Exam_Date')})")
