import sys
import csv
import json
import re
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OPTHO_DIR = Path(r"final\optho")
MANIFEST_PATH = Path(r"final\manifest.json")

errors = []

# 1. Verify CSV
csv_path = OPTHO_DIR / "optho_all.csv"
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    csv_rows = list(csv.DictReader(f))

if len(csv_rows) != 192:
    errors.append(f"CSV row count is {len(csv_rows)}, expected 192")

for idx, r in enumerate(csv_rows, 1):
    for col, val in r.items():
        if val and '#NAME?' in val:
            errors.append(f"CSV row {idx} ({r.get('Question_ID')}) col '{col}' still has #NAME?")

# 2. Verify JSON
json_path = OPTHO_DIR / "optho_all.json"
with open(json_path, 'r', encoding='utf-8') as f:
    json_items = json.load(f)

if len(json_items) != 192:
    errors.append(f"JSON item count is {len(json_items)}, expected 192")

json_ids = [q['id'] for q in json_items]
if len(json_ids) != len(set(json_ids)):
    errors.append("Duplicate IDs found in JSON!")

for idx, q in enumerate(json_items, 1):
    qid = q.get('id')
    opts = q.get('options', [])
    if not opts:
        errors.append(f"JSON item {idx} ({qid}) has NO options!")
    cor_opts = [o for o in opts if o.get('is_correct')]
    if len(cor_opts) != 1:
        errors.append(f"JSON item {idx} ({qid}) has {len(cor_opts)} correct options (expected 1)!")
    cor_let = q.get('correct_option')
    if not cor_let or cor_let != cor_opts[0].get('letter'):
        errors.append(f"JSON item {idx} ({qid}) correct_option '{cor_let}' doesn't match option letter '{cor_opts[0].get('letter')}'!")

# 3. Verify AI MD
ai_md_path = OPTHO_DIR / "optho_all_ai.md"
with open(ai_md_path, 'r', encoding='utf-8') as f:
    ai_md_text = f.read()
ai_blocks = re.findall(r'^#\d+ \[q_optho_\d+\]', ai_md_text, re.MULTILINE)
if len(ai_blocks) != 192:
    errors.append(f"optho_all_ai.md has {len(ai_blocks)} blocks, expected 192")

# 4. Verify AI Temp MD
temp_md_path = OPTHO_DIR / "optho_all_ai_temp.md"
with open(temp_md_path, 'r', encoding='utf-8') as f:
    temp_md_text = f.read()
temp_blocks = re.findall(r'^#\d+ \[q_optho_\d+\]', temp_md_text, re.MULTILINE)
if len(temp_blocks) != 192:
    errors.append(f"optho_all_ai_temp.md has {len(temp_blocks)} blocks, expected 192")

# 5. Verify explanations.txt
exp_txt_path = OPTHO_DIR / "explanations.txt"
with open(exp_txt_path, 'r', encoding='utf-8') as f:
    exp_text = f.read()
exp_headers = re.findall(r'^#\d+', exp_text, re.MULTILINE)
if len(exp_headers) != 192:
    errors.append(f"explanations.txt has {len(exp_headers)} headers, expected 192")

# 6. Verify manifest.json
with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
    manifest = json.load(f)
optho_manifest = manifest.get('subjects', {}).get('optho', {})
if optho_manifest.get('questions_count') != 192:
    errors.append(f"manifest.json optho questions_count is {optho_manifest.get('questions_count')}, expected 192")
if len(optho_manifest.get('topics', [])) != 6:
    errors.append(f"manifest.json optho topics count is {len(optho_manifest.get('topics', []))}, expected 6")

# 7. Verify HTML files
master_htmls = ["optho_all.html", "optho_all_topics.html", "optho_all_sessions.html"]
for h in master_htmls:
    hp = OPTHO_DIR / h
    if not hp.exists():
        errors.append(f"Master HTML missing: {h}")
    else:
        with open(hp, 'r', encoding='utf-8') as f:
            content = f.read()
        q_cards = len(re.findall(r'class="question-card', content))
        if q_cards != 192:
            errors.append(f"{h} has {q_cards} question cards, expected 192!")

topic_htmls = list((OPTHO_DIR / "topics").glob("*.html"))
if len(topic_htmls) != 6:
    errors.append(f"topics/ has {len(topic_htmls)} HTML files, expected 6")

session_htmls = list((OPTHO_DIR / "sessions").glob("*.html"))
if len(session_htmls) != 16:
    errors.append(f"sessions/ has {len(session_htmls)} HTML files, expected 16")

year_htmls = list((OPTHO_DIR / "years").glob("*.html"))
if len(year_htmls) != 9:
    errors.append(f"years/ has {len(year_htmls)} HTML files, expected 9")

# Print verification report
print("================ VERIFICATION REPORT ================")
if errors:
    print(f"[FAILED] Found {len(errors)} issues:")
    for e in errors:
        print("  -", e)
else:
    print("[SUCCESS] ALL 7 CHECKS PASSED PERFECTLY!")
    print(f"  ✓ CSV questions: {len(csv_rows)} (repaired, normalized)")
    print(f"  ✓ JSON questions: {len(json_items)} (192 items, all valid)")
    print(f"  ✓ AI Markdown: {len(ai_blocks)} blocks")
    print(f"  ✓ AI Temp Markdown: {len(temp_blocks)} blocks")
    print(f"  ✓ Explanations text: {len(exp_headers)} items (#01 to #192)")
    print(f"  ✓ Manifest optho count: {optho_manifest.get('questions_count')} (Total questions: {manifest.get('total_questions')})")
    print(f"  ✓ Master HTMLs cards: 192 questions each")
    print(f"  ✓ Topics packages: {len(topic_htmls)} HTML files")
    print(f"  ✓ Sessions packages: {len(session_htmls)} HTML files")
    print(f"  ✓ Years packages: {len(year_htmls)} HTML files")
