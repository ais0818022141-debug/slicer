import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('final/plastic/plastic_all.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

for q in items:
    if q['id'] in ['q_plastic_45', 'q_plastic_39']:
        print(f"=== {q['id']} ===")
        print(repr(q['explanation']))
        print("---")
        print(q['explanation'])
