# -*- coding: utf-8 -*-
import json

with open('final/onco/onco_all.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

with open('scratch/out_exp_utf8.txt', 'w', encoding='utf-8') as out:
    for idx, q in enumerate(items[:6], 1):
        out.write(f"=== Q{idx} ({q['id']}) ===\n")
        out.write(q.get('explanation', '') + "\n\n")

print("Done")
