#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reorder and rename Ophthalmology topics according to user specification:
1. أمراض الملحقات والعين الأمامية
2. أمراض العدسة والزرق
3. أمراض العنبة والشبكية والجسم الزجاجي 
4. أمراض العصب البصري وحركية العين
5. الرضوض والأورام العينية
6. أسواء الانكسار والتشخيص والفحوص العينية
"""

import sys
import os
import re
import csv
import json
import shutil
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
FINAL_OPTHO = BASE_DIR / "final" / "optho"
MANIFEST_PATH = BASE_DIR / "final" / "manifest.json"
PDF_MAKER_DIR = BASE_DIR / "pdf_maker"

TOPIC_MAP = {
    'أمراض الملحقات والعين الأمامية': 'أمراض الملحقات والعين الأمامية',
    'أمراض العدسة والزرق': 'أمراض العدسة والزرق',
    'أمراض العنبة والشبكية والجسم الزجاجي': 'أمراض العنبة والشبكية والجسم الزجاجي',
    'العصبية العينية وحركية العين': 'أمراض العصب البصري وحركية العين',
    'أمراض العصب البصري وحركية العين': 'أمراض العصب البصري وحركية العين',
    'الرضوض والأورام العينية': 'الرضوض والأورام العينية',
    'أسواء الانكسار والتشخيص العيني': 'أسواء الانكسار والتشخيص والفحوص العينية',
    'أسواء الانكسار والتشخيص والفحوص العينية': 'أسواء الانكسار والتشخيص والفحوص العينية'
}

TARGET_ORDER = [
    'أمراض الملحقات والعين الأمامية',
    'أمراض العدسة والزرق',
    'أمراض العنبة والشبكية والجسم الزجاجي',
    'أمراض العصب البصري وحركية العين',
    'الرضوض والأورام العينية',
    'أسواء الانكسار والتشخيص والفحوص العينية'
]

def main():
    print("=== Reordering and Renaming Ophthalmology Topics ===")

    # 1. Load existing JSON
    json_path = FINAL_OPTHO / "optho_all.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    # 2. Load existing CSV
    csv_path = FINAL_OPTHO / "optho_all.csv"
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        csv_rows = list(reader)

    print(f"Loaded {len(questions)} JSON items and {len(csv_rows)} CSV rows.")

    # Build pairs of (json_item, csv_row) matched by ID
    json_by_id = {q['id']: q for q in questions}
    paired = []
    for r in csv_rows:
        qid = r.get('Question_ID') or r.get('\ufeffQuestion_ID')
        jq = json_by_id.get(qid)
        if not jq:
            raise ValueError(f"CSV row {qid} not found in JSON!")
        paired.append((jq, r))

    # Group paired items by target topic
    grouped = {t: [] for t in TARGET_ORDER}
    for jq, r in paired:
        old_topic = (r.get('Chapter_or_Section') or jq.get('topic_name', '')).strip()
        new_topic = TOPIC_MAP.get(old_topic)
        if not new_topic:
            raise ValueError(f"Unknown topic '{old_topic}' for question {jq['id']}")
        
        jq['topic_name'] = new_topic
        r['Chapter_or_Section'] = new_topic
        grouped[new_topic].append((jq, r))

    # Re-assemble in TARGET_ORDER and renumber sequentially
    reordered_json = []
    reordered_csv = []
    global_idx = 1

    print("\n--- Topic Breakdown after Reordering ---")
    for t_idx, topic in enumerate(TARGET_ORDER, 1):
        pair_list = grouped[topic]
        start_q = global_idx
        for jq, r in pair_list:
            new_id = f"q_optho_{global_idx:03d}"
            # Preserve original_id
            if not jq.get('original_id'):
                jq['original_id'] = jq['id']
            jq['id'] = new_id
            r['Question_ID'] = new_id

            reordered_json.append(jq)
            reordered_csv.append(r)
            global_idx += 1
        end_q = global_idx - 1
        print(f"  {t_idx}. {topic} ({len(pair_list)} questions: #{start_q:03d} -> #{end_q:03d})")

    # 3. Save reordered CSV
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reordered_csv)
    print(f"\n[✓] Saved reordered CSV: {csv_path.name} ({len(reordered_csv)} rows)")

    # 4. Save reordered JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(reordered_json, f, ensure_ascii=False, indent=2)
    print(f"[✓] Saved reordered JSON: {json_path.name} ({len(reordered_json)} items)")

    # 5. Build optho_all_ai.md (Clean AI Prompt)
    ai_lines = []
    for idx, item in enumerate(reordered_json, 1):
        num_str = f"{idx:03d}"
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

    with open(FINAL_OPTHO / "optho_all_ai.md", 'w', encoding='utf-8') as f:
        f.write("\n".join(ai_lines).strip() + "\n")
    print("[✓] Updated Clean AI Markdown: optho_all_ai.md")

    # 6. Build optho_all_ai_temp.md (Full Explanation AI Prompt)
    ai_temp_lines = []
    for idx, item in enumerate(reordered_json, 1):
        num_str = f"{idx:03d}"
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

    with open(FINAL_OPTHO / "optho_all_ai_temp.md", 'w', encoding='utf-8') as f:
        f.write("\n".join(ai_temp_lines).strip() + "\n")
    print("[✓] Updated Full AI Markdown: optho_all_ai_temp.md")

    # 7. Build explanations.txt
    exp_lines = []
    for idx, item in enumerate(reordered_json, 1):
        num_str = f"{idx:02d}"
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

    with open(FINAL_OPTHO / "explanations.txt", 'w', encoding='utf-8') as f:
        f.write("\n".join(exp_lines).strip() + "\n")
    print("[✓] Updated explanations.txt (#01 to #192)")

    # 8. Update manifest.json
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        if 'optho' in manifest.get('subjects', {}):
            manifest['subjects']['optho']['questions_count'] = len(reordered_json)
            manifest['subjects']['optho']['topics'] = TARGET_ORDER
        tot = sum(s.get('questions_count', 0) for s in manifest.get('subjects', {}).values())
        manifest['total_questions'] = tot
        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"[✓] Updated manifest.json with new topics order and question count")

    # 9. Clean up old topic HTML files in final/optho/topics/
    topics_sub_dir = FINAL_OPTHO / "topics"
    if topics_sub_dir.exists():
        for old_f in topics_sub_dir.glob("optho_all_*.html"):
            try:
                old_f.unlink()
            except Exception:
                pass
        print("[✓] Cleaned old topic HTML views in topics/")

    # 10. Regenerate HTML/PDF views via generator.py
    print("\n[>] Regenerating HTML views via pdf_maker/generator.py...")
    sys.path.insert(0, str(PDF_MAKER_DIR))
    import generator
    res = generator.process_single_file(json_path)
    print(f"[✓] Generator completed successfully: {res.name if res else 'Done'}")

    print("\n=== All Ophthalmology Topics Reordered and Synced Successfully! ===")

if __name__ == "__main__":
    main()
