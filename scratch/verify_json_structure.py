import os
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

final_dir = Path('final')
subjects = sorted([d for d in final_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])

for d in subjects:
    jf = d / f"{d.name}_all.json"
    if not jf.exists():
        print(f"Missing {jf}")
        continue
    with open(jf, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data:
        print(f"Empty {jf}")
        continue
    sample = data[0]
    keys = set(sample.keys())
    has_options = 'options' in sample and isinstance(sample['options'], list)
    opt_len = len(sample['options']) if has_options else 0
    print(f"{d.name:18} | Qs: {len(data):4} | keys: {len(keys):2} | sample options: {opt_len}")
