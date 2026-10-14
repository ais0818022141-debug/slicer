import sys
import csv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def print_detail(title, row):
    print(f"[{title}]")
    for k, v in row.items():
        if v and k in ['Question_ID', 'Medical_Subject', 'Exam_Date', 'Chapter_or_Section', 'Question_Text', 'Correct_Answer', 'Wrong_Answer_1', 'Wrong_Answer_2', 'Wrong_Answer_3', 'Wrong_Answer_4']:
            print(f"  {k}: {v}")
    print()

headers = ['Question_ID','Medical_Subject','Exam_Date','Chapter_or_Section','Question_Text','Explanation','High_Yield_Note','Correct_Answer','Wrong_Answer_1','Wrong_Answer_2','Wrong_Answer_3','Wrong_Answer_4','Wrong_Answer_5']

with open("working_on/أسئلة دورات أورام.csv", 'r', encoding='utf-8-sig') as f:
    onco_work = [dict(zip(headers, r)) for r in csv.reader(f)]

with open("final/onco/onco_all.csv", 'r', encoding='utf-8-sig') as f:
    onco_final = {r['Question_ID']: r for r in csv.DictReader(f)}

with open("working_on/أسئلة دورات تجميلية.csv", 'r', encoding='utf-8-sig') as f:
    plastic_work = [dict(zip(headers, r)) for r in csv.reader(f)]

with open("final/plastic/plastic_all.csv", 'r', encoding='utf-8-sig') as f:
    plastic_final = {r['Question_ID']: r for r in csv.DictReader(f)}

print("=== COMPARING PAIR 1: q_general_surgery_056 vs q_onco_05 ===")
print_detail("Working On 056", onco_work[2])
print_detail("Final onco_05", onco_final['q_onco_05'])

print("=== COMPARING PAIR 2: q_general_surgery_057 vs q_onco_07 ===")
print_detail("Working On 057", onco_work[3])
print_detail("Final onco_07", onco_final['q_onco_07'])

print("=== COMPARING PAIR 3: q_general_surgery_063 vs q_onco_08 & 10 ===")
print_detail("Working On 063", onco_work[9])
print_detail("Final onco_08", onco_final['q_onco_08'])
print_detail("Final onco_10", onco_final['q_onco_10'])

print("=== COMPARING PAIR 4: q_general_surgery_024 vs q_plastic_54 & 57 ===")
print_detail("Working On 024", plastic_work[2])
print_detail("Final plastic_54", plastic_final['q_plastic_54'])
print_detail("Final plastic_57", plastic_final['q_plastic_57'])
