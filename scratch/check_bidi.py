import json
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for sub in ['onco', 'plastic', 'ped_surgery']:
    with open(f'final/{sub}/{sub}_all.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n=== {sub} ===")
    for q in data:
        exp = q.get('explanation', '')
        # Check where an option code like B) or C) is preceded by latin characters
        # e.g. MEN2B. B) or RET. C) or TSH. B)
        matches = re.findall(r'([A-Za-z0-9_-]{2,}[\s.:\n]*[A-F]\))', exp)
        if matches:
            print(f"Question {q['id']}:")
            for m in matches:
                print(f"   Match: {repr(m)}")
