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

def build_subject_package(subject_slug, subject_name, questions, target_dir):
    print(f"\n=======================================================")
    print(f" Packaging Subject: {subject_name} ({subject_slug})")
    print(f" Total questions: {len(questions)}")
    print(f" Target folder: {target_dir}")
    print(f"=======================================================")

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Renumber questions within the subject
    renumbered_questions = []
    for idx, raw_q in enumerate(questions, start=1):
        q = dict(raw_q)
        num_str = f"{idx:02d}"
        q['id'] = f"q_{subject_slug}_{num_str}"
        q['subject_name'] = subject_name
        renumbered_questions.append(q)

    # 2. Write JSON: <subject_slug>_all.json
    json_path = target_dir / f"{subject_slug}_all.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(renumbered_questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Created JSON: {json_path.name} ({len(renumbered_questions)} questions)")

    # 3. Write CSV: <subject_slug>_all.csv
    csv_rows = []
    for q in renumbered_questions:
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
            "Medical_Subject": subject_name,
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

    csv_path = target_dir / f"{subject_slug}_all.csv"
    df = pd.DataFrame(csv_rows)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"[✓] Created CSV: {csv_path.name}")

    # 4. Write Clean AI Markdown: <subject_slug>_all_ai.md (without explanations)
    ai_lines = []
    for idx, q in enumerate(renumbered_questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        topic = q.get('topic_name', '')
        title = q.get('title', '')
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

    ai_md_path = target_dir / f"{subject_slug}_all_ai.md"
    with open(ai_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(ai_lines).strip() + "\n")
    print(f"[✓] Created clean AI Markdown: {ai_md_path.name}")

    # 5. Write Full Clinical Review AI Markdown: <subject_slug>_all_ai_temp.md
    temp_md_lines = []
    for idx, q in enumerate(renumbered_questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        topic = q.get('topic_name', '')
        title = q.get('title', '')
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

    temp_md_path = target_dir / f"{subject_slug}_all_ai_temp.md"
    with open(temp_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(temp_md_lines).strip() + "\n")
    print(f"[✓] Created full review AI Markdown: {temp_md_path.name}")

    # 6. Write explanations.txt
    exp_lines = []
    for idx, q in enumerate(renumbered_questions, start=1):
        num_str = f"{idx:02d}"
        qid = q['id']
        topic = q.get('topic_name', '')
        obj = q.get('educational_objective', '')
        hyn = q.get('high_yield_note', '')
        exp = q.get('explanation', '')

        exp_lines.append(f"#{num_str} [{qid}] ({topic})")
        exp_lines.append(f"EDUCATIONAL OBJECTIVE:\n{obj}\n")
        exp_lines.append(f"HIGH YIELD NOTE:\n{hyn}\n")
        exp_lines.append(f"EXPLANATION:\n{exp}\n")
        exp_lines.append("---\n")

    exp_path = target_dir / "explanations.txt"
    with open(exp_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(exp_lines).strip() + "\n")
    print(f"[✓] Created explanations text: {exp_path.name}")

    # 7. Generate HTML/PDF study views via generator.py
    print(f"[>] Generating HTML/PDF study views for {subject_slug}...")
    try:
        generator.process_single_file(json_path, output_dir=target_dir)
        print(f"[✓] Successfully generated HTML views for {subject_slug}")
    except Exception as e:
        print(f"[!] Warning running generator for {subject_slug}: {e}")

    return renumbered_questions

def main():
    print("=== Deploying Neurosurgery & Pediatric Surgery as Separate Subjects to final/ ===")

    # Load master questions with explanations from working_on
    master_json = WORKING_DIR / "neuro_peds_all.json"
    with open(master_json, 'r', encoding='utf-8') as f:
        all_qs = json.load(f)

    print(f"Loaded {len(all_qs)} total questions from {master_json.name}")

    # Separate into the two subjects
    neuro_qs = [q for q in all_qs if q.get('subject_name') == "الجراحة العصبية"]
    peds_qs = [q for q in all_qs if q.get('subject_name') == "جراحة الأطفال"]

    print(f"Neurosurgery questions: {len(neuro_qs)}")
    print(f"Pediatric surgery questions: {len(peds_qs)}")

    # 1. Build and deploy Neurosurgery package
    neuro_dir = FINAL_DIR / "neurosurgery"
    neuro_renumbered = build_subject_package("neurosurgery", "الجراحة العصبية", neuro_qs, neuro_dir)

    # 2. Build and deploy Pediatric Surgery package
    peds_dir = FINAL_DIR / "ped_surgery"
    peds_renumbered = build_subject_package("ped_surgery", "جراحة الأطفال", peds_qs, peds_dir)

    # 3. Update final/manifest.json
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Neurosurgery entry
        ordered_neuro_topics = []
        for q in neuro_renumbered:
            t = q.get('topic_name')
            if t and t not in ordered_neuro_topics:
                ordered_neuro_topics.append(t)

        manifest.setdefault('subjects', {})
        manifest['subjects']['neurosurgery'] = {
            "subject_name": "الجراحة العصبية",
            "folder": "final/neurosurgery",
            "questions_count": len(neuro_renumbered),
            "files": {
                "csv": "neurosurgery_all.csv",
                "json": "neurosurgery_all.json",
                "ai_prompt": "neurosurgery_all_ai.md"
            },
            "topics": ordered_neuro_topics
        }

        # Pediatric Surgery entry
        ordered_peds_topics = []
        for q in peds_renumbered:
            t = q.get('topic_name')
            if t and t not in ordered_peds_topics:
                ordered_peds_topics.append(t)

        manifest['subjects']['ped_surgery'] = {
            "subject_name": "جراحة الأطفال",
            "folder": "final/ped_surgery",
            "questions_count": len(peds_renumbered),
            "files": {
                "csv": "ped_surgery_all.csv",
                "json": "ped_surgery_all.json",
                "ai_prompt": "ped_surgery_all_ai.md"
            },
            "topics": ordered_peds_topics
        }

        manifest["subjects_count"] = len(manifest["subjects"])
        manifest["total_questions"] = sum(s.get("questions_count", 0) for s in manifest["subjects"].values())

        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] Updated manifest.json: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")

    print("\n=== Final Deployment of Both Subjects Completed Successfully! ===")

if __name__ == "__main__":
    main()
