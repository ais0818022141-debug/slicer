import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

topics_file = Path("working_on") / "topics.txt"

mapping = {}
with open(topics_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^#?(\d+)\s*\[(q_[a-zA-Z0-9_-]+)\]\s*(?:\((.*?)\)|(.+))$', line)
        if m:
            num = int(m.group(1))
            qid = m.group(2).lower()
            topic = (m.group(3) or m.group(4) or '').strip()
            mapping[num] = (qid, topic)

print(f"Total lines parsed: {len(mapping)}")

requested_topics = [
    # أولاً: الجراحة العصبية
    'رضوض الدماغ والجمجمة والنزوف داخل القحف',
    'أذيات النخاع الشوكي وأمراض العمود الفقري',
    'إصابات الأعصاب المحيطية والضفائر العصبية',
    'التشوهات العصبية الخلقية واستسقاء الدماغ',
    'أورام الجهاز العصبي المركزي',
    'الحوادث الوعائية الدماغية والتقييم العصبي',
    # ثانياً: جراحة الأطفال
    'التشوهات الخلقية في الجهاز الهضمي والحجاب الحاجز',
    'الانسدادات المعوية وآفات جدار البطن والمنطقة الشرجية',
    'أورام الأطفال الجراحية ورتق الطرق الصفراوية'
]

topic_counts = {t: 0 for t in requested_topics}
unknown_topics = {}

for num, (qid, topic) in mapping.items():
    if topic in topic_counts:
        topic_counts[topic] += 1
    else:
        unknown_topics.setdefault(topic, []).append((num, qid))

print("\n--- Topic Counts According to Syllabus Order ---")
print("أولاً: الجراحة العصبية:")
for t in requested_topics[:6]:
    print(f"  - {t}: {topic_counts[t]} أسئلة")

print("\nثانياً: جراحة الأطفال:")
for t in requested_topics[6:]:
    print(f"  - {t}: {topic_counts[t]} أسئلة")

total_neuro = sum(topic_counts[t] for t in requested_topics[:6])
total_peds = sum(topic_counts[t] for t in requested_topics[6:])
print(f"\nTotal Neurosurgery: {total_neuro}")
print(f"Total Pediatric Surgery: {total_peds}")
print(f"Grand Total: {total_neuro + total_peds}")

if unknown_topics:
    print(f"\n[!] Unknown or mismatched topics found: {len(unknown_topics)}")
    for ut, qs in unknown_topics.items():
        print(f"  '{ut}': {qs}")
else:
    print("\n[✓] All 96 questions mapped perfectly to the 9 topics!")
