import sys
import json
import csv
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r"final\optho\optho_all.json", 'r', encoding='utf-8') as f:
    j_items = {q['id']: q for q in json.load(f)}

with open(r"final\optho\optho_all.csv", 'r', encoding='utf-8-sig') as f:
    c_items = {r['Question_ID']: r for r in csv.DictReader(f)}

for qid in ['q_optho_141', 'q_optho_142', 'q_optho_143']:
    print(f"=== {qid} ===")
    print("CSV Explanation start:", repr(c_items[qid]['Explanation'][:50]))
    print("JSON Explanation start:", repr(j_items[qid]['explanation'][:50]))
