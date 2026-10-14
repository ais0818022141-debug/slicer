import sys
import csv
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=== ALL FINAL ONCO QUESTIONS ===")
with open("final/onco/onco_all.csv", 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        print(r['Question_ID'], "::", r['Exam_Date'], "::", r['Question_Text'][:70])
