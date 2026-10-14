import sys
import csv
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open("final/plastic/plastic_all.csv", 'r', encoding='utf-8-sig') as f:
    r = csv.DictReader(f)
    counts = Counter(row['Chapter_or_Section'] for row in r)
    print("Topics in plastic:", counts)
