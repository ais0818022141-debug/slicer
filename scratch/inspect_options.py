import sys
import csv
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r"final\optho\optho_all.json", 'r', encoding='utf-8') as f:
    json_data = json.load(f)
json_by_id = {q['id']: q for q in json_data}

with open(r"final\optho\optho_all.csv", 'r', encoding='utf-8-sig') as f:
    csv_rows = list(csv.DictReader(f))

test_ids = ['q_optho_008', 'q_optho_043', 'q_optho_137', 'q_optho_144', 'q_optho_160', 'q_optho_180']
for qid in test_ids:
    row = next(r for r in csv_rows if (r.get('Question_ID') or r.get('\ufeffQuestion_ID')) == qid)
    jq = json_by_id[qid]
    print(f"================== {qid} ==================")
    print("CSV:")
    print("  Correct:", repr(row.get('Correct_Answer')))
    for i in range(1, 6):
        w = row.get(f'Wrong_Answer_{i}')
        if w:
            print(f"  Wrong_{i}:", repr(w))
    print("JSON:")
    print("  Correct Letter:", jq.get('correct_option'))
    for opt in jq.get('options', []):
        mark = " (CORRECT)" if opt.get('is_correct') else ""
        print(f"  [{opt.get('letter')}]: {repr(opt.get('text'))}{mark}")
