import sys
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r"final\optho\optho_all.json", 'r', encoding='utf-8') as f:
    json_data = json.load(f)

json_by_id = {q['id']: q for q in json_data}

for qid in ['q_optho_141', 'q_optho_142', 'q_optho_143']:
    q = json_by_id[qid]
    print(f"=== {qid} ===")
    print("Explanation:")
    print(q.get('explanation'))
    print("High Yield:")
    print(q.get('high_yield_note'))
    print("Objective:")
    print(q.get('educational_objective'))
