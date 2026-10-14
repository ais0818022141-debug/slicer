import csv
import json
import sys
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def norm_stem(s):
    if not s or not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r'[\s:：]*رأس\s*[:：]*$', '', s)
    s = re.sub(r'[\s:：؟?.]+$', '', s)
    return s + ':'

for sub in ['plastic', 'onco', 'ped_surgery']:
    csv_p = f'final/{sub}/{sub}_all.csv'
    json_p = f'final/{sub}/{sub}_all.json'
    with open(csv_p, 'r', encoding='utf-8-sig') as f:
        csv_rows = list(csv.DictReader(f))
    with open(json_p, 'r', encoding='utf-8') as f:
        json_items = json.load(f)
        
    by_stem = {}
    duplicate_stems = []
    for it in json_items:
        st = norm_stem(it.get('title'))
        if st in by_stem:
            duplicate_stems.append(st)
        by_stem[st] = it
        
    matched = 0
    missing = []
    for r in csv_rows:
        st = norm_stem(r.get('Question_Text'))
        if st in by_stem:
            matched += 1
        else:
            missing.append(st[:50])
            
    print(f"{sub}: Total CSV={len(csv_rows)}, Matched by stem={matched}, Missing={len(missing)}, JSON duplicate stems={len(duplicate_stems)}")
    if missing:
        print(f"  Missing: {missing}")
