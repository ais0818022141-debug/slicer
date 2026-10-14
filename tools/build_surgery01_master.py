import os
import sys
import re
import json
import subprocess
from pathlib import Path
import pandas as pd

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
FINAL_DIR = BASE_DIR / "final"
GS_JSON = FINAL_DIR / "general_surgery" / "general_surgery_all.json"
PO_JSON = FINAL_DIR / "plastic_onco" / "plastic_onco_all.json"
OUTPUT_DIR = FINAL_DIR / "surgery01"
MANIFEST_PATH = FINAL_DIR / "manifest.json"

TOOLS_DIR = BASE_DIR / "tools"
sys.path.append(str(TOOLS_DIR))
from topic_sorter import parse_exam_date

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

# 17 Topics in strict requested syllabus order
SYLLABUS_ORDER = [
    'أمراض المري الجراحية',
    'أمراض المعدة والعفج الجراحية',
    'أمراض الأمعاء الدقيقة الجراحية',
    'أمراض الكولون والمستقيم الجراحية',
    'أمراض القناة الشرجية',
    'أمراض الكبد الجراحية',
    'أمراض الطرق الصفراوية والمرارة',
    'آفات البنكرياس الجراحية',
    'النزف الهضمي وآفات الطحال',
    'أمراض البريتوان والبطن الحاد',
    'الصدمة ورضوض البطن',
    'الفتوق وجدار البطن',
    'أمراض الثدي الجراحية',
    'الجراحة التنظيرية وجراحة البدانة والعناية حول الجراحية',
    'سرطانات الجلد والآفات السطحية',
    'جراحة أورام الغدة الدرقية وجارات الدرق',
    'الحروق'
]

TOPIC_MAPPING = {
    # General Surgery renames & merges
    'أمراض المري الجراحية': 'أمراض المري الجراحية',
    'أمراض المعدة والمعشري الجراحية': 'أمراض المعدة والعفج الجراحية',
    'أمراض المعدة والعفج الجراحية': 'أمراض المعدة والعفج الجراحية',
    'أمراض الأمعاء الدقيقة الجراحية': 'أمراض الأمعاء الدقيقة الجراحية',
    'أمراض الكولون والمستقيم الجراحية': 'أمراض الكولون والمستقيم الجراحية',
    'أمراض القناة الشرجية': 'أمراض القناة الشرجية',
    'أمراض الكبد الجراحية': 'أمراض الكبد الجراحية',
    'أمراض الطرق الصفراوية والمرارة': 'أمراض الطرق الصفراوية والمرارة',
    'آفات البنكرياس الجراحية': 'آفات البنكرياس الجراحية',
    'النزف الهضمي وآفات الطحال': 'النزف الهضمي وآفات الطحال',
    'أمراض البريتوان والبطن الحاد': 'أمراض البريتوان والبطن الحاد',
    'الصدمة ورضوض البطن': 'الصدمة ورضوض البطن',
    'الفتوق وجدار البطن': 'الفتوق وجدار البطن',
    'أمراض الثدي الجراحية': 'أمراض الثدي الجراحية',
    'الجراحة التنظيرية وجراحة البدانة والعناية حول الجراحية': 'الجراحة التنظيرية وجراحة البدانة والعناية حول الجراحية',
    'أورام الجلد والنسج الرخوة': 'سرطانات الجلد والآفات السطحية',
    'جراحة الغدد الصماء (أمراض الدرق)': 'جراحة أورام الغدة الدرقية وجارات الدرق',
    'جراحة الغدد الصماء': 'جراحة أورام الغدة الدرقية وجارات الدرق',

    # Plastic Surgery & Oncology topics
    'سرطانات الجلد والآفات السطحية': 'سرطانات الجلد والآفات السطحية',
    'جراحة أورام الغدة الدرقية وجارات الدرق': 'جراحة أورام الغدة الدرقية وجارات الدرق',
    'الحروق': 'الحروق'
}

def main():
    print("=" * 70)
    print(" TealMED Surgery 1 (surgery01) Master Consolidated Package Builder")
    print(" Combining: General Surgery (277) + Plastic & Oncology Surgery (77)")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load data from source final JSON files
    with open(GS_JSON, 'r', encoding='utf-8') as f:
        gs_questions = json.load(f)
    print(f"[✓] Loaded {len(gs_questions)} questions from {GS_JSON.name}")

    with open(PO_JSON, 'r', encoding='utf-8') as f:
        po_questions = json.load(f)
    print(f"[✓] Loaded {len(po_questions)} questions from {PO_JSON.name}")

    total_input = len(gs_questions) + len(po_questions)
    print(f"Total input questions: {total_input}")

    # 2. Tag source, remap topic, and assign unified subject name
    combined_questions = []
    for q in gs_questions:
        q_copy = dict(q)
        q_copy['source_pkg'] = 'general_surgery'
        old_topic = q_copy.get('topic_name', '')
        q_copy['topic_name'] = TOPIC_MAPPING.get(old_topic, old_topic)
        q_copy['subject_name'] = 'الجراحة 1'
        combined_questions.append(q_copy)

    for q in po_questions:
        q_copy = dict(q)
        q_copy['source_pkg'] = 'plastic_onco'
        old_topic = q_copy.get('topic_name', '')
        q_copy['topic_name'] = TOPIC_MAPPING.get(old_topic, old_topic)
        q_copy['subject_name'] = 'الجراحة 1'
        combined_questions.append(q_copy)

    # 3. Group questions by syllabus topic
    grouped = {t: [] for t in SYLLABUS_ORDER}
    for q in combined_questions:
        t = q['topic_name']
        if t not in grouped:
            print(f"[!] Warning: Unknown topic '{t}' for question {q['id']}")
            grouped.setdefault(t, []).append(q)
            SYLLABUS_ORDER.append(t)
        else:
            grouped[t].append(q)

    # 4. Chronologically sort within each topic (newest exam first) and globally renumber
    sorted_questions = []
    global_idx = 1

    print("\n--- Consolidated Syllabus Breakdown & Ranges ---")
    for t_idx, topic in enumerate(SYLLABUS_ORDER, start=1):
        qs = grouped[topic]
        qs.sort(key=lambda x: parse_exam_date(x.get('exam_period')), reverse=True)
        start_q = global_idx
        for q in qs:
            num_str = f"{global_idx:03d}"
            q['id'] = f"q_surgery01_{num_str}"
            q['title'] = norm_stem(q.get('title', ''))
            for opt in q.get('options', []):
                opt['text'] = norm_option(opt.get('text', ''))
            sorted_questions.append(q)
            global_idx += 1
        end_q = global_idx - 1
        date_span = f"{qs[0].get('exam_period')} -> {qs[-1].get('exam_period')}" if qs else "N/A"
        print(f"  {t_idx:02d}. {topic:52} | {len(qs):2d} أسئلة (#{start_q:03d}-#{end_q:03d}) [{date_span}]")

    assert len(sorted_questions) == total_input, f"Mismatch: {len(sorted_questions)} != {total_input}"
    print(f"\n[✓] Total consolidated and verified questions: {len(sorted_questions)}")

    # 5. Export surgery01_all.json
    json_path = OUTPUT_DIR / "surgery01_all.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Created master JSON: {json_path.name} ({len(sorted_questions)} items)")

    # 6. Export surgery01_all.csv
    csv_rows = []
    for q in sorted_questions:
        options = q.get('options', [])
        cor_let = q.get('correct_option', '')

        correct_txt = ""
        wrong_texts = []
        for opt in options:
            if opt.get('is_correct') or (cor_let and opt.get('letter') == cor_let):
                correct_txt = opt.get('text', '')
            else:
                wrong_texts.append(opt.get('text', ''))

        row = {
            "Question_ID": q.get('id', ''),
            "Medical_Subject": q.get('subject_name', 'الجراحة 1'),
            "Exam_Date": q.get('exam_period', ''),
            "Chapter_or_Section": q.get('topic_name', ''),
            "Question_Text": q.get('title', ''),
            "Explanation": q.get('explanation') or '',
            "High_Yield_Note": q.get('high_yield_note') or '',
            "Correct_Answer": correct_txt
        }
        for i in range(1, 6):
            row[f"Wrong_Answer_{i}"] = wrong_texts[i - 1] if i - 1 < len(wrong_texts) else ""
        csv_rows.append(row)

    csv_path = OUTPUT_DIR / "surgery01_all.csv"
    df = pd.DataFrame(csv_rows)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"[✓] Created master CSV: {csv_path.name} ({len(df)} rows)")

    # 7. Export surgery01_all_ai.md (AI prompt file)
    ai_md_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:03d}"
        qid = q['id']
        topic = q['topic_name']
        title = q['title']
        cor_let = q.get('correct_option', '')

        ai_md_lines.append(f"#{num_str} [{qid}] ({topic})")
        ai_md_lines.append(f"السؤال: {title}")
        ai_md_lines.append(f"الجواب: {cor_let}")
        for opt in q.get('options', []):
            let = opt.get('letter', '')
            txt = opt.get('text', '')
            if opt.get('is_correct'):
                ai_md_lines.append(f"{let}) {txt} (الصحيح)")
            else:
                ai_md_lines.append(f"{let}) {txt}")
        ai_md_lines.append("---")
        ai_md_lines.append("")

    ai_md_path = OUTPUT_DIR / "surgery01_all_ai.md"
    with open(ai_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(ai_md_lines).strip() + "\n")
    print(f"[✓] Created master AI prompt: {ai_md_path.name}")

    # 8. Export surgery01_all_ai_temp.md (Full explanations review prompt)
    temp_md_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:03d}"
        qid = q['id']
        topic = q['topic_name']
        title = q['title']
        cor_let = q.get('correct_option', '')

        temp_md_lines.append(f"#{num_str} [{qid}] ({topic})")
        temp_md_lines.append(f"السؤال: {title}")
        temp_md_lines.append(f"الجواب: {cor_let}")
        for opt in q.get('options', []):
            let = opt.get('letter', '')
            txt = opt.get('text', '')
            if opt.get('is_correct'):
                temp_md_lines.append(f"{let}) {txt} (الصحيح)")
            else:
                temp_md_lines.append(f"{let}) {txt}")
        
        if q.get('educational_objective'):
            temp_md_lines.append(f"الهدف التعليمي: {q['educational_objective']}")
        if q.get('high_yield_note'):
            temp_md_lines.append(f"ملاحظة عالية الأهمية: {q['high_yield_note']}")
        if q.get('explanation'):
            temp_md_lines.append(f"الشرح:\n{q['explanation']}")
        temp_md_lines.append("---")
        temp_md_lines.append("")

    temp_md_path = OUTPUT_DIR / "surgery01_all_ai_temp.md"
    with open(temp_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(temp_md_lines).strip() + "\n")
    print(f"[✓] Created master AI temporary review file: {temp_md_path.name}")

    # 9. Export explanations.txt
    exp_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:03d}"
        exp_lines.append(f"#{num_str}")
        exp_lines.append(f"EDUCATIONAL OBJECTIVE:\n{q.get('educational_objective', '')}\n")
        exp_lines.append(f"HIGH YIELD NOTE:\n{q.get('high_yield_note', '')}\n")
        exp_lines.append(f"EXPLANATION:\n{q.get('explanation', '')}\n")
        exp_lines.append("---\n")

    exp_path = OUTPUT_DIR / "explanations.txt"
    with open(exp_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(exp_lines).strip() + "\n")
    print(f"[✓] Created unified explanations.txt: {exp_path.name}")

    # 10. Generate HTML files via pdf_maker/generator.py
    print("\nRunning pdf_maker/generator.py to compile HTML views...")
    gen_cmd = [sys.executable, str(BASE_DIR / "pdf_maker" / "generator.py"), str(json_path), "-o", str(OUTPUT_DIR)]
    res = subprocess.run(gen_cmd, capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0:
        print(f"[!] Generator error: {res.stderr}")
    else:
        print(f"[✓] Generator completed successfully:\n{res.stdout.strip()}")

    # 11. Update manifest.json
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        manifest.setdefault("subjects", {})
        manifest["subjects"]["surgery01"] = {
            "subject_name": "الجراحة 1",
            "folder": "final/surgery01",
            "questions_count": len(sorted_questions),
            "files": {
                "csv": "surgery01_all.csv",
                "json": "surgery01_all.json",
                "ai_prompt": "surgery01_all_ai.md"
            },
            "topics": SYLLABUS_ORDER
        }

        manifest["subjects_count"] = len(manifest["subjects"])
        manifest["total_questions"] = sum(s.get("questions_count", 0) for s in manifest["subjects"].values())

        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] Updated manifest.json: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")

    print("\n" + "=" * 70)
    print(" Surgery 1 (surgery01) Consolidated Package Completed Successfully!")
    print(f" Output Location: {OUTPUT_DIR.resolve()}")
    print("=" * 70)

if __name__ == "__main__":
    main()
