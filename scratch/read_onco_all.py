import sys
import csv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("final/onco/onco_all.csv", 'r', encoding='utf-8-sig') as f:
    r = csv.DictReader(f)
    for row in r:
        print(row['Question_ID'], "|", row['Medical_Subject'], "|", row['Chapter_or_Section'], "|", row['Question_Text'])
