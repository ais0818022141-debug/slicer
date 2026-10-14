import sys
from pathlib import Path
import pandas as pd

sys.path.append("tools")
from topic_sorter import parse_exam_date

dates = [
    'أيار 2026', 'آب 2025', 'كانون 2025', 'تشرين 2024', 'أيار 2024',
    'تشرين 2023', 'آذار 2023', 'أيلول 2022', 'آذار 2022', 'تشرين 2021',
    'حزيران 2021', 'تشرين 2020', 'حزيران 2020', 'تشرين 2019', 'شباط 2019',
    'تشرين 2018'
]

parsed = [(d, parse_exam_date(d)) for d in dates]
parsed.sort(key=lambda x: x[1], reverse=True)

print("Parsed and sorted dates (newest first):")
for d, p in parsed:
    print(f"  {d:15} -> {p}")
