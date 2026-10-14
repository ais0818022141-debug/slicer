import sys
import csv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("working_on/أسئلة دورات أورام.csv", 'r', encoding='utf-8-sig') as f:
    r = csv.reader(f)
    for i, row in enumerate(r):
        print(f"--- Q{i+1} ---")
        print("ID:", row[0])
        print("Subject:", row[1])
        print("Date:", row[2])
        print("Topic:", row[3])
        print("Question:", row[4])
        print("Answer:", row[7])
