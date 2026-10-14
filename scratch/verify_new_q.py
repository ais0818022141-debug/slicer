import sys
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r"final\optho\optho_all.json", 'r', encoding='utf-8') as f:
    items = json.load(f)

for q in items:
    if q['id'] in ['q_optho_191', 'q_optho_192']:
        print(f"================ {q['id']} ================")
        print("Title:", q['title'])
        print("Topic:", q['topic_name'])
        print("Date:", q['exam_period'])
        print("Correct Option:", q['correct_option'])
        print("Objective:", q['educational_objective'])
        print("High Yield:", q['high_yield_note'])
        print("Explanation:", q['explanation'][:100] + "...")
        print("Options:")
        for o in q['options']:
            print(f"  [{o['letter']}] {o['text']} {'(CORRECT)' if o['is_correct'] else ''}")
