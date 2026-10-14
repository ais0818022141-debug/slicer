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
FINAL_DIR = BASE_DIR / "final"
MANIFEST_PATH = FINAL_DIR / "manifest.json"
PDF_MAKER_DIR = BASE_DIR / "pdf_maker"
GENERATOR_SCRIPT = PDF_MAKER_DIR / "generator.py"

# Add pdf_maker to path to import generator directly
sys.path.insert(0, str(PDF_MAKER_DIR))
import generator

def clean_explanation_block(block_text: str):
    obj_m = re.search(r'EDUCATIONAL\s+OBJECTIVE\s*:\s*(.*?)(?=\nHIGH\s+YIELD\s+NOTE|\Z)', block_text, re.DOTALL | re.IGNORECASE)
    obj = obj_m.group(1).strip() if obj_m else ""

    note_m = re.search(r'HIGH\s+YIELD\s+NOTE\s*:\s*(.*?)(?=\nEXPLANATION|\Z)', block_text, re.DOTALL | re.IGNORECASE)
    note = note_m.group(1).strip() if note_m else ""

    exp_m = re.search(r'EXPLANATION\s*:\s*(.*)', block_text, re.DOTALL | re.IGNORECASE)
    exp_raw = exp_m.group(1).strip() if exp_m else ""
    exp_raw = re.sub(r'\n\s*---\s*$', '', exp_raw).strip()

    flag = ""
    flag_m = re.search(r'\(?\s*CLINICAL\s+ERROR\s+FLAG\s*[:：]?\s*(.*?)\)?\s*$', exp_raw, re.DOTALL | re.IGNORECASE)
    if flag_m:
        flag = flag_m.group(1).strip().rstrip(')')
        exp_raw = exp_raw[:flag_m.start()].strip()

    split_m = re.search(r'(?:^|\n)\s*[\*\-•]?\s*الخيارات\s+الأخرى\s*[:：]\s*(.*)', exp_raw, re.DOTALL)
    if split_m:
        khiarat_raw = split_m.group(1).strip()
        t3leel_raw = exp_raw[:split_m.start()].strip()
    else:
        khiarat_raw = ""
        t3leel_raw = exp_raw

    t3leel = re.sub(r'^(?:[\*\-•]\s*)?(التعليل\s+السريري|التعليل|الشرح)\s*[:：]\s*', '', t3leel_raw).strip()

    lines = [l.strip() for l in khiarat_raw.splitlines() if l.strip()]
    formatted_options = []
    for l in lines:
        l = re.sub(r'^\*\s*', '', l).strip()
        parts = re.split(r'(?<=[.،؛\)])\s+(?=[A-E][:\)\s])', l)
        if len(parts) == 1 and not re.match(r'^[A-E][:\)]\s', l):
            parts = re.split(r'(?<=[.،؛])\s+(?=[A-E]\s)', l)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            m_opt = re.match(r'^([A-E])\s*[:）)]\s*(.*)', p)
            if m_opt:
                formatted_options.append(f"{m_opt.group(1)}) {m_opt.group(2).strip()}")
            else:
                m_opt2 = re.match(r'^([A-E])\s+([\u0600-\u06FF].*)', p)
                if m_opt2:
                    formatted_options.append(f"{m_opt2.group(1)}) {m_opt2.group(2).strip()}")
                else:
                    formatted_options.append(p)

    clean_parts = []
    clean_parts.append(f"- التعليل السريري: {t3leel}")
    if formatted_options:
        clean_parts.append("- الخيارات الأخرى:\n" + "\n\n".join(formatted_options))
    if flag:
        clean_parts.append(f"- تنبيه سريري (Clinical Error Flag): {flag}")

    final_exp = "\n\n".join(clean_parts).strip()
    return {
        "educational_objective": obj,
        "high_yield_note": note,
        "explanation": final_exp
    }

def parse_all_explanations(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    pattern = re.compile(r'(?:^|\n)\s*#\s*(\d+)(?:\s+\[.*?\])?(?:\s+\(.*?\))?\s*\n')
    matches = list(pattern.finditer(text))

    blocks = {}
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks[num] = text[start:end].strip()

    parsed_data = {}
    for num, block_text in blocks.items():
        parsed_data[num] = clean_explanation_block(block_text)

    return parsed_data

def main():
    print("=== Merging Explanations and Deploying Urology Surgery to final/ ===")

    # 1. Parse explanations.txt
    exp_file = WORKING_DIR / "explanations.txt"
    print(f"Parsing {exp_file.name}...")
    exp_map = parse_all_explanations(exp_file)
    print(f"[✓] Parsed {len(exp_map)} explanation blocks")
    assert len(exp_map) == 86, f"Expected 86 blocks, got {len(exp_map)}"

    # 2. Load master questions
    master_json_path = WORKING_DIR / "urology_all.json"
    with open(master_json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    print(f"Loaded {len(questions)} questions from {master_json_path.name}")
    assert len(questions) == 86

    # 3. Merge explanations into questions
    for idx, q in enumerate(questions, start=1):
        entry = exp_map[idx]
        q['educational_objective'] = entry['educational_objective']
        q['high_yield_note'] = entry['high_yield_note']
        q['explanation'] = entry['explanation']

    # Update working_on/urology_all.json
    with open(master_json_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Updated {master_json_path.name}")

    # 4. Update working_on/urology_all.csv and urology.csv
    csv_rows = []
    for q in questions:
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
            "Medical_Subject": q.get('subject_name', 'الجراحة البولية'),
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

    df = pd.DataFrame(csv_rows)
    df.to_csv(WORKING_DIR / "urology_all.csv", index=False, encoding='utf-8-sig')
    df.to_csv(WORKING_DIR / "urology.csv", index=False, encoding='utf-8-sig')
    print(f"[✓] Updated urology_all.csv and urology.csv")

    # 5. Generate urology_all_ai_temp.md in working_on
    temp_md_lines = []
    for idx, q in enumerate(questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        topic = q.get('topic_name', '')
        date_str = q.get('exam_period', '')
        title = q['title']
        cor_let = q.get('correct_option', '')

        temp_md_lines.append(f"#{num_str} [{qid}] ({topic}) - {date_str}")
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

    temp_md_path = WORKING_DIR / "urology_all_ai_temp.md"
    with open(temp_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(temp_md_lines).strip() + "\n")
    print(f"[✓] Saved clinical review markdown: {temp_md_path.name}")

    # 6. Update clean explanations.txt in working_on
    clean_exp_lines = []
    for idx, q in enumerate(questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        topic = q.get('topic_name', '')
        entry = exp_map[idx]
        clean_exp_lines.append(f"#{num_str} [{qid}] ({topic})")
        clean_exp_lines.append(f"EDUCATIONAL OBJECTIVE:\n{entry['educational_objective']}\n")
        clean_exp_lines.append(f"HIGH YIELD NOTE:\n{entry['high_yield_note']}\n")
        clean_exp_lines.append(f"EXPLANATION:\n{entry['explanation']}\n")
        clean_exp_lines.append("---\n")

    with open(exp_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(clean_exp_lines).strip() + "\n")
    print(f"[✓] Refreshed clean {exp_file.name}")

    # 7. Update sliced chunks in working_on/csv/ and working_on/json/
    csv_dir = WORKING_DIR / "csv"
    json_dir = WORKING_DIR / "json"
    chunk_size = 12
    total_chunks = (len(questions) + chunk_size - 1) // chunk_size

    for c_idx in range(total_chunks):
        c_num = c_idx + 1
        tag = f"{c_num:02d}"
        start_i = c_idx * chunk_size
        end_i = min(start_i + chunk_size, len(questions))

        chunk_qs = questions[start_i:end_i]
        c_json = json_dir / f"urology_{tag}.json"
        with open(c_json, 'w', encoding='utf-8') as f:
            json.dump(chunk_qs, f, ensure_ascii=False, indent=2)

        chunk_df = df.iloc[start_i:end_i]
        c_csv = csv_dir / f"urology_{tag}.csv"
        chunk_df.to_csv(c_csv, index=False, encoding='utf-8-sig')

    print(f"[✓] Synchronized {total_chunks} chunks in csv/ and json/")

    # 8. Deploy Package to final/urology
    target_dir = FINAL_DIR / "urology"
    print(f"\n=======================================================")
    print(f" Packaging Subject: الجراحة البولية (urology)")
    print(f" Total questions: {len(questions)}")
    print(f" Target folder: {target_dir}")
    print(f"=======================================================")
    target_dir.mkdir(parents=True, exist_ok=True)

    # final JSON
    final_json = target_dir / "urology_all.json"
    with open(final_json, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Created final JSON: {final_json.name}")

    # final CSV
    final_csv = target_dir / "urology_all.csv"
    df.to_csv(final_csv, index=False, encoding='utf-8-sig')
    print(f"[✓] Created final CSV: {final_csv.name}")

    # final clean AI md
    final_ai = target_dir / "urology_all_ai.md"
    shutil.copy2(WORKING_DIR / "urology_all_ai.md", final_ai)
    print(f"[✓] Created final clean AI Markdown: {final_ai.name}")

    # final full clinical review md
    final_temp_md = target_dir / "urology_all_ai_temp.md"
    shutil.copy2(temp_md_path, final_temp_md)
    print(f"[✓] Created final review AI Markdown: {final_temp_md.name}")

    # final explanations.txt
    final_exp = target_dir / "explanations.txt"
    shutil.copy2(exp_file, final_exp)
    print(f"[✓] Created final explanations text: {final_exp.name}")

    # 9. Generate HTML study engines and views
    print(f"[>] Generating HTML/PDF study views for urology...")
    try:
        generator.process_single_file(final_json, output_dir=target_dir)
        print(f"[✓] Successfully generated HTML views for urology")
    except Exception as e:
        print(f"[!] Warning running generator for urology: {e}")

    # 10. Update final/manifest.json
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        ordered_topics = []
        for q in questions:
            t = q.get('topic_name')
            if t and t not in ordered_topics:
                ordered_topics.append(t)

        manifest.setdefault('subjects', {})
        manifest['subjects']['urology'] = {
            "subject_name": "الجراحة البولية",
            "folder": "final/urology",
            "questions_count": len(questions),
            "files": {
                "csv": "urology_all.csv",
                "json": "urology_all.json",
                "ai_prompt": "urology_all_ai.md"
            },
            "topics": ordered_topics
        }

        manifest["subjects_count"] = len(manifest["subjects"])
        manifest["total_questions"] = sum(s.get("questions_count", 0) for s in manifest["subjects"].values())

        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] Updated manifest.json: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")

    print("\n=== Urology Deployment to final/ Completed Successfully! ===")

if __name__ == "__main__":
    main()
