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

with open("working_on/أسئلة دورات تجميلية.csv", 'r', encoding='utf-8-sig') as f:
    plastic_work = [dict(zip(headers, r)) for r in csv.reader(f)]

with open("final/plastic/plastic_all.csv", 'r', encoding='utf-8-sig') as f:
    plastic_final = list(csv.DictReader(f))

print("=== ONCO ANALYSIS ===")
for i, w in enumerate(onco_work):
    print(f"\n[{i+1}] {w['Question_ID']} | Session: {w['Exam_Date']}")
    print(f"    Q: {w['Question_Text']}")
    print(f"    Ans: {w['Correct_Answer']}")
    # Compare with each final question
    for f in onco_final:
        # Check topic similarity
        ratio = difflib.SequenceMatcher(None, w['Question_Text'], f['Question_Text']).ratio()
        ans_ratio = difflib.SequenceMatcher(None, w['Correct_Answer'], f['Correct_Answer']).ratio()
        if ratio > 0.4 or ans_ratio > 0.5:
            print(f"    -> Compare with {f['Question_ID']} ({f['Exam_Date']}) [Q_sim: {ratio:.2f}, Ans_sim: {ans_ratio:.2f}]:")
            print(f"       Q_final: {f['Question_Text']}")
            print(f"       Ans_final: {f['Correct_Answer']}")

print("\n\n=== PLASTIC ANALYSIS ===")
for i, w in enumerate(plastic_work):
    print(f"\n[{i+1}] {w['Question_ID']} | Session: {w['Exam_Date']}")
    print(f"    Q: {w['Question_Text']}")
    print(f"    Ans: {w['Correct_Answer']}")
    for f in plastic_final:
        ratio = difflib.SequenceMatcher(None, w['Question_Text'], f['Question_Text']).ratio()
        ans_ratio = difflib.SequenceMatcher(None, w['Correct_Answer'], f['Correct_Answer']).ratio()
        if ratio > 0.4 or ans_ratio > 0.5:
            print(f"    -> Compare with {f['Question_ID']} ({f['Exam_Date']}) [Q_sim: {ratio:.2f}, Ans_sim: {ans_ratio:.2f}]:")
            print(f"       Q_final: {f['Question_Text']}")
            print(f"       Ans_final: {f['Correct_Answer']}")
