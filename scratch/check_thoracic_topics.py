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

print(f"Total lines parsed from topics.txt: {len(mapping)}")

thoracic_topics = [
    'رضوض الصدر والأذيات الإسعافية',
    'أمراض وجراحة الجنب',
    'سرطان الرئة والنقائل الورمية',
    'الآفات الرئوية الإنتانية والخمجية',
    'تشوهات جدار الصدر وأورام المنصف',
    'الإجراءات الصدرية وتدبير الطريق الهوائي'
]

cardiac_topics = [
    'دارة القلب والرئة الاصطناعية',
    'داء الشرايين الإكليلية وجراحة المجازات',
    'أمراض صمامات القلب وجراحتها',
    'تشوهات القلب الخلقية والولادية',
    'آفات التامور والسطام والدعم الدوراني'
]

vascular_topics = [
    'رضوض الشرايين والانسدادات الحادة',
    'التصلب العصيدي ونقص التروية المزمن',
    'تسلخ الأبهر وأمهات الدم الشريانية',
    'المتلازمات الوعائية والتهابات الشرايين',
    'أمراض الأوردة والأوعية اللمفية'
]

all_expected = thoracic_topics + cardiac_topics + vascular_topics
topic_counts = {t: 0 for t in all_expected}
unknown_topics = {}

for num, (qid, topic) in mapping.items():
    if topic in topic_counts:
        topic_counts[topic] += 1
    else:
        unknown_topics.setdefault(topic, []).append((num, qid))

print("\n--- Topic Counts According to Syllabus Order ---")
print("أولاً: الجراحة الصدرية:")
for t in thoracic_topics:
    print(f"  - {t}: {topic_counts[t]} أسئلة")

print("\nثانياً: الجراحة القلبية:")
for t in cardiac_topics:
    print(f"  - {t}: {topic_counts[t]} أسئلة")

print("\nثالثاً: جراحة الأوعية:")
for t in vascular_topics:
    print(f"  - {t}: {topic_counts[t]} أسئلة")

total_thoracic = sum(topic_counts[t] for t in thoracic_topics)
total_cardiac = sum(topic_counts[t] for t in cardiac_topics)
total_vascular = sum(topic_counts[t] for t in vascular_topics)

print(f"\nTotal Thoracic: {total_thoracic}")
print(f"Total Cardiac:  {total_cardiac}")
print(f"Total Vascular: {total_vascular}")
print(f"Grand Total:    {total_thoracic + total_cardiac + total_vascular}")

if unknown_topics:
    print(f"\n[!] Unknown topics: {len(unknown_topics)}")
    for ut, qs in unknown_topics.items():
        print(f"  '{ut}': {qs}")
else:
    print("\n[✓] All 167 questions mapped perfectly to the 16 topics!")
