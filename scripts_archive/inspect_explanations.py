import json
import os

subjects = ['cardio', 'endo', 'gastro', 'renal', 'hema', 'rheuma', 'gync', 'obs', 'peds', 'peds1']

report = []
for s in subjects:
    p = f'final/{s}/{s}_all.json'
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    report.append(f"=== SUBJECT: {s} (count: {len(data)}) ===")
    for idx, q in enumerate(data[:4]):
        exp = q.get('explanation', '')
        # show first 250 chars of explanation
        first_lines = exp[:300].replace('\n', ' \\n ')
        report.append(f"  Q{idx+1}: {first_lines}")

with open('scratch_explanations_sample.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print("Wrote sample to scratch_explanations_sample.txt")
