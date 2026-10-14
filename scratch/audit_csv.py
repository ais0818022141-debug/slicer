import sys
import csv
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

csv_path = Path(r"final\optho\optho_all.csv")
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

print(f"Total rows in CSV: {len(rows)}")

seen_ids = set()
for idx, r in enumerate(rows, start=1):
    qid = r.get('Question_ID') or r.get('\ufeffQuestion_ID') or f"row_{idx}"
    if not qid:
        print(f"[!] Row {idx} has NO Question_ID!")
    elif qid in seen_ids:
        print(f"[!] Row {idx} has DUPLICATE Question_ID: {qid}!")
    seen_ids.add(qid)

    stem = (r.get('Question_Text') or '').strip()
    if not stem:
        print(f"[!] Row {idx} ({qid}) has EMPTY Question_Text!")

    correct = (r.get('Correct_Answer') or '').strip()
    if not correct:
        print(f"[!] Row {idx} ({qid}) has EMPTY Correct_Answer!")

    wrongs = [r.get(f'Wrong_Answer_{i}', '').strip() for i in range(1, 6) if r.get(f'Wrong_Answer_{i}', '').strip()]
    if len(wrongs) < 2:
        print(f"[!] Row {idx} ({qid}) has only {len(wrongs)} wrong answers!")

    # Check for duplicate options within the same question
    all_opts = [correct] + wrongs
    if len(all_opts) != len(set(all_opts)):
        print(f"[!] Row {idx} ({qid}) has DUPLICATE options inside question: {all_opts}")

    exp = (r.get('Explanation') or '').strip()
    if not exp:
        print(f"[!] Row {idx} ({qid}) has EMPTY Explanation!")
    elif '#NAME?' in exp:
        print(f"[*] Row {idx} ({qid}) has #NAME? in Explanation (needs repair)")

print("[✓] Audit complete.")
