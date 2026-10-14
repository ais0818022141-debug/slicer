import pandas as pd
import random
import re
import sys
import json
from pathlib import Path

# Ensure UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
WORKING_DIR = BASE_DIR / "working_on"
SUPP_CSV = WORKING_DIR / "تكملة أسئلة الجراحة العامة.csv"

rng = random.Random(42)
LETTERS = ['A', 'B', 'C', 'D', 'E']

def norm_stem(s):
    if not s or not isinstance(s, str):
        return ''
    s = s.strip()
    # Clean accidental duplicate option attached to Q12
    s = re.sub(r'التشخيص الأكثر احتمالاً\s*التهاب مرارة حاد\s*[:：]*', 'التشخيص الأكثر احتمالاً:', s)
    s = re.sub(r'[\s:：]*رأس\s*[:：]*$', '', s)
    s = re.sub(r'[\s:：؟?.]+$', '', s)
    return s + ':'

def norm_option(s):
    if not s or not isinstance(s, str):
        return ''
    s = s.strip()
    s = re.sub(r'[\s.:：]+$', '', s)
    return s + '.'

def clean_topic(t):
    if not t or not isinstance(t, str):
        return 'الموضوع'
    return re.sub(r'^\d+\.\s*', '', t).strip()

def main():
    print("=== Generating AI Prompt for Supplementary General Surgery Questions ===")
    
    df = pd.read_csv(SUPP_CSV, encoding='utf-8-sig', header=None)
    print(f"Loaded {len(df)} questions from {SUPP_CSV.name}")

    questions = []
    md_lines = []
    csv_rows = []

    for i in range(len(df)):
        row = df.iloc[i]
        subj = str(row[0]).strip() if pd.notna(row[0]) else "الجراحة العامة"
        date = str(row[1]).strip() if pd.notna(row[1]) else "آب 2025"
        topic = clean_topic(str(row[2]))
        stem = norm_stem(str(row[3]))
        corr = norm_option(str(row[4]))
        wrongs = [norm_option(str(row[col])) for col in range(5, 9) if pd.notna(row[col]) and str(row[col]).strip()]

        choices = [{'text': corr, 'is_correct': True}]
        for w in wrongs:
            choices.append({'text': w, 'is_correct': False})

        rng.shuffle(choices)

        for idx, c in enumerate(choices):
            c['letter'] = LETTERS[idx]

        corr_let = next(c['letter'] for c in choices if c['is_correct'])
        num_str = f"{i+1:02d}"
        qid = f"q_general_surgery_supp_{num_str}"

        q_obj = {
            "id": qid,
            "subject_name": subj,
            "topic_name": topic,
            "title": stem,
            "difficulty": "متوسط",
            "exam_type": "national_board",
            "exam_period": date,
            "points": 10,
            "is_free": 1,
            "correct_option": corr_let,
            "vignette": None,
            "attending_clue": None,
            "educational_objective": "",
            "high_yield_note": "",
            "explanation": "",
            "options": choices
        }
        questions.append(q_obj)

        # Build AI Markdown lines
        md_lines.append(f"#{num_str} [{qid}] ({topic})")
        md_lines.append(f"السؤال: {stem}")
        md_lines.append(f"الجواب: {corr_let}")
        for c in choices:
            let = c['letter']
            txt = c['text']
            if c['is_correct']:
                md_lines.append(f"{let}) {txt} (الصحيح)")
            else:
                md_lines.append(f"{let}) {txt}")
        md_lines.append("---")
        md_lines.append("")

        # CSV row
        csv_row = {
            "Question_ID": qid,
            "Medical_Subject": subj,
            "Exam_Date": date,
            "Chapter_or_Section": topic,
            "Question_Text": stem,
            "Explanation": "",
            "High_Yield_Note": "",
            "Correct_Answer": corr
        }
        for w_i, w_txt in enumerate(wrongs, start=1):
            csv_row[f"Wrong_Answer_{w_i}"] = w_txt
        for w_i in range(len(wrongs) + 1, 6):
            csv_row[f"Wrong_Answer_{w_i}"] = ""
        csv_rows.append(csv_row)

    # 1. Export AI Markdown
    out_md = WORKING_DIR / "general_surgery_supp_ai.md"
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines).strip() + "\n")
    print(f"[✓] Created AI Prompt: {out_md.name}")

    # 2. Export Companion JSON
    out_json = WORKING_DIR / "general_surgery_supp.json"
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Created Companion JSON: {out_json.name}")

    # 3. Export Companion CSV
    out_csv = WORKING_DIR / "general_surgery_supp.csv"
    pd.DataFrame(csv_rows).to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f"[✓] Created Companion CSV: {out_csv.name}")

    print(f"=== Successfully prepared {len(questions)} supplementary questions! ===")

if __name__ == "__main__":
    main()
