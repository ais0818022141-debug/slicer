import json
import re

with open('final/obs/obs_all.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total questions: {len(data)}")
has_subsequent = 0
for idx, q in enumerate(data):
    exp = q['explanation']
    lines = [l.strip() for l in exp.split('\n') if l.strip()]
    if len(lines) > 1:
        has_subsequent += 1

print(f"Questions with subsequent lines: {has_subsequent}")
