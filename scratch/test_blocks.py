import sys
import json
import re
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BLOCK_1_SUBJECTS = {'cardio', 'gastro', 'pulmo', 'hema', 'endo', 'rheuma', 'renal', 'peds1', 'peds'}
BLOCK_2_SUBJECTS = {'gync', 'obs', 'general_surgery', 'orthopedics', 'urology', 'thoracic_surgery',
                    'ped_surgery', 'neurosurgery', 'plastic', 'cardiac_surgery', 'vascular_surgery',
                    'onco', 'ent', 'optho'}

def norm_session(s):
    if not s:
        return 'غير محدد'
    s = re.sub(r'[\u0640]', '', s).strip()
    s = re.sub(r'\s+', ' ', s)
    m = re.search(r'((?:19|20)\d\d)', s)
    if not m:
        return s
    year = m.group(1)
    month = s.replace(year, '').strip()
    return f"{month} {year}"

final_dir = Path('final')
sessions_block_counts = defaultdict(lambda: {'b1': 0, 'b2': 0, 'b1_subjs': set(), 'b2_subjs': set(), 'total': 0})

for d in final_dir.iterdir():
    if not d.is_dir() or d.name.startswith('.'):
        continue
    jf = d / f"{d.name}_all.json"
    if not jf.exists():
        continue
    with open(jf, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for q in data:
        raw_ep = q.get('exam_period') or q.get('Exam_Date') or 'غير محدد'
        ep = norm_session(raw_ep)
        sessions_block_counts[ep]['total'] += 1
        if d.name in BLOCK_1_SUBJECTS:
            sessions_block_counts[ep]['b1'] += 1
            sessions_block_counts[ep]['b1_subjs'].add(d.name)
        elif d.name in BLOCK_2_SUBJECTS:
            sessions_block_counts[ep]['b2'] += 1
            sessions_block_counts[ep]['b2_subjs'].add(d.name)
        else:
            print(f"Unknown subject: {d.name}")

print(f"{'Session Name':20} | {'Block 1':8} | {'Block 2':8} | {'Total':8} | Status")
print("-" * 65)

for ep, c in sorted(sessions_block_counts.items()):
    status = "OK (Both Blocks)" if c['b1'] > 0 and c['b2'] > 0 else ("Only B1" if c['b1'] > 0 else "Only B2")
    print(f"{ep:20} | {c['b1']:8} | {c['b2']:8} | {c['total']:8} | {status}")
