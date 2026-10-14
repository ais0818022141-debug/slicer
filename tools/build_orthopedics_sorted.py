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

def main():
    print("=== Building Sorted Orthopedic Surgery Dataset (الجراحة العظمية) ===")

    # 1. Load topics.txt mapping
    topics_file = WORKING_DIR / "topics.txt"
    topics_map = {}
    with open(topics_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^#(\d+)\s+\[(.*?)\]\s+\((.*)\)$', line)
            if m:
                qnum = int(m.group(1))
                topic = m.group(3).strip()
                topics_map[qnum] = topic

    print(f"[✓] Loaded {len(topics_map)} topic assignments from topics.txt")
    assert len(topics_map) == 88, f"Expected 88 topics, got {len(topics_map)}"

    # 2. Load questions from orthopedics_all.json
    master_json_path = WORKING_DIR / "orthopedics_all.json"
    with open(master_json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    print(f"[✓] Loaded {len(questions)} questions from orthopedics_all.json")

    # Attach topic and original index
    for idx, q in enumerate(questions, start=1):
        q['original_num'] = idx
        q['original_id'] = q.get('id')
        q['topic_name'] = topics_map.get(idx, 'غير محدد')

    # 3. Define the ordered topic list
    topic_order = [
        'مبادئ الرضوض والتقييم وتدبير الكسور واختلاطاتها العامة',
        'كسور وخلوع الطرف العلوي والكتف والرسغ',
        'كسور وخلوع الحوض والطرف السفلي والقدم والكاحل',
        'أذيات الأوتار والأربطة والغضاريف والمحفظة المفصلية',
        'جراحة عظام الأطفال وتشوهات العمود الفقري وصفائح النمو',
        'أمراض المفاصل التنكسية والإنتانات العظمية المفصلية',
        'أورام العظام السليمة والخبيثة والآفات شبيهة الورم'
    ]

    # Verify all topics in questions match the defined order
    all_assigned_topics = set(q['topic_name'] for q in questions)
    for t in all_assigned_topics:
        assert t in topic_order, f"Unrecognized topic: {t}"

    # 4. Group questions by topic and sort chronologically (newest first)
    sorted_questions = []
    print("\nTopic Breakdown & Sorting:")
    for topic in topic_order:
        topic_qs = [q for q in questions if q['topic_name'] == topic]
        # Sort chronologically: newest exam date first, then preserve original order
        topic_qs.sort(key=lambda q: (parse_exam_date(q.get('exam_period', '')), -q['original_num']), reverse=True)
        sorted_questions.extend(topic_qs)
        print(f" - {topic}: {len(topic_qs)} questions")

    assert len(sorted_questions) == 88, f"Expected 88 sorted questions, got {len(sorted_questions)}"

    # 5. Renumber questions sequentially q_orthopedics_01 to q_orthopedics_88
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:02d}"
        q['id'] = f"q_orthopedics_{num_str}"

    # 6. Save updated orthopedics_all.json
    with open(master_json_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_questions, f, ensure_ascii=False, indent=2)
    print(f"\n[✓] Saved sorted master JSON: {master_json_path.name}")

    # 7. Save updated orthopedics_all.csv and orthopedics.csv
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
            "Medical_Subject": q.get('subject_name', 'الجراحة العظمية'),
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

    df_sorted = pd.DataFrame(csv_rows)
    master_csv_path = WORKING_DIR / "orthopedics_all.csv"
    clean_csv_path = WORKING_DIR / "orthopedics.csv"
    df_sorted.to_csv(master_csv_path, index=False, encoding='utf-8-sig')
    df_sorted.to_csv(clean_csv_path, index=False, encoding='utf-8-sig')
    print(f"[✓] Saved sorted CSVs: {master_csv_path.name} and {clean_csv_path.name}")

    # 8. Save updated orthopedics_all_ai.md
    ai_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        topic = q.get('topic_name', '')
        date_str = q.get('exam_period', '')
        title = q['title']
        cor_let = q.get('correct_option', '')

        ai_lines.append(f"#{num_str} [{qid}] ({topic}) - {date_str}")
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

    master_ai_path = WORKING_DIR / "orthopedics_all_ai.md"
    with open(master_ai_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(ai_lines).strip() + "\n")
    print(f"[✓] Saved sorted AI prompt: {master_ai_path.name}")

    # 9. Update sliced chunks in csv/, json/, and md/
    csv_dir = WORKING_DIR / "csv"
    json_dir = WORKING_DIR / "json"
    md_dir = WORKING_DIR / "md"
    chunk_size = 12
    total_chunks = (len(sorted_questions) + chunk_size - 1) // chunk_size

    for c_idx in range(total_chunks):
        c_num = c_idx + 1
        tag = f"{c_num:02d}"
        start_i = c_idx * chunk_size
        end_i = min(start_i + chunk_size, len(sorted_questions))

        # JSON chunk
        chunk_qs = sorted_questions[start_i:end_i]
        c_json = json_dir / f"orthopedics_{tag}.json"
        with open(c_json, 'w', encoding='utf-8') as f:
            json.dump(chunk_qs, f, ensure_ascii=False, indent=2)

        # CSV chunk
        chunk_df = df_sorted.iloc[start_i:end_i]
        c_csv = csv_dir / f"orthopedics_{tag}.csv"
        chunk_df.to_csv(c_csv, index=False, encoding='utf-8-sig')

        # MD chunk
        c_md_lines = []
        for idx_c, q in enumerate(chunk_qs, start=start_i + 1):
            num_str = f"{idx_c:02d}"
            qid = q['id']
            topic = q.get('topic_name', '')
            date_str = q.get('exam_period', '')
            title = q['title']
            cor_let = q.get('correct_option', '')

            c_md_lines.append(f"#{num_str} [{qid}] ({topic}) - {date_str}")
            c_md_lines.append(f"السؤال: {title}")
            c_md_lines.append(f"الجواب: {cor_let}")
            for opt in q.get('options', []):
                let = opt.get('letter', '')
                txt = opt.get('text', '')
                if opt.get('is_correct'):
                    c_md_lines.append(f"{let}) {txt} (الصحيح)")
                else:
                    c_md_lines.append(f"{let}) {txt}")
            c_md_lines.append("---")
            c_md_lines.append("")

        c_md = md_dir / f"orthopedics_{tag}_ai.md"
        with open(c_md, 'w', encoding='utf-8') as f:
            f.write("\n".join(c_md_lines).strip() + "\n")

    print(f"[✓] Sliced {total_chunks} chunks in csv/, json/, and md/")

    # 10. Generate explanations.txt template ready for user explanations
    exp_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        topic = q.get('topic_name', '')
        exp_lines.append(f"#{num_str} [{qid}] ({topic})")
        exp_lines.append("EDUCATIONAL OBJECTIVE:\n\n")
        exp_lines.append("HIGH YIELD NOTE:\n\n")
        exp_lines.append("EXPLANATION:\n\n")
        exp_lines.append("---\n")

    exp_file_path = WORKING_DIR / "explanations.txt"
    with open(exp_file_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(exp_lines).strip() + "\n")
    print(f"[✓] Created explanations template: {exp_file_path.name}")

    # 11. Update topics.txt reflecting sorted order
    sorted_topics_lines = []
    for idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        topic = q.get('topic_name', '')
        sorted_topics_lines.append(f"#{num_str} [{qid}] ({topic})")

    with open(topics_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sorted_topics_lines).strip() + "\n")
    print(f"[✓] Updated topics.txt with sorted questions")

    print("\n=== Orthopedics Sorting and Template Generation Completed Successfully! ===")

if __name__ == "__main__":
    main()
