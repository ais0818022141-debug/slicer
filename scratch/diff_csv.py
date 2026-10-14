import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def compare_csv(curr_path, backup_path):
    print(f"\n=======================================================")
    print(f"Comparing {curr_path.name} with {backup_path.name}")
    print(f"=======================================================")
    with open(curr_path, 'r', encoding='utf-8-sig') as f:
        curr_rows = list(csv.DictReader(f))
    with open(backup_path, 'r', encoding='utf-8-sig') as f:
        back_rows = list(csv.DictReader(f))
    
    print(f"Current rows: {len(curr_rows)} | Backup rows: {len(back_rows)}")
    curr_ids = [r.get('Question_ID') for r in curr_rows]
    back_ids = [r.get('Question_ID') for r in back_rows]
    
    curr_id_set = set(curr_ids)
    back_id_set = set(back_ids)
    
    added = curr_id_set - back_id_set
    removed = back_id_set - curr_id_set
    print(f"Added IDs count: {len(added)}: {list(added)[:5]}")
    print(f"Removed IDs count: {len(removed)}: {list(removed)[:5]}")
    
    # Check topics
    curr_topics = set(r.get('Chapter_or_Section') for r in curr_rows)
    back_topics = set(r.get('Chapter_or_Section') for r in back_rows)
    print(f"Current topics ({len(curr_topics)}): {curr_topics}")
    print(f"Backup topics ({len(back_topics)}): {back_topics}")

compare_csv(
    Path('final/plastic/plastic_all.csv'),
    Path('final/plastic/.backup/plastic_all_20260929_165900.csv')
)

compare_csv(
    Path('final/onco/onco_all.csv'),
    Path('final/onco/.backup/onco_all_20260929_165934.csv')
)

compare_csv(
    Path('final/ped_surgery/ped_surgery_all.csv'),
    Path('final/ped_surgery/.backup/ped_surgery_all_20260929_165832.csv')
)
