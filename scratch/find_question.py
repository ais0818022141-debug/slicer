import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('final/onco/onco_all.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

for idx, it in enumerate(items, 1):
    exp = it.get('explanation', '')
    if 'نظراً لميله للغزو الوعائي' in exp:
        print(f"Index: #{idx}, ID: {it.get('id')}")
        print("Question:", it.get('title'))
        print("Correct Option:", it.get('correct_option'))
        print("Explanation:")
        print(exp)
        print("="*60)
