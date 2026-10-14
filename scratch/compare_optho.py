import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

csv_path = Path(r"final\optho\optho_all.csv")
json_path = Path(r"final\optho\optho_all.json")

with open(json_path, 'r', encoding='utf-8') as f:
    json_data = json.load(f)

for enc in ['utf-8-sig', 'utf-8']:
    try:
        with open(csv_path, 'r', encoding=enc) as f:
            csv_rows = list(csv.DictReader(f))
            break
    except Exception:
        pass

json_by_id = {q['id']: q for q in json_data}

differences = []
for idx, r in enumerate(csv_rows):
    qid = r.get('Question_ID') or r.get('\ufeffQuestion_ID')
    if qid not in json_by_id:
        differences.append(f"NEW QUESTION: {qid} (row {idx+1}): {r.get('Question_Text', '')[:60]}")
        continue
    
    jq = json_by_id[qid]
    
    # Check stem
    csv_stem = (r.get('Question_Text') or '').strip()
    json_stem = (jq.get('title') or '').strip()
    if csv_stem != json_stem:
        differences.append(f"{qid} stem changed:\n  CSV:  {csv_stem}\n  JSON: {json_stem}")
        
    # Check topic
    csv_topic = (r.get('Chapter_or_Section') or '').strip()
    json_topic = (jq.get('topic_name') or '').strip()
    if csv_topic != json_topic:
        differences.append(f"{qid} topic changed: CSV='{csv_topic}' vs JSON='{json_topic}'")
        
    # Check exam_date
    csv_date = (r.get('Exam_Date') or '').strip()
    json_date = (jq.get('exam_period') or '').strip()
    if csv_date != json_date:
        differences.append(f"{qid} exam_date changed: CSV='{csv_date}' vs JSON='{json_date}'")
        
    # Check explanation
    csv_exp = (r.get('Explanation') or '').strip()
    json_exp = (jq.get('explanation') or '').strip()
    if csv_exp != json_exp:
        differences.append(f"{qid} explanation changed:\n  CSV:  {csv_exp[:60]}...\n  JSON: {json_exp[:60]}...")

    # Check high_yield
    csv_hy = (r.get('High_Yield_Note') or '').strip()
    json_hy = (jq.get('high_yield_note') or '').strip()
    if csv_hy != json_hy:
        differences.append(f"{qid} high_yield changed: CSV='{csv_hy[:50]}' vs JSON='{json_hy[:50]}'")

    # Check options
    correct_csv = (r.get('Correct_Answer') or '').strip()
    csv_wrongs = [r.get(f'Wrong_Answer_{i}', '').strip() for i in range(1, 6) if r.get(f'Wrong_Answer_{i}', '').strip()]
    
    json_correct = next((o['text'].strip() for o in jq.get('options', []) if o.get('is_correct')), '')
    json_wrongs = [o['text'].strip() for o in jq.get('options', []) if not o.get('is_correct')]
    
    if correct_csv != json_correct:
        differences.append(f"{qid} correct answer changed:\n  CSV:  '{correct_csv}'\n  JSON: '{json_correct}'")
        
    if csv_wrongs != json_wrongs:
        differences.append(f"{qid} wrong answers changed:\n  CSV:  {csv_wrongs}\n  JSON: {json_wrongs}")

print(f"Total modified/new items found: {len(differences)}")
for d in differences:
    print("---")
    print(d)
