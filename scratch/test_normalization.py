import os
import sys
import json
import re
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

def normalize_session_name(s):
    if not s:
        return ""
    # remove tatweel
    s = re.sub(r'[\u0640]', '', s)
    # normalize spaces
    s = re.sub(r'\s+', ' ', s).strip()
    
    # Extract year (4 digits)
    m = re.search(r'((?:19|20)\d\d)', s)
    if not m:
        return s
    year = m.group(1)
    
    # Extract non-year part
    non_year = s.replace(year, '').strip()
    
    # Normalize month/period names
    month = non_year
    # remove prefixes like دورة or فصل if needed, or see what exists
    # let's see what combinations exist
    return f"{month} {year}"

final_dir = Path('final')
subjects = sorted([d for d in final_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])

normalized_sessions = defaultdict(lambda: defaultdict(int))
raw_mapping = defaultdict(set)

for subj_dir in subjects:
    jfile = subj_dir / f"{subj_dir.name}_all.json"
    if not jfile.exists():
        continue
    with open(jfile, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for q in data:
        raw_ep = q.get('exam_period') or q.get('Exam_Date') or 'غير محدد'
        norm_ep = normalize_session_name(raw_ep)
        normalized_sessions[norm_ep][subj_dir.name] += 1
        raw_mapping[norm_ep].add(raw_ep)

print("=== NORMALIZED EXAM SESSIONS ===")
for ep, counts in sorted(normalized_sessions.items()):
    tot = sum(counts.values())
    raws = list(raw_mapping[ep])
    print(f"\nSession: [{ep}] (Raw: {raws}) -> Total: {tot} questions, {len(counts)} subjects")
    subjs_with_count = [f"{s}:{c}" for s, c in sorted(counts.items())]
    print("  " + ", ".join(subjs_with_count))
