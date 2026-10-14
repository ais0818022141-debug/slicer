import os
import sys
import re
import csv
import json
import shutil
import datetime
from pathlib import Path
from collections import OrderedDict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
FINAL_DIR = BASE_DIR / "final"
MANIFEST_PATH = FINAL_DIR / "manifest.json"
PDF_MAKER_DIR = BASE_DIR / "pdf_maker"
GENERATOR_SCRIPT = PDF_MAKER_DIR / "generator.py"

LETTERS_POOL = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']

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
    'تشرين': 10.5,
    'كانون': 12,
    'دكتوراه': 13,
    'فصل اول': 4,
    'فصل أول': 4,
    'فصل ثاني': 7,
    'فصل ثان': 7,
    'دورة اولى': 4,
    'دورة أولى': 4,
    'دورة ثانية': 7,
    'تكميلية': 9.5,
    'استثنائية': 9.6,
    'ربيع': 4,
    'صيف': 7,
    'خريف': 10,
    'شتاء': 1
}

SYLLABUS_TOPIC_ORDERS = {
    "plastic": [
        'الحروق',
        'الطعوم الجلدية',
        'اندمال الجروح وتدبيرها',
        'الشرائح والضياع المادي وتغطيته',
        'الجراحة التجميلية للقوام (شد البطن)',
        'سرطانات الجلد والآفات قبل السرطانية',
        'إنتانات الجلد',
        'جراحة الثدي الترميمية'
    ],
    "ped_surgery": [
        'التشوهات الخلقية في الجهاز الهضمي والحجاب الحاجز',
        'الانسدادات المعوية وآفات جدار البطن والمنطقة الشرجية',
        'أورام الأطفال الجراحية ورتق الطرق الصفراوية'
    ],
    "onco": [
        'جراحة أورام الغدة الدرقية وجارات الدرق'
    ]
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

def norm_stem(s):
    if not s or not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r'[\s:：]*رأس\s*[:：]*$', '', s)
    s = re.sub(r'[\s:：؟?.]+$', '', s)
    return s + ':'

def norm_option(s):
    if not s or not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r'[\s.:：]+$', '', s)
    return s + '.'

def dry_run_subject(subject_slug):
    csv_path = FINAL_DIR / subject_slug / f"{subject_slug}_all.csv"
    json_path = FINAL_DIR / subject_slug / f"{subject_slug}_all.json"
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        raw_rows = list(reader)
        
    id_col = 'Question_ID' if 'Question_ID' in fieldnames else fieldnames[0]
    
    with open(json_path, 'r', encoding='utf-8') as f:
        old_json_items = json.load(f)
    
    old_by_id = {it['id']: it for it in old_json_items if 'id' in it}
    old_by_stem = {norm_stem(it.get('title')): it for it in old_json_items if 'title' in it}
    
    # Map old items by original ID before renumbering
    row_to_old = {}
    for r in raw_rows:
        qid = r.get(id_col)
        old_it = old_by_id.get(qid)
        if not old_it:
            st = norm_stem(r.get('Question_Text'))
            old_it = old_by_stem.get(st)
        row_to_old[id(r)] = old_it
        
    # Group rows by topic
    topic_order = SYLLABUS_TOPIC_ORDERS.get(subject_slug, [])
    grouped = OrderedDict()
    for t in topic_order:
        grouped[t] = []
        
    for r in raw_rows:
        t = (r.get('Chapter_or_Section') or 'عام').strip()
        grouped.setdefault(t, []).append(r)
        
    sorted_rows = []
    print(f"\n==========================================")
    print(f" Subject: {subject_slug} ({len(raw_rows)} questions)")
    print(f"==========================================")
    for t_idx, (t, q_rows) in enumerate(grouped.items(), 1):
        if not q_rows:
            continue
        q_rows.sort(key=lambda r: parse_exam_date(r.get('Exam_Date')), reverse=True)
        sorted_rows.extend(q_rows)
        dates = [r.get('Exam_Date') for r in q_rows]
        print(f"  Topic {t_idx}: {t} ({len(q_rows)} qs)")
        print(f"    Date range: {dates[0]} -> {dates[-1]}")
        
    print(f"Total sorted rows: {len(sorted_rows)}")
    
    # Check educational objective coverage
    objs_found = 0
    for r in sorted_rows:
        old_it = row_to_old.get(id(r))
        if old_it and (old_it.get('educational_objective') or '').strip():
            objs_found += 1
    print(f"Educational objectives preserved: {objs_found} / {len(sorted_rows)}")

for s in ['plastic', 'onco', 'ped_surgery']:
    dry_run_subject(s)
