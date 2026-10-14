import csv
import sys
import re
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Syrian and Arab Medical Board exam month normalization map
MONTH_MAP = {
    'كانون الثاني': 1,
    'شباط': 2,
    'اذار': 3,
    'آذار': 3,
    'نيسان': 4,
    'ايار': 5,
    'أيار': 5,
    'حزيران': 6,
    'تموز': 7,
    'اب': 8,
    'آب': 8,
    'ايلول': 9,
    'أيلول': 9,
    'تشرين الاول': 10,
    'تشرين الأول': 10,
    'تشرين الثاني': 11,
    'كانون الاول': 12,
    'كانون الأول': 12,
    # Short / common variations
    'تشرين': 10,
    'كانون': 12,
    'ربيع': 4,
    'صيف': 7,
    'خريف': 10,
    'شتاء': 1
}

def parse_exam_date(text):
    if not text:
        return (0, 0)
    raw = str(text)
    norm = raw.replace('ـ', '')
    norm = re.sub(r'[أإآ]', 'ا', norm)
    y_match = re.search(r'(20\d\d|19\d\d)', norm)
    year = int(y_match.group(1)) if y_match else 0
    month = 0
    for name, m_val in sorted(MONTH_MAP.items(), key=lambda x: -len(x[0])):
        norm_name = re.sub(r'[أإآ]', 'ا', name)
        if norm_name in norm:
            month = m_val
            break
    return (year, month)

for sub in ['plastic', 'onco', 'ped_surgery']:
    csv_p = Path(f'final/{sub}/{sub}_all.csv')
    with open(csv_p, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    
    print(f"\n==============================================")
    print(f"Checking Order in {sub} ({len(rows)} rows)")
    print(f"==============================================")
    
    # Check if topics are contiguous
    current_topic = None
    topic_changes = 0
    seen_topics = set()
    topic_contiguous = True
    
    for r in rows:
        t = r.get('Chapter_or_Section')
        if t != current_topic:
            if t in seen_topics:
                print(f"[!] Non-contiguous topic found: '{t}' appeared again!")
                topic_contiguous = False
            seen_topics.add(t)
            current_topic = t
            topic_changes += 1
            
    print(f"Distinct topics: {len(seen_topics)}, topic transitions: {topic_changes}, Contiguous: {topic_contiguous}")
    
    # Check date ordering within each topic
    from itertools import groupby
    inversion_count = 0
    for t, group in groupby(rows, key=lambda r: r.get('Chapter_or_Section')):
        group_rows = list(group)
        dates = [r.get('Exam_Date') for r in group_rows]
        scores = [parse_exam_date(d) for d in dates]
        print(f"\nTopic: {t} ({len(group_rows)} questions):")
        for i in range(len(scores) - 1):
            if scores[i] < scores[i+1]:
                print(f"  [!] Date inversion at row {i+1}->{i+2}: '{dates[i]}' ({scores[i]}) is older than '{dates[i+1]}' ({scores[i+1]})")
                inversion_count += 1
            else:
                pass
        # Print all dates
        print(f"  Dates: {dates}")
    print(f"\nTotal date inversions in {sub}: {inversion_count}")
