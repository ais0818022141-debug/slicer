import csv
import sys
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for sub in ['plastic', 'onco', 'ped_surgery']:
    p = f'final/{sub}/{sub}_all.csv'
    with open(p, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    by_topic = defaultdict(list)
    for r in rows:
        by_topic[r['Chapter_or_Section']].append(r)
    print(f"\n=====================================")
    print(f"Sub: {sub}")
    print(f"=====================================")
    for t, qlist in by_topic.items():
        print(f"Topic: {t} ({len(qlist)} questions)")
        for idx, q in enumerate(qlist, 1):
            qid = q.get('Question_ID')
            date = q.get('Exam_Date')
            title = q.get('Question_Text')[:40]
            print(f"  {idx:2d}. [{qid}] ({date}): {title}...")
