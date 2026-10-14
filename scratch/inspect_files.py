import sys
import csv
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def inspect(path):
    print(f"=== {path.name} ===")
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.reader(f)
        rows = list(reader)
    print("Total rows:", len(rows))
    for i, r in enumerate(rows):
        print(f"[{i}] len={len(r)} id={r[0]} subj={r[1] if len(r)>1 else ''} date={r[2] if len(r)>2 else ''} topic={r[3] if len(r)>3 else ''} q={r[4][:40] if len(r)>4 else ''}")

print("WORKING ON:")
inspect(Path("working_on/أسئلة دورات أورام.csv"))
inspect(Path("working_on/أسئلة دورات تجميلية.csv"))

print("\nFINAL ONCO TOPICS:")
with open("final/onco/onco_all.csv", 'r', encoding='utf-8-sig') as f:
    r = csv.DictReader(f)
    onco_rows = list(r)
    print("Total onco rows:", len(onco_rows))
    topics = set(row.get("Chapter_or_Section") for row in onco_rows)
    print("Topics:", topics)
    subjs = set(row.get("Medical_Subject") for row in onco_rows)
    print("Subjects:", subjs)

print("\nFINAL PLASTIC TOPICS:")
with open("final/plastic/plastic_all.csv", 'r', encoding='utf-8-sig') as f:
    r = csv.DictReader(f)
    plastic_rows = list(r)
    print("Total plastic rows:", len(plastic_rows))
    topics = set(row.get("Chapter_or_Section") for row in plastic_rows)
    print("Topics:", topics)
    subjs = set(row.get("Medical_Subject") for row in plastic_rows)
    print("Subjects:", subjs)
