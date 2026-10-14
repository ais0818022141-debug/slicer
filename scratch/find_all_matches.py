import sys
import csv
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def clean(s):
    import re
    return re.sub(r'[\s\.:：،,\(\)\[\]؟?]+', '', s or '')

# Load all questions across final/
final_questions = []
final_dir = Path("final")
for csv_file in final_dir.glob("*/*_all.csv"):
    subj_folder = csv_file.parent.name
    with open(csv_file, 'r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            final_questions.append({
                'subj_folder': subj_folder,
                'id': row.get('Question_ID'),
                'subject': row.get('Medical_Subject'),
                'topic': row.get('Chapter_or_Section'),
                'date': row.get('Exam_Date'),
                'text': row.get('Question_Text', ''),
                'correct': row.get('Correct_Answer', '')
            })

print(f"Total questions in final: {len(final_questions)}")

# Check working_on onco
print("\n================== CHECKING ONCO QUESTIONS ==================")
with open("working_on/أسئلة دورات أورام.csv", 'r', encoding='utf-8-sig') as f:
    for i, r in enumerate(csv.reader(f)):
        q_id = r[0]
        q_text = r[4]
        q_clean = clean(q_text)
        matches = []
        for fq in final_questions:
            # check exact or substring or clean match
            fc = clean(fq['text'])
            if q_clean in fc or fc in q_clean or (len(q_clean) > 20 and q_clean[:25] in fc):
                matches.append(fq)
        print(f"\n[Onco Row {i+1}] {q_id} ({r[2]}) {q_text[:40]}...")
        if matches:
            print(f"   -> FOUND {len(matches)} MATCH(ES):")
            for m in matches:
                print(f"      * [{m['subj_folder']}] {m['id']} ({m['date']}) {m['topic']} | {m['text'][:40]}")
        else:
            print("   -> NO MATCH FOUND in final.")

# Check working_on plastic
print("\n================== CHECKING PLASTIC QUESTIONS ==================")
with open("working_on/أسئلة دورات تجميلية.csv", 'r', encoding='utf-8-sig') as f:
    for i, r in enumerate(csv.reader(f)):
        q_id = r[0]
        q_text = r[4]
        q_clean = clean(q_text)
        matches = []
        for fq in final_questions:
            fc = clean(fq['text'])
            if q_clean in fc or fc in q_clean or (len(q_clean) > 20 and q_clean[:25] in fc):
                matches.append(fq)
        print(f"\n[Plastic Row {i+1}] {q_id} ({r[2]}) {q_text[:40]}...")
        if matches:
            print(f"   -> FOUND {len(matches)} MATCH(ES):")
            for m in matches:
                print(f"      * [{m['subj_folder']}] {m['id']} ({m['date']}) {m['topic']} | {m['text'][:40]}")
        else:
            print("   -> NO MATCH FOUND in final.")
