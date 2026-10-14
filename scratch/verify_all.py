import os
import sys
import re
import csv
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

MONTH_MAP = {
    'كانون الثاني': 1, 'شباط': 2, 'اذار': 3, 'آذار': 3, 'نيسان': 4,
    'ايار': 5, 'أيار': 5, 'حزيران': 6, 'تموز': 7, 'اب': 8, 'آب': 8,
    'ايلول': 9, 'أيلول': 9, 'تشرين الاول': 10, 'تشرين الأول': 10,
    'تشرين الثاني': 11, 'كانون الاول': 12, 'كانون الأول': 12,
    'تشرين': 10.5, 'كانون': 12, 'دكتوراه': 13
}

def parse_exam_date(text):
    if not text:
        return (0, 0.0)
    raw = str(text)
    norm = raw.replace('ـ', '')
    y_match = re.search(r'((?:19|20)\d\d)', norm)
    year = int(y_match.group(1)) if y_match else 0
    m_val = 0.0
    for name, weight in sorted(MONTH_MAP.items(), key=lambda x: -len(x[0])):
        if name in norm:
            m_val = float(weight)
            break
    return (year, m_val)

TARGETS = {
    "plastic": 51,
    "onco": 26,
    "ped_surgery": 44
}

all_ok = True

for sub, expected_count in TARGETS.items():
    print(f"\n=======================================================")
    print(f" VERIFYING: {sub} (Expected: {expected_count} questions)")
    print(f"=======================================================")
    
    sub_dir = Path(f"final/{sub}")
    csv_p = sub_dir / f"{sub}_all.csv"
    json_p = sub_dir / f"{sub}_all.json"
    ai_p = sub_dir / f"{sub}_all_ai.md"
    ai_temp_p = sub_dir / f"{sub}_all_ai_temp.md"
    exp_txt_p = sub_dir / "explanations.txt"
    exp_md_p = sub_dir / "explanations.md"
    html_p = sub_dir / f"{sub}_all.html"
    topics_html_p = sub_dir / f"{sub}_all_topics.html"
    sessions_html_p = sub_dir / f"{sub}_all_sessions.html"
    topics_dir = sub_dir / "topics"
    sessions_dir = sub_dir / "sessions"
    years_dir = sub_dir / "years"
    topics_md_dir = sub_dir / "topics_md"
    explained_md_p = topics_md_dir / f"{sub}_all_explained.md"
    
    # 1. CSV check
    with open(csv_p, 'r', encoding='utf-8-sig') as f:
        csv_rows = list(csv.DictReader(f))
    csv_count = len(csv_rows)
    print(f"  CSV rows: {csv_count} (match: {csv_count == expected_count})")
    if csv_count != expected_count: all_ok = False
    
    # Check CSV IDs
    csv_ids = [r['Question_ID'] for r in csv_rows]
    expected_ids = [f"q_{sub}_{i:02d}" for i in range(1, expected_count + 1)]
    id_match = (csv_ids == expected_ids)
    print(f"  CSV IDs sequential q_{sub}_01..{expected_count:02d}: {id_match}")
    if not id_match: all_ok = False
    
    # Check topic contiguity and date ordering in CSV
    current_topic = None
    seen_topics = set()
    contig = True
    inversions = 0
    from itertools import groupby
    for t, grp in groupby(csv_rows, key=lambda r: r['Chapter_or_Section']):
        if t in seen_topics:
            contig = False
        seen_topics.add(t)
        g_rows = list(grp)
        dates = [parse_exam_date(r['Exam_Date']) for r in g_rows]
        for i in range(len(dates) - 1):
            if dates[i] < dates[i+1]:
                inversions += 1
                print(f"    [!] Inversion in topic '{t}': {g_rows[i]['Exam_Date']} vs {g_rows[i+1]['Exam_Date']}")
                all_ok = False
    print(f"  CSV distinct topics: {len(seen_topics)}, Contiguous: {contig}, Date inversions: {inversions}")
    if not contig or inversions > 0: all_ok = False

    # 2. JSON check
    with open(json_p, 'r', encoding='utf-8') as f:
        json_items = json.load(f)
    json_count = len(json_items)
    json_ids = [it['id'] for it in json_items]
    json_id_match = (json_ids == expected_ids)
    print(f"  JSON items: {json_count} (match: {json_count == expected_count}), IDs sequential: {json_id_match}")
    if json_count != expected_count or not json_id_match: all_ok = False

    # 3. AI Markdown check
    with open(ai_p, 'r', encoding='utf-8') as f:
        ai_content = f.read()
    ai_q_headers = re.findall(r'^#(\d+)\s+\[q_', ai_content, re.M)
    ai_count = len(ai_q_headers)
    print(f"  AI markdown items: {ai_count} (first: #{ai_q_headers[0]}, last: #{ai_q_headers[-1]})")
    if ai_count != expected_count: all_ok = False

    # 4. Explanations files check
    with open(exp_txt_p, 'r', encoding='utf-8') as f:
        exp_txt = f.read()
    exp_headers = re.findall(r'^#(\d+)$', exp_txt, re.M)
    print(f"  Explanations.txt items: {len(exp_headers)} (first: #{exp_headers[0]}, last: #{exp_headers[-1]})")
    if len(exp_headers) != expected_count: all_ok = False
    
    with open(exp_md_p, 'r', encoding='utf-8') as f:
        exp_md = f.read()
    exp_md_headers = re.findall(r'^#(\d+)$', exp_md, re.M)
    print(f"  Explanations.md items: {len(exp_md_headers)} (first: #{exp_md_headers[0]}, last: #{exp_md_headers[-1]})")
    if len(exp_md_headers) != expected_count: all_ok = False

    # 5. HTML checks
    print(f"  Master HTML: {html_p.name} (exists: {html_p.exists()})")
    print(f"  Topics HTML: {topics_html_p.name} (exists: {topics_html_p.exists()})")
    print(f"  Sessions HTML: {sessions_html_p.name} (exists: {sessions_html_p.exists()})")
    topic_htmls = list(topics_dir.glob("*.html"))
    session_htmls = list(sessions_dir.glob("*.html"))
    year_htmls = list(years_dir.glob("*.html"))
    print(f"  Standalone topic HTMLs: {len(topic_htmls)} files")
    print(f"  Standalone session HTMLs: {len(session_htmls)} files")
    print(f"  Standalone year HTMLs: {len(year_htmls)} files")

    # 6. Topics MD checks
    print(f"  Master explained MD: {explained_md_p.name} (exists: {explained_md_p.exists()})")
    topic_mds = [f for f in topics_md_dir.glob("*.md") if f.name != explained_md_p.name]
    print(f"  Per-topic MDs: {len(topic_mds)} files in {topics_md_dir.name}/")

# Manifest check
with open("final/manifest.json", 'r', encoding='utf-8') as f:
    mf = json.load(f)
print("\n=======================================================")
print(" MANIFEST.JSON CHECK")
print("=======================================================")
for sub, expected_count in TARGETS.items():
    sub_mf = mf['subjects'][sub]
    cnt = sub_mf['questions_count']
    tops = sub_mf['topics']
    print(f"  {sub:15s}: count={cnt} (match: {cnt == expected_count}), topics count={len(tops)}")
    print(f"    Topics: {tops}")
print(f"  Total manifest questions: {mf['total_questions']}")
print(f"\nALL CHECKS PASSED: {all_ok}")
