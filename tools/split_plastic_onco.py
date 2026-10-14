#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TealMED Plastic Surgery & Oncology Splitter
===========================================
Splits final/plastic_onco into two dedicated subjects in final/:
1. final/plastic/ (الجراحة التجميلية)
   - 66 questions: الحروق (30), سرطانات الجلد والآفات السطحية (36)
   - IDs: q_plastic_01 .. q_plastic_66
2. final/onco/ (جراحة الأورام)
   - 11 questions: جراحة أورام الغدة الدرقية وجارات الدرق (11)
   - IDs: q_onco_01 .. q_onco_11

Generates full packages (.csv, .json, _ai.md, _ai_temp.md, explanations.txt, .html, topics/, sessions/, years/)
and updates final/manifest.json.
"""

import os
import sys
import csv
import json
import shutil
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
FINAL_DIR = BASE_DIR / "final"
SRC_DIR = FINAL_DIR / "plastic_onco"
MANIFEST_PATH = FINAL_DIR / "manifest.json"
PDF_MAKER_DIR = BASE_DIR / "pdf_maker"

sys.path.insert(0, str(PDF_MAKER_DIR))
import generator

def export_subject_package(subject_slug, subject_name, questions_json, csv_rows, fieldnames, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    count = len(questions_json)
    num_width = 3 if count >= 100 else 2

    # 1. Update questions data
    updated_json = []
    for idx, q in enumerate(questions_json, start=1):
        num_str = f"{idx:0{num_width}d}"
        q_copy = dict(q)
        q_copy['id'] = f"q_{subject_slug}_{num_str}"
        q_copy['subject_name'] = subject_name
        updated_json.append(q_copy)

    # 2. Update CSV rows
    updated_csv_rows = []
    for idx, r in enumerate(csv_rows, start=1):
        num_str = f"{idx:0{num_width}d}"
        r_copy = dict(r)
        r_copy['Question_ID'] = f"q_{subject_slug}_{num_str}"
        r_copy['Medical_Subject'] = subject_name
        updated_csv_rows.append(r_copy)

    # 3. Save CSV
    csv_path = output_dir / f"{subject_slug}_all.csv"
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_csv_rows)
    print(f"[✓] Created CSV: {csv_path.name} ({len(updated_csv_rows)} rows)")

    # 4. Save JSON
    json_path = output_dir / f"{subject_slug}_all.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(updated_json, f, ensure_ascii=False, indent=2)
    print(f"[✓] Created JSON: {json_path.name} ({len(updated_json)} items)")

    # 5. Save Clean AI Prompt (_all_ai.md)
    ai_lines = []
    for idx, item in enumerate(updated_json, start=1):
        num_str = f"{idx:0{num_width}d}"
        q_id = item["id"]
        topic = item.get("topic_name", "")
        stem_val = item.get("title", "")
        cor_let = item.get("correct_option", "")

        ai_lines.append(f"#{num_str} [{q_id}] ({topic})")
        ai_lines.append(f"السؤال: {stem_val}")
        ai_lines.append(f"الجواب: {cor_let}")
        for opt in item.get("options", []):
            let = opt.get("letter", "")
            txt = opt.get("text", "")
            if opt.get("is_correct", False):
                ai_lines.append(f"{let}) {txt} (الصحيح)")
            else:
                ai_lines.append(f"{let}) {txt}")
        ai_lines.append("---")
        ai_lines.append("")

    ai_path = output_dir / f"{subject_slug}_all_ai.md"
    with open(ai_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(ai_lines).strip() + "\n")
    print(f"[✓] Created AI Markdown: {ai_path.name}")

    # 6. Save Full-explanation AI Markdown (_all_ai_temp.md)
    ai_temp_lines = []
    for idx, item in enumerate(updated_json, start=1):
        num_str = f"{idx:0{num_width}d}"
        q_id = item["id"]
        topic = item.get("topic_name", "")
        stem_val = item.get("title", "")
        cor_let = item.get("correct_option", "")

        ai_temp_lines.append(f"#{num_str} [{q_id}] ({topic})")
        ai_temp_lines.append(f"السؤال: {stem_val}")
        ai_temp_lines.append(f"الجواب: {cor_let}")
        for opt in item.get("options", []):
            let = opt.get("letter", "")
            txt = opt.get("text", "")
            if opt.get("is_correct", False):
                ai_temp_lines.append(f"{let}) {txt} (الصحيح)")
            else:
                ai_temp_lines.append(f"{let}) {txt}")

        if item.get("educational_objective"):
            ai_temp_lines.append(f"الهدف التعليمي: {item['educational_objective']}")
        if item.get("high_yield_note"):
            ai_temp_lines.append(f"ملاحظة عالية الأهمية: {item['high_yield_note']}")

        exp_val = (item.get("explanation") or "").strip()
        if exp_val:
            ai_temp_lines.append("الشرح:")
            ai_temp_lines.append(exp_val)

        ai_temp_lines.append("---")
        ai_temp_lines.append("")

    ai_temp_path = output_dir / f"{subject_slug}_all_ai_temp.md"
    with open(ai_temp_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(ai_temp_lines).strip() + "\n")
    print(f"[✓] Created Full AI Markdown: {ai_temp_path.name}")

    # 7. Save Explanations (explanations.txt)
    exp_lines = []
    for idx, item in enumerate(updated_json, start=1):
        num_str = f"{idx:0{num_width}d}"
        obj = (item.get("educational_objective") or "").strip()
        hy = (item.get("high_yield_note") or "").strip()
        exp = (item.get("explanation") or "").strip()

        exp_lines.append(f"#{num_str}")
        exp_lines.append("EDUCATIONAL OBJECTIVE:")
        exp_lines.append(obj)
        exp_lines.append("")
        exp_lines.append("HIGH YIELD NOTE:")
        exp_lines.append(hy)
        exp_lines.append("")
        exp_lines.append("EXPLANATION:")
        exp_lines.append(exp)
        exp_lines.append("")
        exp_lines.append("---")
        exp_lines.append("")

    exp_path = output_dir / "explanations.txt"
    with open(exp_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(exp_lines).strip() + "\n")
    print(f"[✓] Created Explanations file: {exp_path.name}")

    # 8. Rebuild HTML master views and subfolders via generator.py
    print(f"[>] Generating HTML views and packages for {subject_slug}...")
    res = generator.process_single_file(json_path)
    print(f"[✓] HTML master and subfolders generated: {res.name if res else 'Done'}")

    return updated_json


def main():
    print("=" * 65)
    print(" Splitting plastic_onco into plastic and onco ")
    print("=" * 65)

    # 1. Load source files
    src_csv = SRC_DIR / "plastic_onco_all.csv"
    src_json = SRC_DIR / "plastic_onco_all.json"

    with open(src_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        all_csv_rows = list(reader)

    with open(src_json, 'r', encoding='utf-8') as f:
        all_json_data = json.load(f)

    print(f"Total source items: {len(all_csv_rows)} CSV rows, {len(all_json_data)} JSON items")

    # Plastic: items 0 to 65 (66 items)
    # Onco: items 66 to 76 (11 items)
    plastic_csv = all_csv_rows[:66]
    plastic_json = all_json_data[:66]

    onco_csv = all_csv_rows[66:]
    onco_json = all_json_data[66:]

    print(f"Plastic items: {len(plastic_csv)} CSV, {len(plastic_json)} JSON")
    print(f"Onco items: {len(onco_csv)} CSV, {len(onco_json)} JSON")

    # 2. Export final/plastic/
    print("\n--- Exporting final/plastic/ (الجراحة التجميلية) ---")
    plastic_dir = FINAL_DIR / "plastic"
    plastic_updated_json = export_subject_package(
        subject_slug="plastic",
        subject_name="الجراحة التجميلية",
        questions_json=plastic_json,
        csv_rows=plastic_csv,
        fieldnames=fieldnames,
        output_dir=plastic_dir
    )

    # 3. Export final/onco/
    print("\n--- Exporting final/onco/ (جراحة الأورام) ---")
    onco_dir = FINAL_DIR / "onco"
    onco_updated_json = export_subject_package(
        subject_slug="onco",
        subject_name="جراحة الأورام",
        questions_json=onco_json,
        csv_rows=onco_csv,
        fieldnames=fieldnames,
        output_dir=onco_dir
    )

    # 4. Update manifest.json
    print("\n--- Updating final/manifest.json ---")
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        subjects = manifest.get("subjects", {})

        # Remove plastic_onco from active subjects
        if "plastic_onco" in subjects:
            del subjects["plastic_onco"]

        # Add plastic
        ordered_plastic_topics = []
        for q in plastic_updated_json:
            t = q.get("topic_name")
            if t and t not in ordered_plastic_topics:
                ordered_plastic_topics.append(t)

        subjects["plastic"] = {
            "subject_name": "الجراحة التجميلية",
            "folder": "final/plastic",
            "questions_count": len(plastic_updated_json),
            "files": {
                "csv": "plastic_all.csv",
                "json": "plastic_all.json",
                "ai_prompt": "plastic_all_ai.md"
            },
            "topics": ordered_plastic_topics
        }

        # Add onco
        ordered_onco_topics = []
        for q in onco_updated_json:
            t = q.get("topic_name")
            if t and t not in ordered_onco_topics:
                ordered_onco_topics.append(t)

        subjects["onco"] = {
            "subject_name": "جراحة الأورام",
            "folder": "final/onco",
            "questions_count": len(onco_updated_json),
            "files": {
                "csv": "onco_all.csv",
                "json": "onco_all.json",
                "ai_prompt": "onco_all_ai.md"
            },
            "topics": ordered_onco_topics
        }

        manifest["subjects_count"] = len(subjects)
        manifest["total_questions"] = sum(s.get("questions_count", 0) for s in subjects.values())

        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"[✓] Manifest updated successfully: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")

    print("\n[SUCCESS] Split completed successfully!")

if __name__ == "__main__":
    main()
