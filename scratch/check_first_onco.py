import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('final/onco/onco_all.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for q in data[:4]:
    print(f"=== {q['id']} ===")
    print(repr(q['explanation']))
    print("---")
    print(q['explanation'])
