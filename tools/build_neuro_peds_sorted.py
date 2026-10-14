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

def main():
    print("=== Processing Neurosurgery & Pediatric Surgery Topics & Chronological Sorting ===")

    # 1. Load topics.txt mapping
    topics_file = WORKING_DIR / "topics.txt"
    topics_map = {}
    with open(topics_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^#?(\d+)\s*\[(q_[a-zA-Z0-9_-]+)\]\s*(?:\((.*?)\)|(.+))$', line)
            if m:
                qid = m.group(2).lower()
                topic = (m.group(3) or m.group(4) or '').strip()
                topics_map[qid] = topic

    print(f"[✓] Loaded {len(topics_map)} topic entries from topics.txt")

    # 2. Load all 96 questions from working_on/json/
    json_dir = WORKING_DIR / "json"
    chunk_files = sorted(
        json_dir.glob("neuro_peds_*.json"),
        key=lambda p: int(re.search(r'_(\d+)\.json', p.name).group(1))
    )
    all_questions = []
    for cf in chunk_files:
        with open(cf, 'r', encoding='utf-8') as f:
            all_questions.extend(json.load(f))

    print(f"[✓] Loaded {len(all_questions)} questions from {len(chunk_files)} JSON chunks")

    # 3. Assign topics and preserve original ID
    for idx, q in enumerate(all_questions, start=1):
        raw_qid = q.get('id', f'q_neuro_peds_{idx:02d}').lower()
        q['original_id'] = q.get('id')
        q['topic_name'] = topics_map.get(raw_qid, 'غير محدد')

    # 4. Strict syllabus topic order requested by user:
    # أولاً: الجراحة العصبية (6 مواضيع)
    neuro_topics = [
        'رضوض الدماغ والجمجمة والنزوف داخل القحف',
        'أذيات النخاع الشوكي وأمراض العمود الفقري',
        'إصابات الأعصاب المحيطية والضفائر العصبية',
        'التشوهات العصبية الخلقية واستسقاء الدماغ',
        'أورام الجهاز العصبي المركزي',
        'الحوادث الوعائية الدماغية والتقييم العصبي'
    ]

    # ثانياً: جراحة الأطفال (3 مواضيع)
    peds_topics = [
        'التشوهات الخلقية في الجهاز الهضمي والحجاب الحاجز',
        'الانسدادات المعوية وآفات جدار البطن والمنطقة الشرجية',
        'أورام الأطفال الجراحية ورتق الطرق الصفراوية'
    ]

    syllabus_order = neuro_topics + peds_topics

    grouped = {t: [] for t in syllabus_order}
    for q in all_questions:
        t = q['topic_name']
        if t not in grouped:
            print(f"[!] Warning: Unknown topic '{t}' for question {q['id']}")
            grouped.setdefault(t, []).append(q)
            syllabus_order.append(t)
        else:
            grouped[t].append(q)

    # 5. Chronologically sort within each topic (newest first) and renumber globally
    sorted_questions = []
    global_idx = 1

    print("\n--- Topics Breakdown & Question Ranges ---")
    print("\n>>> أولاً: الجراحة العصبية")
    for t_idx, topic in enumerate(syllabus_order, start=1):
        if t_idx == 7:
            print("\n>>> ثانياً: جراحة الأطفال")
            
        qs = grouped[topic]
        # Sort chronologically by exam_period (newest session first)
        qs.sort(key=lambda x: parse_exam_date(x.get('exam_period')), reverse=True)
        
        # Determine proper subject name
        subj_name = "الجراحة العصبية" if topic in neuro_topics else "جراحة الأطفال"
        
        start_q = global_idx
        for q in qs:
            num_str = f"{global_idx:02d}"
            q['id'] = f"q_neuro_peds_{num_str}"
            q['subject_name'] = subj_name
            q['title'] = norm_stem(q.get('title', ''))
            for opt in q.get('options', []):
                opt['text'] = norm_option(opt.get('text', ''))
            sorted_questions.append(q)
            global_idx += 1
        end_q = global_idx - 1
        date_span = f"{qs[0].get('exam_period')} -> {qs[-1].get('exam_period')}" if qs else "N/A"
        print(f"  {t_idx:02d}. {topic:52} | {len(qs):2d} أسئلة (#{start_q:02d}-#{end_q:02d}) [{date_span}]")

    print(f"\n[✓] Total sorted and renumbered questions: {len(sorted_questions)}")

    # 6. Backup original neuro_peds.csv
    backup_dir = WORKING_DIR / ".backup"
    backup_dir.mkdir(exist_ok=True)
    if (WORKING_DIR / "neuro_peds.csv").exists():
        shutil.copyfile(WORKING_DIR / "neuro_peds.csv", backup_dir / "neuro_peds_original_unsorted.csv")

    # 7. Generate Master AI Markdown Prompt: working_on/neuro_peds_all_ai.md
    md_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        topic = q['topic_name']
        title = q['title']
        cor_let = q.get('correct_option', '')

        md_lines.append(f"#{num_str} [{qid}] ({topic})")
        md_lines.append(f"السؤال: {title}")
        md_lines.append(f"الجواب: {cor_let}")
        for opt in q.get('options', []):
            let = opt.get('letter', '')
            txt = opt.get('text', '')
            if opt.get('is_correct'):
                md_lines.append(f"{let}) {txt} (الصحيح)")
            else:
                md_lines.append(f"{let}) {txt}")
        md_lines.append("---")
        md_lines.append("")

    master_md_path = WORKING_DIR / "neuro_peds_all_ai.md"
    with open(master_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines).strip() + "\n")
    print(f"[✓] Created master AI prompt: {master_md_path.name} ({len(sorted_questions)} questions)")

    # 8. Generate Master CSV: working_on/neuro_peds_all.csv and neuro_peds.csv
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
            "Medical_Subject": q.get('subject_name', ''),
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

    master_csv_path = WORKING_DIR / "neuro_peds_all.csv"
    df = pd.DataFrame(csv_rows)
    df.to_csv(master_csv_path, index=False, encoding='utf-8-sig')
    df.to_csv(WORKING_DIR / "neuro_peds.csv", index=False, encoding='utf-8-sig')
    print(f"[✓] Created master CSV: {master_csv_path.name} and neuro_peds.csv")

    # 9. Generate Master JSON: working_on/neuro_peds_all.json
    master_json_path = WORKING_DIR / "neuro_peds_all.json"
    with open(master_json_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Created master JSON: {master_json_path.name}")

    # 10. Update the Sliced Chunks in working_on/ (csv/, json/, md/)
    csv_dir = WORKING_DIR / "csv"
    json_dir = WORKING_DIR / "json"
    md_dir = WORKING_DIR / "md"

    rows_per_chunk = 12
    total_chunks = (len(sorted_questions) + rows_per_chunk - 1) // rows_per_chunk

    for c_idx in range(total_chunks):
        chunk_num = c_idx + 1
        start_i = c_idx * rows_per_chunk
        end_i = min(start_i + rows_per_chunk, len(sorted_questions))
        chunk_q = sorted_questions[start_i:end_i]
        chunk_rows = csv_rows[start_i:end_i]

        tag = f"{chunk_num:02d}"
        c_csv = csv_dir / f"neuro_peds_{tag}.csv"
        c_json = json_dir / f"neuro_peds_{tag}.json"
        c_md = md_dir / f"neuro_peds_{tag}_ai.md"

        # CSV
        pd.DataFrame(chunk_rows).to_csv(c_csv, index=False, encoding='utf-8-sig')

        # JSON
        with open(c_json, 'w', encoding='utf-8') as f:
            json.dump(chunk_q, f, ensure_ascii=False, indent=2)

        # AI MD
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

    print(f"[✓] Updated {total_chunks} chunk files in csv/, json/, md/")

    # 11. Update working_on/topics.txt to reflect new sorted numbering
    updated_topics_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:02d}"
        updated_topics_lines.append(f"#{num_str} [{q['id']}] ({q['topic_name']})")
    with open(topics_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(updated_topics_lines).strip() + "\n")
    print(f"[✓] Updated {topics_file.name} with renumbered sequence")

    # 12. Prepare clean template for explanations.txt
    exp_file = WORKING_DIR / "explanations.txt"
    exp_template_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:02d}"
        exp_template_lines.append(f"#{num_str} [{q['id']}] ({q['topic_name']})")
        exp_template_lines.append("EDUCATIONAL OBJECTIVE:\n")
        exp_template_lines.append("HIGH YIELD NOTE:\n")
        exp_template_lines.append("EXPLANATION:\n")
        exp_template_lines.append("---\n")

    with open(exp_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(exp_template_lines).strip() + "\n")
    print(f"[✓] Initialized {exp_file.name} with {len(sorted_questions)} template blocks")

    print("\n=== Neurosurgery & Pediatric Surgery Sorting Completed Successfully ===")

if __name__ == "__main__":
    main()
