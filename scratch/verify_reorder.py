import sys
import json
import re
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Check JSON topic order
with open('final/general_surgery/general_surgery_all.json', 'r', encoding='utf-8') as f:
    jdata = json.load(f)

json_topics = []
for it in jdata:
    t = it.get('topic_name')
    if t and t not in json_topics:
        json_topics.append(t)

print("JSON TOPICS ORDER:")
for i, t in enumerate(json_topics, 1):
    print(f"  {i:02d}. {t}")

# 2. Check manifest topics order
with open('final/manifest.json', 'r', encoding='utf-8') as f:
    m = json.load(f)

manifest_topics = m['subjects']['general_surgery']['topics']
print("\nMANIFEST TOPICS ORDER:")
for i, t in enumerate(manifest_topics, 1):
    print(f"  {i:02d}. {t}")

# 3. Check HTML index order
html_path = Path('final/general_surgery/general_surgery_all_topics.html')
html_text = html_path.read_text(encoding='utf-8')
# Find topic card headings or sections
matches = re.findall(r'<h[234][^>]*class="[^"]*topic-[^"]*"[^>]*>(.*?)</h[234]>', html_text)
if not matches:
    # Look for topic names in cards
    matches = re.findall(r'<div class="topic-title">(.*?)</div>', html_text)
if not matches:
    # Look for section headers
    matches = re.findall(r'data-topic="([^"]+)"', html_text)

print(f"\nHTML TOPIC MENTIONS ({len(matches)}):")
for i, m in enumerate(matches[:15], 1):
    print(f"  {i:02d}. {m.strip()}")

assert json_topics[0] == "أمراض المري الجراحية"
assert json_topics[1] == "أمراض المعدة والعفج الجراحية"
assert json_topics[2] == "أمراض الأمعاء الدقيقة الجراحية"
assert json_topics[3] == "أمراض الكولون والمستقيم الجراحية"
assert json_topics[4] == "أمراض القناة الشرجية"
assert json_topics[5] == "أمراض الكبد الجراحية"
assert json_topics[6] == "أمراض الطرق الصفراوية والمرارة"
assert json_topics[7] == "آفات البنكرياس الجراحية"
assert json_topics[8] == "النزف الهضمي وآفات الطحال"
assert json_topics[9] == "أمراض البريتوان والبطن الحاد"
assert json_topics[10] == "الصدمة ورضوض البطن"
assert json_topics[11] == "الفتوق وجدار البطن"
assert json_topics[12] == "أمراض الثدي الجراحية"
assert json_topics[13] == "الجراحة التنظيرية وجراحة البدانة والعناية حول الجراحية"

print("\nALL ASSERTIONS PASSED! TOPICS ARE ORDERED EXACTLY AS REQUESTED!")
