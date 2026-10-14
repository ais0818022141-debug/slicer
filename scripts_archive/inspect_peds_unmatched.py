import json
import re

with open('final/peds/peds_all.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('scratch_peds_unmatched.txt', 'w', encoding='utf-8') as out:
    for idx, q in enumerate(data):
        exp = q.get('explanation', '')
        if 'الإجابة الصحيحة' in exp:
            out.write(f"=== Q{idx+1} ===\n")
            out.write(exp[:200] + "\n\n")
