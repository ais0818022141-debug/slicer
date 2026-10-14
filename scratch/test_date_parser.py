import csv
import sys
import re
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

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

all_dates = set()
for s in ['plastic', 'onco', 'ped_surgery']:
    with open(f'final/{s}/{s}_all.csv', 'r', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            d = r.get('Exam_Date')
            if d:
                all_dates.add(d)

print("Parsed dates from newest to oldest:")
for d in sorted(all_dates, key=parse_exam_date, reverse=True):
    print(f"  {d:25s} -> {parse_exam_date(d)}")
