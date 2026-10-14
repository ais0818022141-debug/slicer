import json
import csv
from pathlib import Path

def compare(sub):
    csv_file = Path(f'final/{sub}/{sub}_all.csv')
    json_file = Path(f'final/{sub}/{sub}_all.json')
    if not csv_file.exists() or not json_file.exists():
        print(f"Skipping {sub}: file not found")
        return
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        csv_rows = list(csv.DictReader(f))
    with open(json_file, 'r', encoding='utf-8') as f:
        json_rows = json.load(f)
    print(f'=== {sub} ===')
    print(f'CSV count: {len(csv_rows)}, JSON count: {len(json_rows)}')
    
    diffs = 0
    for i, (cr, jr) in enumerate(zip(csv_rows, json_rows)):
        c_title = cr.get('Question_Text', '').strip()
        j_title = jr.get('title', '').strip()
        c_exp = (cr.get('Explanation') or '').strip()
        j_exp = (jr.get('explanation') or '').strip()
        c_hy = (cr.get('High_Yield_Note') or '').strip()
        j_hy = (jr.get('high_yield_note') or '').strip()
        c_sec = (cr.get('Chapter_or_Section') or '').strip()
        j_sec = (jr.get('topic_name') or '').strip()
        c_cor = (cr.get('Correct_Answer') or '').strip()
        
        # Check correct answer in json
        j_cor = ""
        for opt in jr.get('options', []):
            if opt.get('is_correct'):
                j_cor = opt.get('text', '').strip()
                break

        diff_fields = []
        if c_title.rstrip(':') != j_title.rstrip(':'): diff_fields.append('title')
        if c_sec != j_sec: diff_fields.append('topic')
        if c_exp != j_exp: diff_fields.append('explanation')
        if c_hy != j_hy: diff_fields.append('high_yield_note')
        if c_cor.rstrip('.') != j_cor.rstrip('.'): diff_fields.append('correct_answer')
        
        if diff_fields:
            diffs += 1
            if diffs <= 5:
                qid = cr.get('Question_ID') or cr.get('\ufeffQuestion_ID')
                print(f'  Row {i+1} ({qid}): diff in {diff_fields}')
                for fld in diff_fields:
                    if fld == 'correct_answer':
                        print(f'    [CSV cor]: {c_cor}')
                        print(f'    [JSON cor]: {j_cor}')
                    elif fld == 'title':
                        print(f'    [CSV title]: {c_title}')
                        print(f'    [JSON title]: {j_title}')
                    elif fld == 'topic':
                        print(f'    [CSV topic]: {c_sec}')
                        print(f'    [JSON topic]: {j_sec}')
                    elif fld == 'explanation':
                        print(f'    [CSV exp]: {c_exp[:60]}...')
                        print(f'    [JSON exp]: {j_exp[:60]}...')
    print(f'Total diffs in {sub}: {diffs}\n')

for s in ['orthopedics', 'urology', 'pulmo', 'rheuma', 'ent']:
    compare(s)
