import sys
import csv
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=== ALL FINAL ONCO QUESTIONS ===")
with open("final/onco/onco_all.csv", 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        print(f"{r['Question_ID']} | {r['Exam_Date']} | {r['Question_Text'][:60]}")

print("\n=== ALL WORKING ON ONCO QUESTIONS ===")
with open("working_on/أسئلة دورات أورام.csv", 'r', encoding='utf-8-sig') as f:
    r = csv.reader(f)
    for i, row in enumerate(r):
        print(f"[{i}] {row[0]} | {row[2]} | {row[3]} | {row[4][:60]}")

print("\n=== ALL FINAL PLASTIC QUESTIONS (Count: ) ===")
with open("final/plastic/plastic_all.csv", 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
    print(f"Total: {len(rows)}")
    for r in rows:
        if "جلد" in r['Chapter_or_Section']:
            print(f"{r['Question_ID']} | {r['Chapter_or_Section']} | {r['Question_Text'][:60]}")

print("\n=== ALL WORKING ON PLASTIC QUESTIONS ===")
with open("working_on/أسئلة دورات تجميلية.csv", 'r', encoding='utf-8-sig') as f:
    r = csv.reader(f)
    for i, row in enumerate(r):
        print(f"[{i}] {row[0]} | {row[2]} | {row[3]} | {row[4][:60]}")
