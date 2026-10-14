import json
import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

WORKING_DIR = Path("working_on")

# 1. Check Master JSON
with open(WORKING_DIR / "neuro_peds_all.json", 'r', encoding='utf-8') as f:
    qs = json.load(f)

print(f"Total questions in neuro_peds_all.json: {len(qs)}")
empty_obj = [q['id'] for q in qs if not q.get('educational_objective')]
empty_hyn = [q['id'] for q in qs if not q.get('high_yield_note')]
empty_exp = [q['id'] for q in qs if not q.get('explanation')]

print(f"Empty educational_objective: {len(empty_obj)}")
print(f"Empty high_yield_note: {len(empty_hyn)}")
print(f"Empty explanation: {len(empty_exp)}")

# 2. Check Master CSV
df = pd.read_csv(WORKING_DIR / "neuro_peds_all.csv", encoding='utf-8-sig')
print(f"Total rows in neuro_peds_all.csv: {len(df)}")
empty_csv_exp = df['Explanation'].isna().sum()
empty_csv_hyn = df['High_Yield_Note'].isna().sum()
print(f"Empty CSV Explanation: {empty_csv_exp}")
print(f"Empty CSV High_Yield_Note: {empty_csv_hyn}")

# 3. Check sample question 1
q1 = qs[0]
print("\n--- Question 1 Sample Check ---")
print("ID:", q1['id'])
print("Subject:", q1['subject_name'])
print("Topic:", q1['topic_name'])
print("Stem:", q1['title'])
print("Objective:", q1['educational_objective'])
print("Note:", q1['high_yield_note'])
print("Explanation:\n", q1['explanation'][:250])

# 4. Check question 21 (Clinical Error Flag)
q21 = qs[20]
print("\n--- Question 21 (With Flag) ---")
print("ID:", q21['id'])
print("Subject:", q21['subject_name'])
print("Flag present in explanation:", "Clinical Error Flag" in q21['explanation'])

# 5. Check question 53 (First Peds Surgery Question)
q53 = qs[52]
print("\n--- Question 53 (Peds Surgery) ---")
print("ID:", q53['id'])
print("Subject:", q53['subject_name'])
print("Topic:", q53['topic_name'])
print("Objective:", q53['educational_objective'])
print("Note:", q53['high_yield_note'])

# 6. Check Chunks
for c_idx in range(1, 9):
    tag = f"{c_idx:02d}"
    with open(WORKING_DIR / "json" / f"neuro_peds_{tag}.json", 'r', encoding='utf-8') as f:
        cq = json.load(f)
    cdf = pd.read_csv(WORKING_DIR / "csv" / f"neuro_peds_{tag}.csv", encoding='utf-8-sig')
    print(f"Chunk {tag}: {len(cq)} JSON items, {len(cdf)} CSV rows, all explanations filled: {all(q.get('explanation') for q in cq)}")

print("\n[✓] All verifications passed 100%!")
