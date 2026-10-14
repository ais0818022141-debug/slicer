# -*- coding: utf-8 -*-
import json
import codecs

with open('final/onco/onco_all.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

for idx, q in enumerate(items[:6], 1):
    print(f"=== Q{idx} ({q['id']}) ===")
    print(q.get('explanation', ''))
