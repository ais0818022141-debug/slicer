import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('final/onco/onco_all.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

for q in items:
    if q['id'] in ['q_onco_04', 'q_onco_06', 'q_onco_24']:
        print(f"=== {q['id']} ===")
        print(q['explanation'])
