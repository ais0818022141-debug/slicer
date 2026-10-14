import os
import sys
import json
import re
from pathlib import Path
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding='utf-8')

final_dir = Path('final')
subjects = sorted([d for d in final_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])

print(f"Total subjects in final/: {len(subjects)}")

# Let's inspect manifest.json
manifest_file = final_dir / 'manifest.json'
manifest = {}
if manifest_file.exists():
    with open(manifest_file, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

print(f"Manifest subjects count: {len(manifest.get('subjects', {}))}")

# Check subjects details
all_exam_periods = defaultdict(lambda: defaultdict(int))
subject_metadata = {}

total_questions = 0

for subj_dir in subjects:
    jfile = subj_dir / f"{subj_dir.name}_all.json"
    if not jfile.exists():
        # check any *_all.json
        cands = list(subj_dir.glob("*_all.json"))
        if cands:
            jfile = cands[0]
        else:
            print(f"WARNING: No json file for {subj_dir.name}")
            continue

    with open(jfile, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_questions += len(data)
    manifest_info = manifest.get('subjects', {}).get(subj_dir.name, {})
    subj_name_arabic = manifest_info.get('subject_name')
    if not subj_name_arabic and len(data) > 0:
        subj_name_arabic = data[0].get('subject_name', subj_dir.name)

    subject_metadata[subj_dir.name] = {
        'arabic_name': subj_name_arabic,
        'count': len(data),
        'json_path': str(jfile)
    }

    for q in data:
        ep = q.get('exam_period') or q.get('Exam_Date') or 'غير محدد'
        all_exam_periods[ep][subj_dir.name] += 1

print(f"Total questions found across all subjects: {total_questions}")

print("\n--- All Subjects Summary ---")
for code, meta in sorted(subject_metadata.items()):
    print(f"{code:18} | {meta['arabic_name']:20} | {meta['count']} questions")

print("\n--- All Unique exam_period values ---")
for ep, counts in sorted(all_exam_periods.items(), key=lambda x: str(x[0])):
    tot = sum(counts.values())
    subjs_with_count = [f"{s}:{c}" for s, c in sorted(counts.items())]
    print(f"\nPeriod: [{ep}] (Total: {tot} questions, {len(counts)} subjects)")
    print("  " + ", ".join(subjs_with_count))
