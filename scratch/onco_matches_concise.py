import sys
import csv
import difflib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

headers = ['Question_ID','Medical_Subject','Exam_Date','Chapter_or_Section','Question_Text','Explanation','High_Yield_Note','Correct_Answer','Wrong_Answer_1','Wrong_Answer_2','Wrong_Answer_3','Wrong_Answer_4','Wrong_Answer_5']

with open("working_on/أسئلة دورات أورام.csv", 'r', encoding='utf-8-sig') as f:
    onco_work = [dict(zip(headers, r)) for r in csv.reader(f)]

with open("final/onco/onco_all.csv", 'r', encoding='utf-8-sig') as f:
    onco_final = list(csv.DictReader(f))

for i, w in enumerate(onco_work):
    print(f"[{i+1}] {w['Question_ID']} | {w['Exam_Date']} | {w['Question_Text'][:50]} | Ans: {w['Correct_Answer']}")
    matches = []
    for f in onco_final:
        q_ratio = difflib.SequenceMatcher(None, w['Question_Text'], f['Question_Text']).ratio()
        a_ratio = difflib.SequenceMatcher(None, w['Correct_Answer'], f['Correct_Answer']).ratio()
        if q_ratio > 0.45 or a_ratio > 0.6:
            matches.append((f, q_ratio, a_ratio))
    if matches:
        for f, qr, ar in matches:
            print(f"    -> MATCH with {f['Question_ID']} ({f['Exam_Date']}) [Q:{qr:.2f}, A:{ar:.2f}]: {f['Question_Text'][:50]} | Ans: {f['Correct_Answer']}")
    else:
        print("    -> Distinct (no close duplicate)")
