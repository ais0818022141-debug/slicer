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
    
    by_id = {it['id']: it for it in json_items if 'id' in it}
    by_stem = {norm_stem(it['title']): it for it in json_items if 'title' in it}
    
    matched_id = 0
    matched_stem = 0
    unmatched = []
    
    for r in csv_rows:
        qid = r.get('Question_ID')
        st = norm_stem(r.get('Question_Text'))
        if qid in by_id:
            matched_id += 1
        elif st in by_stem:
            matched_stem += 1
        else:
            unmatched.append((qid, st[:40]))
            
    print(f"=== {sub} ({len(csv_rows)} rows) ===")
    print(f"  Matched by ID: {matched_id}")
    print(f"  Matched by Stem: {matched_stem}")
    print(f"  Unmatched: {len(unmatched)}")
    if unmatched:
        for u in unmatched:
            print(f"    Unmatched: {u}")
