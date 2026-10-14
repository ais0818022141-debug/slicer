import os
import sys
import re
import json
import random
import pandas as pd
from pathlib import Path

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
WORKING_DIR = BASE_DIR / "working_on"
RAW_CSV = WORKING_DIR / "أسئلة دورات الجراحة العظمية.csv"
CLEAN_CSV = WORKING_DIR / "orthopedics.csv"
BACKUP_DIR = WORKING_DIR / ".backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def safe_clean_text(val):
    if val is None or pd.isna(val):
        return ""
    text = str(val)
    text = text.replace("_x000D_", "\n").replace("*x000D*", "\n")
    # Strip HTML tags
    text = re.sub(r'</?(?:html|body|p|span|div|br|b|i|strong|em|font|table|tbody|tr|td|th|ul|ol|li|a|h[1-6]|style|script)\b[^>]*>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'(?:style|class|id)\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    # Remove tatweel / kashida
    text = re.sub(r'[\u0640]', '', text)
    # Clean whitespace
    lines = []
    for line in text.splitlines():
        l_clean = re.sub(r'[ \t\f\v]+', ' ', line).strip()
        if l_clean:
            lines.append(l_clean)
    return "\n".join(lines).strip()

def normalize_date(val):
    d = safe_clean_text(val)
    d = re.sub(r'\s+', ' ', d).strip()
    return d

def main():
    print("=== Initial Processing of Orthopedic Surgery Questions (الجراحة العظمية) ===")

    # 1. Read raw CSV
    print(f"Reading raw CSV: {RAW_CSV.name}...")
    df_raw = pd.read_csv(RAW_CSV, encoding='utf-8-sig')
    print(f"Total rows found: {len(df_raw)}")

    # Backup original
    df_raw.to_csv(BACKUP_DIR / "orthopedics_original_raw.csv", index=False, encoding='utf-8-sig')

    # 2. Build clean standardized dataframe
    clean_rows = []
    for idx, row in df_raw.iterrows():
        q_num = idx + 1
        q_id = f"q_orthopedics_{q_num:02d}"
        med_sub = "الجراحة العظمية"
        exam_d = normalize_date(row.get('Exam_Date', ''))
        topic = safe_clean_text(row.get('Chapter_or_Section', '')) or "الموضوع"
        q_text = safe_clean_text(row.get('Question_Text', ''))
        exp = safe_clean_text(row.get('Explanation', ''))
        correct = safe_clean_text(row.get('Correct_Answer', ''))
        w1 = safe_clean_text(row.get('Wrong_Answer_1', ''))
        w2 = safe_clean_text(row.get('Wrong_Answer_2', ''))
        w3 = safe_clean_text(row.get('Wrong_Answer_3', ''))
        w4 = safe_clean_text(row.get('Wrong_Answer_4', ''))

        clean_rows.append({
            "Question_ID": q_id,
            "Medical_Subject": med_sub,
            "Exam_Date": exam_d,
            "Chapter_or_Section": topic,
            "Question_Text": q_text,
            "Explanation": exp,
            "High_Yield_Note": "",
            "Correct_Answer": correct,
            "Wrong_Answer_1": w1,
            "Wrong_Answer_2": w2,
            "Wrong_Answer_3": w3,
            "Wrong_Answer_4": w4,
        })

    df_clean = pd.DataFrame(clean_rows)
    df_clean.to_csv(CLEAN_CSV, index=False, encoding='utf-8-sig')
    print(f"[✓] Saved clean master CSV: {CLEAN_CSV.name}")

    # 3. Create full master JSON (orthopedics_all.json)
    rng = random.Random(42)
    master_questions = []

    for idx, row in df_clean.iterrows():
        q_id = row['Question_ID']
        raw_choices = [{"text": row['Correct_Answer'], "is_correct": True}]
        for w in [row['Wrong_Answer_1'], row['Wrong_Answer_2'], row['Wrong_Answer_3'], row['Wrong_Answer_4']]:
            if w:
                raw_choices.append({"text": w, "is_correct": False})

        rng.shuffle(raw_choices)
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        formatted_options = []
        correct_letter = None

        for i, opt in enumerate(raw_choices):
            letter = alphabet[i]
            if opt["is_correct"]:
                correct_letter = letter
            formatted_options.append({
                "letter": letter,
                "text": opt["text"],
                "is_correct": opt["is_correct"]
            })

        master_questions.append({
            "id": q_id,
            "subject_name": row['Medical_Subject'],
            "topic_name": row['Chapter_or_Section'],
            "title": row['Question_Text'],
            "exam_period": row['Exam_Date'],
            "explanation": row['Explanation'] or None,
            "high_yield_note": None,
            "educational_objective": None,
            "correct_option": correct_letter,
            "options": formatted_options
        })

    master_json_path = WORKING_DIR / "orthopedics_all.json"
    with open(master_json_path, 'w', encoding='utf-8') as f:
        json.dump(master_questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Saved master JSON: {master_json_path.name}")

    # 4. Generate master AI Markdown (orthopedics_all_ai.md)
    ai_lines = []
    for idx, q in enumerate(master_questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        date_str = q.get('exam_period', '')
        title = q['title']
        cor_let = q.get('correct_option', '')

        ai_lines.append(f"#{num_str} [{qid}] ({date_str})")
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
    print(f"[✓] Saved master AI review: {master_ai_path.name}")

    # 5. Split into chunks of 12 (csv, json, md)
    csv_dir = WORKING_DIR / "csv"
    json_dir = WORKING_DIR / "json"
    md_dir = WORKING_DIR / "md"
    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    chunk_size = 12
    total_chunks = (len(master_questions) + chunk_size - 1) // chunk_size

    for c_idx in range(total_chunks):
        c_num = c_idx + 1
        tag = f"{c_num:02d}"
        start_i = c_idx * chunk_size
        end_i = min(start_i + chunk_size, len(master_questions))

        # JSON chunk
        chunk_qs = master_questions[start_i:end_i]
        c_json = json_dir / f"orthopedics_{tag}.json"
        with open(c_json, 'w', encoding='utf-8') as f:
            json.dump(chunk_qs, f, ensure_ascii=False, indent=2)

        # CSV chunk
        chunk_df = df_clean.iloc[start_i:end_i]
        c_csv = csv_dir / f"orthopedics_{tag}.csv"
        chunk_df.to_csv(c_csv, index=False, encoding='utf-8-sig')

        # MD chunk
        c_md_lines = []
        for idx_c, q in enumerate(chunk_qs, start=start_i + 1):
            num_str = f"{idx_c:02d}"
            qid = q['id']
            date_str = q.get('exam_period', '')
            title = q['title']
            cor_let = q.get('correct_option', '')

            c_md_lines.append(f"#{num_str} [{qid}] ({date_str})")
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

    print(f"[✓] Created {total_chunks} chunks in csv/, json/, and md/")

    # 6. Generate topics.txt template for user
    topics_lines = [
        "# topics.txt - تصنيف مواضيع الجراحة العظمية",
        "# اكتب الموضوع لكل سؤال بين القوسين بجانب رقم السؤال أو أرسل قائمة المواضيع وترتيبها في المحادثة",
        "#" + "=" * 60,
        ""
    ]
    for idx, q in enumerate(master_questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        date_str = q.get('exam_period', '')
        title = q['title'].replace('\n', ' ')
        topics_lines.append(f"#{num_str} [{qid}] ({date_str})")
        topics_lines.append(f"السؤال: {title}")
        topics_lines.append("الموضوع: ")
        topics_lines.append("")

    topics_txt_path = WORKING_DIR / "topics.txt"
    with open(topics_txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(topics_lines).strip() + "\n")
    print(f"[✓] Created topics template: {topics_txt_path.name}")

    print("\n=== Orthopedics Initial Processing Completed Successfully! ===")

if __name__ == "__main__":
    main()
