import sys
import csv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("final/general_surgery/general_surgery_all.csv", 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        qid = r.get('Question_ID', '')
        if qid in [f'q_general_surgery_0{i:02d}' for i in range(20, 70)]:
            print(qid, "::", r.get('Chapter_or_Section'), "::", r.get('Question_Text')[:50])
