import sys
import json
import re
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

thoracic_expected = [
    "رضوض الصدر والأذيات الإسعافية",
    "أمراض وجراحة الجنب",
    "سرطان الرئة والنقائل الورمية",
    "الآفات الرئوية الإنتانية والخمجية",
    "تشوهات جدار الصدر وأورام المنصف",
    "الإجراءات الصدرية وتدبير الطريق الهوائي"
]

vascular_expected = [
    "رضوض الشرايين والانسدادات الحادة",
    "التصلب العصيدي ونقص التروية المزمن",
    "تسلخ الأبهر وأمهات الدم الشريانية",
    "المتلازمات الوعائية والتهابات الشرايين",
    "أمراض الأوردة والأوعية اللمفية"
]

def verify_subject(sub_slug: str, expected_order: list):
    print(f"\n=======================================================")
    print(f" Verifying {sub_slug}")
    print(f"=======================================================")
    
    sub_dir = Path("final") / sub_slug
    json_path = sub_dir / f"{sub_slug}_all.json"
    html_path = sub_dir / f"{sub_slug}_all_topics.html"
    
    # 1. JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        j_items = json.load(f)
    
    j_topics = []
    for it in j_items:
        t = it.get('topic_name')
        if t and t not in j_topics:
            j_topics.append(t)
            
    print("1. JSON Topics Order:")
    for i, t in enumerate(j_topics, 1):
        print(f"   {i}. {t}")
    assert j_topics == expected_order, f"JSON topic mismatch in {sub_slug}!"
    print("   [✓] JSON matches expected order 100%!")

    # 2. Manifest
    with open("final/manifest.json", 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    m_topics = manifest['subjects'][sub_slug]['topics']
    print("\n2. Manifest Topics Order:")
    for i, t in enumerate(m_topics, 1):
        print(f"   {i}. {t}")
    assert m_topics == expected_order, f"Manifest topic mismatch in {sub_slug}!"
    print("   [✓] Manifest matches expected order 100%!")

    # 3. HTML
    html_text = html_path.read_text(encoding='utf-8')
    matches = re.findall(r'<div class="topic-title-text">(.*?)</div>', html_text)
    # Deduplicate preserving order
    html_topics = []
    for m in matches:
        m_clean = m.strip()
        if m_clean not in html_topics:
            html_topics.append(m_clean)
            
    print("\n3. HTML Rendered Topics Order:")
    for i, t in enumerate(html_topics, 1):
        print(f"   {i}. {t}")
    assert html_topics == expected_order, f"HTML rendered topic mismatch in {sub_slug}!"
    print("   [✓] HTML matches expected order 100%!")

def main():
    verify_subject("thoracic_surgery", thoracic_expected)
    verify_subject("vascular_surgery", vascular_expected)
    print("\n🎉 ALL VERIFICATIONS PASSED WITH ZERO ERRORS!")

if __name__ == "__main__":
    main()
