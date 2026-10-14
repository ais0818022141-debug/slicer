import json
import html
import re
from pathlib import Path
from collections import defaultdict

# Let's verify index generation
with open('exams_builder/output/json/دورة_أيار_2026.json', 'r', encoding='utf-8') as f:
    session_data = json.load(f)

questions = session_data['questions']
session_name = session_data['session_name']
total_q = len(questions)

b1_qs = [q for q in questions if q.get("block_id") == 1]
b2_qs = [q for q in questions if q.get("block_id") == 2]

# Build subject stats
b1_subjs = defaultdict(lambda: {"count": 0, "cat": "", "code": ""})
for q in b1_qs:
    s = q.get("subject_name")
    b1_subjs[s]["count"] += 1
    b1_subjs[s]["cat"] = q.get("category_name", "")
    b1_subjs[s]["code"] = q.get("subject_code", s)

b2_subjs = defaultdict(lambda: {"count": 0, "cat": "", "code": ""})
for q in b2_qs:
    s = q.get("subject_name")
    b2_subjs[s]["count"] += 1
    b2_subjs[s]["cat"] = q.get("category_name", "")
    b2_subjs[s]["code"] = q.get("subject_code", s)

print("Block 1 Index items:", len(b1_subjs))
print("Block 2 Index items:", len(b2_subjs))
