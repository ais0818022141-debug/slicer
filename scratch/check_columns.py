import sys
import csv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("final/onco/onco_all.csv", 'r', encoding='utf-8-sig') as f:
    onco_headers = csv.reader(f).__next__()

with open("final/plastic/plastic_all.csv", 'r', encoding='utf-8-sig') as f:
    plastic_headers = csv.reader(f).__next__()

print("ONCO FINAL HEADERS:", onco_headers)
print("PLASTIC FINAL HEADERS:", plastic_headers)

# Let's inspect the working_on files
with open("working_on/أسئلة دورات أورام.csv", 'r', encoding='utf-8-sig') as f:
    onco_work_rows = list(csv.reader(f))

with open("working_on/أسئلة دورات تجميلية.csv", 'r', encoding='utf-8-sig') as f:
    plastic_work_rows = list(csv.reader(f))

print(f"\nOnco work: {len(onco_work_rows)} rows. Column count of row 0: {len(onco_work_rows[0])}")
for idx, col in enumerate(onco_work_rows[0]):
    print(f"  Col {idx}: {col[:30]}")

print(f"\nPlastic work: {len(plastic_work_rows)} rows. Column count of row 0: {len(plastic_work_rows[0])}")
for idx, col in enumerate(plastic_work_rows[0]):
    print(f"  Col {idx}: {col[:30]}")
