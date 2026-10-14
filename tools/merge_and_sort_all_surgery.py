import os
import sys
import re
import json
import shutil
import pandas as pd
from pathlib import Path

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
WORKING_DIR = BASE_DIR / "working_on"
TOOLS_DIR = BASE_DIR / "tools"

sys.path.append(str(TOOLS_DIR))
from topic_sorter import parse_exam_date

LETTERS_POOL = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']

syllabus_order = [
    'الجراحة التنظيرية وجراحة البدانة والعناية حول الجراحية',
    'الصدمة ورضوض البطن',
    'أورام الجلد والنسج الرخوة',
    'أمراض الثدي الجراحية',
    'جراحة الغدد الصماء (أمراض الدرق)',
    'جراحة الغدد الصماء',
    'الفتوق وجدار البطن',
    'أمراض البريتوان والالبطن الحاد', # will be normalized below
    'أمراض البريتوان والبطن الحاد',
    'أمراض المري الجراحية',
    'أمراض المعدة والمعشري الجراحية',
    'أمراض الأمعاء الدقيقة الجراحية',
    'أمراض الكولون والمستقيم الجراحية',
    'أمراض القناة الشرجية',
    'أمراض الكبد الجراحية',
    'أمراض الطرق الصفراوية والمرارة',
    'آفات البنكرياس الجراحية',
    'النزف الهضمي وآفات الطحال'
]
# Clean duplicates while preserving order
seen = set()
clean_syllabus_order = []
for s in syllabus_order:
    if s not in seen and s != 'أمراض البريتوان والالبطن الحاد':
        seen.add(s)
        clean_syllabus_order.append(s)

syllabus_order = clean_syllabus_order

def parse_supp_explanations(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    lines = text.splitlines()
    blocks = {}
    current_num = None
    current_lines = []

    for line in lines:
        m = re.match(r'^\s*#(\d+)\s*$', line)
        if m:
            if current_num is not None:
                blocks[current_num] = "\n".join(current_lines).strip()
            current_num = int(m.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    if current_num is not None:
        blocks[current_num] = "\n".join(current_lines).strip()

    parsed_data = {}
    for qnum, block_text in blocks.items():
        obj_m = re.search(r'EDUCATIONAL\s+OBJECTIVE\s*:\s*(.*?)(?=\nHIGH\s+YIELD\s+NOTE\s*:|\nEXPLANATION\s*:|\n---|\Z)', block_text, re.DOTALL | re.IGNORECASE)
        hyn_m = re.search(r'HIGH\s+YIELD\s+NOTE\s*:\s*(.*?)(?=\nEXPLANATION\s*:|\n---|\Z)', block_text, re.DOTALL | re.IGNORECASE)
        exp_m = re.search(r'EXPLANATION\s*:\s*(.*?)(?=\n---|\nCLINICAL\s+ERROR|\Z)', block_text, re.DOTALL | re.IGNORECASE)

        obj = obj_m.group(1).strip() if obj_m else ""
        hyn = hyn_m.group(1).strip() if hyn_m else ""
        exp = exp_m.group(1).strip() if exp_m else ""

        parsed_data[qnum] = {
            "educational_objective": obj,
            "high_yield_note": hyn,
            "explanation": exp
        }
    return parsed_data

def main():
    print("=== Consolidating All General Surgery Questions (264 + 13 = 277) ===")

    # 1. Load existing 264 questions
    master_json_path = WORKING_DIR / "general_surgery_all.json"
    with open(master_json_path, 'r', encoding='utf-8') as f:
        existing_q = json.load(f)
    print(f"[✓] Loaded {len(existing_q)} existing questions from general_surgery_all.json")

    # 2. Load and attach explanations to 13 supplementary questions
    supp_json_path = WORKING_DIR / "general_surgery_supp.json"
    with open(supp_json_path, 'r', encoding='utf-8') as f:
        supp_q = json.load(f)
    print(f"[✓] Loaded {len(supp_q)} supplementary questions from general_surgery_supp.json")

    supp_exp_path = WORKING_DIR / "Explanations_supp.txt"
    supp_exp_map = parse_supp_explanations(supp_exp_path)
    print(f"[✓] Parsed {len(supp_exp_map)} explanation blocks from Explanations_supp.txt")

    for idx, q in enumerate(supp_q, start=1):
        if idx in supp_exp_map:
            entry = supp_exp_map[idx]
            q['educational_objective'] = entry['educational_objective']
            q['high_yield_note'] = entry['high_yield_note']
            q['explanation'] = entry['explanation']
        # Ensure topic name is standardized
        raw_topic = re.sub(r'^\d+\.\s*', '', q.get('topic_name', '')).strip()
        q['topic_name'] = raw_topic

    # Also update general_surgery_supp.json and general_surgery_supp.csv with explanations
    with open(supp_json_path, 'w', encoding='utf-8') as f:
        json.dump(supp_q, f, ensure_ascii=False, indent=2)

    # 3. Combine all 277 questions
    combined_questions = existing_q + supp_q
    print(f"[✓] Combined total questions: {len(combined_questions)}")

    # 4. Group by standard syllabus topic order
    grouped = {t: [] for t in syllabus_order}
    for q in combined_questions:
        t = q.get('topic_name', 'عام').strip()
        if t not in grouped:
            print(f"[!] Warning: Unknown topic '{t}' for question {q['id']}")
            grouped.setdefault(t, []).append(q)
            syllabus_order.append(t)
        else:
            grouped[t].append(q)

    # 5. Sort chronologically within each topic (newest exam session first) and renumber 1 to 277
    sorted_questions = []
    global_idx = 1

    print("\n--- Consolidated Topics Breakdown & Question Ranges ---")
    for t_idx, topic in enumerate(syllabus_order, start=1):
        qs = grouped[topic]
        qs.sort(key=lambda x: parse_exam_date(x.get('exam_period')), reverse=True)
        start_q = global_idx
        for q in qs:
            num_str = f"{global_idx:03d}"
            q['id'] = f"q_general_surgery_{num_str}"
            sorted_questions.append(q)
            global_idx += 1
        end_q = global_idx - 1
        date_span = f"{qs[0].get('exam_period')} -> {qs[-1].get('exam_period')}" if qs else "N/A"
        print(f"  {t_idx:02d}. {topic:50} | {len(qs):2d} أسئلة (#{start_q:03d}-#{end_q:03d}) [{date_span}]")

    print(f"\n[✓] Total sorted and renumbered questions: {len(sorted_questions)}")

    # 6. Backup existing master files
    backup_dir = WORKING_DIR / ".backup"
    backup_dir.mkdir(exist_ok=True)
    shutil.copyfile(master_json_path, backup_dir / "general_surgery_all_264_backup.json")
    if (WORKING_DIR / "general_surgery_all.csv").exists():
        shutil.copyfile(WORKING_DIR / "general_surgery_all.csv", backup_dir / "general_surgery_all_264_backup.csv")

    # 7. Write Master JSON: general_surgery_all.json
    with open(master_json_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Saved updated Master JSON: {master_json_path.name} ({len(sorted_questions)} questions)")

    # 8. Write Master CSV: general_surgery_all.csv & general_surgery.csv
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
            "Medical_Subject": q.get('subject_name', 'الجراحة العامة'),
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

    master_csv_path = WORKING_DIR / "general_surgery_all.csv"
    df = pd.DataFrame(csv_rows)
    df.to_csv(master_csv_path, index=False, encoding='utf-8-sig')
    df.to_csv(WORKING_DIR / "general_surgery.csv", index=False, encoding='utf-8-sig')
    print(f"[✓] Saved updated Master CSV: {master_csv_path.name} and general_surgery.csv")

    # 9. Write Clean AI Prompt Markdown: general_surgery_all_ai.md
    ai_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:03d}"
        qid = q['id']
        topic = q['topic_name']
        title = q['title']
        cor_let = q.get('correct_option', '')

        ai_lines.append(f"#{num_str} [{qid}] ({topic})")
        ai_lines.append(f"السؤال: {title}")
        ai_lines.append(f"الجواب: {cor_let}")
        for opt in q.get('options', []):
            let = opt.get('letter', '')
            txt = opt.get('text', '')
            if opt.get('is_correct'):
                ai_lines.append(f"{let}) {txt} (الصحيح)")
            else:
                ai_lines.append(f"{let}) {txt}")
        ai_lines.append("---")
        ai_lines.append("")

    master_ai_md_path = WORKING_DIR / "general_surgery_all_ai.md"
    with open(master_ai_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(ai_lines).strip() + "\n")
    print(f"[✓] Saved updated AI Prompt: {master_ai_md_path.name}")

    # 10. Write Full Explanations Markdown: general_surgery_all_ai_temp.md
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

    temp_md_path = WORKING_DIR / "general_surgery_all_ai_temp.md"
    with open(temp_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(temp_md_lines).strip() + "\n")
    print(f"[✓] Saved updated Full Explanations Markdown: {temp_md_path.name}")

    # 11. Sliced Chunks in csv/, json/, md/ (12 questions per chunk)
    csv_dir = WORKING_DIR / "csv"
    json_dir = WORKING_DIR / "json"
    md_dir = WORKING_DIR / "md"

    # Clean old chunk files first
    for f in list(csv_dir.glob("general_surgery_*.csv")) + list(json_dir.glob("general_surgery_*.json")) + list(md_dir.glob("general_surgery_*.md")):
        f.unlink()

    rows_per_chunk = 12
    total_chunks = (len(sorted_questions) + rows_per_chunk - 1) // rows_per_chunk

    for c_idx in range(total_chunks):
        chunk_num = c_idx + 1
        start_i = c_idx * rows_per_chunk
        end_i = min(start_i + rows_per_chunk, len(sorted_questions))

        chunk_q = sorted_questions[start_i:end_i]
        chunk_rows = csv_rows[start_i:end_i]

        tag = f"{chunk_num:02d}"
        c_csv = csv_dir / f"general_surgery_{tag}.csv"
        c_json = json_dir / f"general_surgery_{tag}.json"
        c_md = md_dir / f"general_surgery_{tag}_ai.md"

        # CSV
        pd.DataFrame(chunk_rows).to_csv(c_csv, index=False, encoding='utf-8-sig')

        # JSON
        with open(c_json, 'w', encoding='utf-8') as f:
            json.dump(chunk_q, f, ensure_ascii=False, indent=2)

        # MD
        chunk_md_lines = []
        for q in chunk_q:
            qid = q['id']
            m = re.search(r'_(\d+)$', qid)
            num_str = m.group(1) if m else "00"
            topic = q['topic_name']
            title = q['title']
            cor_let = q.get('correct_option', '')

            chunk_md_lines.append(f"#{num_str} [{qid}] ({topic})")
            chunk_md_lines.append(f"السؤال: {title}")
            chunk_md_lines.append(f"الجواب: {cor_let}")
            for opt in q.get('options', []):
                let = opt.get('letter', '')
                txt = opt.get('text', '')
                if opt.get('is_correct'):
                    chunk_md_lines.append(f"{let}) {txt} (الصحيح)")
                else:
                    chunk_md_lines.append(f"{let}) {txt}")
            chunk_md_lines.append("---")
            chunk_md_lines.append("")

        with open(c_md, 'w', encoding='utf-8') as f:
            f.write("\n".join(chunk_md_lines).strip() + "\n")

    print(f"[✓] Regenerated {total_chunks} chunk files (12 Qs each) in csv/, json/, md/")
    print("=== Consolidation Completed Successfully ===")

if __name__ == "__main__":
    main()
