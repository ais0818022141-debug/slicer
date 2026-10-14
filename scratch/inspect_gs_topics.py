import sys
import csv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('final/general_surgery/general_surgery_all.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

topics_map = {}
for r in rows:
    t = r['Chapter_or_Section']
    topics_map.setdefault(t, []).append(r)

print("ACTUAL TOPICS IN CSV:")
for t, qs in topics_map.items():
    print(f"  * '{t}' ({len(qs)} qs)")

user_requested_order = [
    "أمراض المري الجراحية",
    "أمراض المعدة والعفج الجراحية",
    "أمراض الأمعاء الدقيقة الجراحية",
    "أمراض الكولون والمستقيم الجراحية",
    "أمراض القناة الشرجية",
    "أمراض الكبد الجراحية",
    "أمراض الطرق الصفراوية والمرارة",
    "آفات البنكرياس الجراحية",
    "النزف الهضمي وآفات الطحال",
    "أمراض البريتوان والبطن الحاد",
    "الصدمة ورضوض البطن",
    "الفتوق وجدار البطن",
    "أمراض الثدي الجراحية",
    "الجراحة التنظيرية وجراحة البدانة والعناية حول الجراحية"
]

print("\nMATCHING USER ORDER WITH ACTUAL:")
for idx, u_t in enumerate(user_requested_order, 1):
    matched = None
    for actual_t in topics_map.keys():
        if actual_t == u_t or actual_t.replace("والمعشري", "والعفج") == u_t or u_t.replace("والعفج", "والمعشري") == actual_t:
            matched = actual_t
            break
    print(f"{idx:02d}. Requested: '{u_t}' -> Actual: '{matched}' ({len(topics_map[matched]) if matched else 0} qs)")

unmatched = [t for t in topics_map.keys() if t not in [actual_t for actual_t in topics_map.keys() if any(actual_t == u_t or actual_t.replace("والمعشري", "والعفج") == u_t for u_t in user_requested_order)]]
print("\nUNMATCHED TOPICS IN CSV:", unmatched)
