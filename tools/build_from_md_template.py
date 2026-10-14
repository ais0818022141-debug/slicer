#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TealMED Markdown Template to Final Subject Package Builder
===========================================================
Parses a question bank written in Markdown (.md), extracts all questions,
metadata, options, educational objectives, high-yield notes, and clinical explanations,
and automatically builds the complete final/ package:

1. <subject>_all.csv (Consolidated CSV with Educational_Objective)
2. <subject>_all.json (TealMED schema JSON)
3. <subject>_all_ai.md (AI prompt markdown)
4. explanations.md & explanations.txt (Clinical explanations)
5. sessions/ folder (<subject>_all_<session>.csv for each session)
6. topics/ folder (<subject>_all_<topic>.csv for each topic)
7. topics_md/ folder (<subject>_all_explained.md + <subject>_all_<topic>.md)
8. Updates final/manifest.json automatically
"""

import os
import sys
import re
import csv
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def sanitize_filename(name: str) -> str:
    """Sanitizes text to safe filename preserving Arabic characters."""
    if not name:
        return "غير_محدد"
    clean = re.sub(r'[^\w\u0600-\u06FF]+', '_', str(name).strip())
    clean = clean.strip('._')
    return clean or "عام"


def clean_str(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def parse_markdown_questions(md_text: str):
    """
    Parses questions from a template Markdown file.
    Supports YAML frontmatter or top markdown headers for global subject metadata,
    and supports both Arabic and English section names.
    """
    global_meta = {
        "subject_name": "",
        "subject_slug": "",
        "default_exam_period": "",
        "default_topic": "",
        "default_difficulty": "متوسط",
        "exam_type": "national_board",
        "points": 10,
        "is_free": 1
    }

    # 1. Parse YAML Frontmatter if present
    text = md_text
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if frontmatter_match:
        yaml_content = frontmatter_match.group(1)
        text = text[frontmatter_match.end():]
        for line in yaml_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip().strip('"\'')
                if k in ["subject_name", "subject", "المادة", "اسم_المادة", "اسم المادة"]:
                    global_meta["subject_name"] = v
                elif k in ["subject_slug", "slug", "prefix", "المعرف", "كود_المادة"]:
                    global_meta["subject_slug"] = v.lower()
                elif k in ["default_exam_period", "exam_period", "exam_date", "الدورة", "دورة"]:
                    global_meta["default_exam_period"] = v
                elif k in ["default_topic", "topic", "الموضوع", "الفصل"]:
                    global_meta["default_topic"] = v
                elif k in ["default_difficulty", "difficulty", "الصعوبة"]:
                    global_meta["default_difficulty"] = v
                elif k in ["exam_type", "نوع_الامتحان"]:
                    global_meta["exam_type"] = v

    # Also parse top markdown metadata before the first question header
    # e.g.: * **المادة:** الغدية
    first_q_pos = re.search(r'(?m)^(?:###?\s*(?:Question|السؤال|\d+)|#\d{2,4}\b)', text)
    if first_q_pos:
        top_header = text[:first_q_pos.start()]
    else:
        top_header = text[:500]

    for line in top_header.splitlines():
        line = line.strip()
        m = re.match(r'^(?:\*\s*)?(?:\*\*|\#\#)?\s*([^:*#]+?)\s*(?:\*\*)?\s*:\s*(.*)$', line)
        if m:
            key_raw = m.group(1).strip().lower()
            val_raw = m.group(2).strip().strip('"\'*#')
            if any(x in key_raw for x in ["subject_name", "اسم المادة", "المادة"]) and not global_meta["subject_name"]:
                global_meta["subject_name"] = val_raw
            elif any(x in key_raw for x in ["subject_slug", "slug", "prefix", "المعرف", "الكود"]) and not global_meta["subject_slug"]:
                global_meta["subject_slug"] = val_raw.lower()
            elif any(x in key_raw for x in ["default_exam_period", "دورة الامتحان", "الدورة"]) and not global_meta["default_exam_period"]:
                global_meta["default_exam_period"] = val_raw
            elif any(x in key_raw for x in ["default_topic", "الموضوع الافتراضي", "الموضوع"]) and not global_meta["default_topic"]:
                global_meta["default_topic"] = val_raw
            elif any(x in key_raw for x in ["difficulty", "الصعوبة"]) and global_meta["default_difficulty"] == "متوسط":
                global_meta["default_difficulty"] = val_raw

    # Split into raw question blocks
    # Possible split delimiters:
    # '### Question', '### السؤال', '## Question', '## السؤال', '#001 [id]', or '---'
    # Best practice: split by '(?m)^(?=###?\s*(?:Question|السؤال\b|\d+\b)|#\d{2,4}\s*\[)'
    question_split_regex = re.compile(
        r'(?m)^(?=###?\s*(?:Question|السؤال\b|\d+\b)|#\d{2,4}\s*\[)',
        re.IGNORECASE
    )
    raw_blocks = question_split_regex.split(text)

    # If only 1 block or split didn't find headers, try splitting by '---'
    if len(raw_blocks) <= 1:
        raw_blocks = re.split(r'(?m)^---\s*$', text)

    questions = []

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        # Check if block actually contains a question
        # Must have options (e.g. A) or a Question / Title line
        if not re.search(r'(?m)^(?:\*\s*)?[A-Fa-f][\)\.\-:]\s+', block) and not re.search(r'(?:السؤال|Question|title)\s*[:：]', block, re.IGNORECASE):
            continue

        q_data = parse_single_question_block(block, global_meta)
        if q_data and q_data.get("title"):
            questions.append(q_data)

    return global_meta, questions


def parse_single_question_block(block: str, global_meta: dict) -> dict:
    lines = block.splitlines()

    title = ""
    topic_name = global_meta.get("default_topic", "")
    exam_period = global_meta.get("default_exam_period", "")
    difficulty = global_meta.get("default_difficulty", "متوسط")
    exam_type = global_meta.get("exam_type", "national_board")
    correct_option = ""
    explicit_id = ""

    options_dict = {}
    educational_objective = ""
    high_yield_note = ""
    explanation_lines = []

    # State tracking
    current_section = None  # None, 'options', 'edu', 'hy', 'explanation'

    option_regex = re.compile(r'^(?:\*\s*|-\s*)?([A-Fa-f])[\)\.\-:]\s*(.+)$')

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            if current_section == "explanation":
                explanation_lines.append("")
            elif current_section == "note":
                # The note is the last element in explanation; a blank line marks its end
                current_section = "ignore"
            continue

        # Stop section on divider
        if line_clean.startswith("---") or line_clean.startswith("==="):
            current_section = None
            continue

        # Check for section header via colon split
        parts = re.split(r'[:：]', line_clean, 1)
        tag_clean = re.sub(r'[*#_`]', '', parts[0]).strip().lower()
        inline_val = ""
        if len(parts) > 1:
            val_clean = re.sub(r'[*#_`]', '', parts[1]).strip()
            if val_clean:
                inline_val = parts[1].strip().strip('*_`')

        # 1. Educational Objective Header
        if any(tag_clean == x for x in ["educational objective", "الهدف من السؤال", "الهدف التعليمي", "الهدف"]):
            current_section = "edu"
            if inline_val:
                educational_objective = inline_val
            continue

        # 2. High Yield Note Header
        if any(tag_clean == x for x in ["high yield note", "نقطة عالية الأهمية", "ملاحظة عالية الأهمية", "الفكرة من السؤال", "الفكرة"]):
            current_section = "hy"
            if inline_val:
                high_yield_note = inline_val
            continue

        # 3. Explanation Header
        if any(tag_clean == x for x in ["explanation", "التعليل السريري", "التعليل", "الشرح"]):
            current_section = "explanation"
            if inline_val:
                explanation_lines.append(inline_val)
            continue

        # 4. Options Section Header
        if any(tag_clean == x for x in ["options", "الخيارات", "بدائل الإجابة"]):
            current_section = "options"
            continue

        # Check Option line: A) ... (Only if not already in explanation section)
        opt_match = option_regex.match(line_clean)
        if opt_match and current_section not in ["explanation", "note", "ignore"]:
            current_section = "options"
            letter = opt_match.group(1).upper()
            opt_text = opt_match.group(2).strip()

            # Check if option is marked correct: (الصحيح) or (صحيح) or [x] or * (Correct)
            if re.search(r'(?:\(الصحيح\)|\(صحيح\)|\(correct\)|\*correct\*|\[x\])', opt_text, re.IGNORECASE):
                correct_option = letter
                opt_text = re.sub(r'\s*(?:\(الصحيح\)|\(صحيح\)|\(correct\)|\*correct\*|\[x\])\s*', '', opt_text, flags=re.IGNORECASE).strip()

            options_dict[letter] = opt_text
            continue

        # In Explanation or Clinical Note section
        if current_section in ["explanation", "note"]:
            norm_tag = re.sub(r'[*#_`]', '', line_clean).strip().lower()

            # Check unwanted stop tags (الاستناد, ملاحظة نصية, ملاحظة علمية, مرجع)
            if any(norm_tag.startswith(x) for x in ["الاستناد", "استناد", "ملاحظة نصية", "ملاحظة علمية", "مرجع", "المرجع"]) or line_clean.startswith("[المرجع") or line_clean.startswith("[مصدر") or line_clean.startswith("[نص السؤال"):
                current_section = "ignore"
                continue

            # Check if this line is clinical note: **ملاحظة:** or ملاحظة:
            is_note_header = bool(re.match(r'^(?:\*\s*|-\s*)?\*\*ملاحظة\s*:\*\*', line_clean)) or (norm_tag.startswith("ملاحظة:") and not any(norm_tag.startswith(x) for x in ["ملاحظة نصية", "ملاحظة علمية"]))

            if is_note_header:
                explanation_lines.append(line)
                current_section = "note"
                continue

            if current_section == "note":
                # If already captured the note and another bold tag/section or link starts, stop capturing
                if re.match(r'^(?:\*\s*|-\s*)?\*\*[^*]+\*\*[:：]', line_clean) or line_clean.startswith("["):
                    current_section = "ignore"
                    continue
                explanation_lines.append(line)
                continue

            # General explanation line
            explanation_lines.append(line)
            continue

        if current_section == "ignore":
            continue

        # In Educational Objective section
        if current_section == "edu":
            val_line = line_clean.strip('*_`')
            if val_line:
                if educational_objective:
                    educational_objective += " " + val_line
                else:
                    educational_objective = val_line
            continue

        # In High Yield Note section
        if current_section == "hy":
            val_line = line_clean.strip('*_`')
            if val_line:
                if high_yield_note:
                    high_yield_note += " " + val_line
                else:
                    high_yield_note = val_line
            continue

        # Header metadata parsing
        # Check ID e.g. #001 [q_endo_01] (مقدمة وفحص الغدد الصم)
        id_m = re.search(r'\[([a-zA-Z0-9_-]+)\]', line_clean)
        if id_m:
            explicit_id = id_m.group(1)

        paren_topic = re.search(r'\(([\u0600-\u06FF\w\s-]+)\)', line_clean)
        if paren_topic and not topic_name:
            topic_name = paren_topic.group(1).strip()

        # Key-Value match
        kv_m = re.match(r'^(?:\*\s*|-\s*)?(?:\*\*|\#\#)?\s*([^:*#]+?)\s*(?:\*\*)?\s*[:：]\s*(.*)$', line_clean)
        if kv_m:
            k = kv_m.group(1).strip().lower()
            v = kv_m.group(2).strip().strip('*_`')

            if any(x in k for x in ["title", "question", "السؤال", "نص السؤال"]):
                title = v
            elif any(x in k for x in ["topic", "الموضوع", "الفصل"]):
                topic_name = v
            elif any(x in k for x in ["exam_period", "exam_date", "الدورة", "دورة الامتحان"]):
                exam_period = v
            elif any(x in k for x in ["correct_option", "الجواب", "الجواب الصحيح", "correct_answer"]):
                ans_letter_m = re.search(r'([A-Fa-f])\b', v)
                if ans_letter_m:
                    correct_option = ans_letter_m.group(1).upper()
            elif any(x in k for x in ["difficulty", "الصعوبة"]):
                difficulty = v
            elif any(x in k for x in ["exam_type", "نوع الامتحان"]):
                exam_type = v
            elif any(x in k for x in ["educational_objective", "الهدف من السؤال", "الهدف التعليمي"]):
                educational_objective = v
            elif any(x in k for x in ["high_yield_note", "الفكرة من السؤال", "نقطة عالية الأهمية"]):
                high_yield_note = v
            elif any(x in k for x in ["explanation", "التعليل السريري", "الشرح"]):
                explanation_lines.append(v)
                current_section = "explanation"
            continue

        # If line has no key and title is still empty, and not an option/section
        if not title and not line_clean.startswith("#") and not line_clean.startswith("*"):
            title = line_clean

    explanation = "\n".join(explanation_lines).strip()

    # Default correct option if not specified
    if not correct_option:
        correct_option = "A"

    return {
        "explicit_id": explicit_id,
        "title": title,
        "topic_name": topic_name or global_meta.get("default_topic", "عام"),
        "exam_period": exam_period or global_meta.get("default_exam_period", "غير محدد"),
        "difficulty": difficulty,
        "exam_type": exam_type,
        "correct_option": correct_option,
        "options_dict": options_dict,
        "educational_objective": educational_objective.strip(),
        "high_yield_note": high_yield_note.strip(),
        "explanation": explanation
    }


def build_subject_package(
    md_file_path: Path,
    output_final_dir: Path = None,
    subject_slug_override: str = None,
    subject_name_override: str = None
):
    """
    Main pipeline function that parses Markdown and builds the full final package.
    """
    md_file_path = Path(md_file_path).resolve()
    if not md_file_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_file_path}")

    # Read markdown
    with open(md_file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    global_meta, questions_raw = parse_markdown_questions(content)

    if not questions_raw:
        raise ValueError(f"No questions could be parsed from: {md_file_path.name}")

    # Subject Slug & Name resolution
    slug = subject_slug_override or global_meta.get("subject_slug")
    if not slug:
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', md_file_path.stem.lower()).strip('_')
        # Remove suffixes like _questions, _all, etc.
        slug = re.sub(r'_(?:questions|bank|all|template|master)$', '', slug)
        if not slug:
            slug = "subject"

    subject_name = subject_name_override or global_meta.get("subject_name") or slug

    print(f"\n[+] Parsed Subject: '{subject_name}' (slug: '{slug}')")
    print(f"[+] Total questions found: {len(questions_raw)}")

    # Target folder in final/
    if output_final_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
        target_subject_dir = base_dir / "final" / slug
    else:
        target_subject_dir = Path(output_final_dir) / slug

    target_subject_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{slug}_all"

    # Process questions into standard TealMED JSON and CSV formats
    json_items = []
    csv_rows = []
    ai_md_lines = []
    explanations_md_lines = []
    explained_master_lines = []

    pad_width = 3 if len(questions_raw) >= 100 else 2

    for idx, q in enumerate(questions_raw, start=1):
        num_str = f"#{idx:0{pad_width}d}"
        q_id = q.get("explicit_id") or f"q_{slug}_{idx:0{pad_width}d}"

        title = clean_str(q["title"])
        topic = clean_str(q["topic_name"])
        exam_p = clean_str(q["exam_period"])
        diff = clean_str(q["difficulty"])
        ex_type = clean_str(q["exam_type"])
        corr_letter = clean_str(q["correct_option"]).upper() or "A"
        edu_obj = clean_str(q["educational_objective"])
        hy_note = clean_str(q["high_yield_note"])
        expl = clean_str(q["explanation"])

        opts_dict = q["options_dict"]
        # Ensure letters A, B, C, D at minimum if available
        sorted_letters = sorted(opts_dict.keys())
        if not sorted_letters:
            # Fallback if options were not explicitly lettered
            sorted_letters = ["A", "B", "C", "D"]
            opts_dict = {l: f"خيار {l}" for l in sorted_letters}

        # Build options JSON array
        json_options = []
        for l in sorted_letters:
            is_c = (l == corr_letter)
            json_options.append({
                "letter": l,
                "text": clean_str(opts_dict[l]),
                "is_correct": is_c
            })

        # Correct answer and wrong answers for CSV
        corr_answer_text = clean_str(opts_dict.get(corr_letter, ""))
        wrong_answers = [clean_str(opts_dict[l]) for l in sorted_letters if l != corr_letter]

        # 1. JSON item
        json_item = {
            "id": q_id,
            "subject_name": subject_name,
            "topic_name": topic,
            "title": title,
            "difficulty": diff,
            "exam_type": ex_type,
            "exam_period": exam_p,
            "points": global_meta.get("points", 10),
            "is_free": global_meta.get("is_free", 1),
            "correct_option": corr_letter,
            "vignette": None,
            "attending_clue": None,
            "educational_objective": edu_obj,
            "high_yield_note": hy_note,
            "explanation": expl,
            "options": json_options,
            "original_id": q_id
        }
        json_items.append(json_item)

        # 2. CSV row
        csv_row = {
            "Question_ID": q_id,
            "Medical_Subject": subject_name,
            "Exam_Date": exam_p,
            "Chapter_or_Section": topic,
            "Question_Text": title,
            "Explanation": expl,
            "High_Yield_Note": hy_note,
            "Educational_Objective": edu_obj,
            "Correct_Answer": corr_answer_text,
            "Wrong_Answer_1": wrong_answers[0] if len(wrong_answers) > 0 else "",
            "Wrong_Answer_2": wrong_answers[1] if len(wrong_answers) > 1 else "",
            "Wrong_Answer_3": wrong_answers[2] if len(wrong_answers) > 2 else "",
            "Wrong_Answer_4": wrong_answers[3] if len(wrong_answers) > 3 else "",
            "Wrong_Answer_5": wrong_answers[4] if len(wrong_answers) > 4 else ""
        }
        csv_rows.append(csv_row)

        # 3. AI prompt markdown (<slug>_all_ai.md)
        ai_block = [
            f"{num_str} [{q_id}] ({topic})",
            f"السؤال: {title}",
            f"الجواب: {corr_letter}"
        ]
        for l in sorted_letters:
            txt = clean_str(opts_dict[l])
            mark = " (الصحيح)" if l == corr_letter else ""
            ai_block.append(f"{l}) {txt}{mark}")
        ai_block.append("---")
        ai_md_lines.append("\n".join(ai_block))

        # 4. Explanations markdown (explanations.md)
        exp_block = [
            f"{num_str}",
            "EDUCATIONAL OBJECTIVE:",
            edu_obj or "غير محدد",
            "",
            "HIGH YIELD NOTE:",
            hy_note or "غير محدد",
            "",
            "EXPLANATION:",
            expl or "غير محدد",
            "",
            "---"
        ]
        explanations_md_lines.append("\n".join(exp_block))

        # 5. Combined Explained question (for topics_md)
        comb_block = [
            f"{num_str} [{q_id}] ({topic})",
            f"السؤال: {title}",
            f"الجواب: {corr_letter}"
        ]
        for l in sorted_letters:
            txt = clean_str(opts_dict[l])
            mark = " (الصحيح)" if l == corr_letter else ""
            comb_block.append(f"{l}) {txt}{mark}")
        comb_block.extend([
            "",
            "EDUCATIONAL OBJECTIVE:",
            edu_obj or "غير محدد",
            "",
            "HIGH YIELD NOTE:",
            hy_note or "غير محدد",
            "",
            "EXPLANATION:",
            expl or "غير محدد",
            "---"
        ])
        explained_master_lines.append("\n".join(comb_block))

    # Timestamped backup of existing master files before rebuilding
    backup_dir = target_subject_dir / ".backup"
    existing_master = target_subject_dir / f"{stem}.json"
    if existing_master.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        for fn in [f"{stem}.json", f"{stem}.csv", f"{stem}_ai.md", f"{stem}.html", "explanations.md", "explanations.txt"]:
            src = target_subject_dir / fn
            if src.exists():
                try:
                    shutil.copy2(src, backup_dir / f"{src.stem}_{ts}{src.suffix}")
                except Exception:
                    pass

    # --- Write Master Files ---
    # A. <slug>_all.json
    master_json_path = target_subject_dir / f"{stem}.json"
    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(json_items, f, ensure_ascii=False, indent=2)
    print(f" [✓] Created JSON: {master_json_path.name}")

    # B. <slug>_all.csv
    csv_fieldnames = [
        "Question_ID",
        "Medical_Subject",
        "Exam_Date",
        "Chapter_or_Section",
        "Question_Text",
        "Explanation",
        "High_Yield_Note",
        "Educational_Objective",
        "Correct_Answer",
        "Wrong_Answer_1",
        "Wrong_Answer_2",
        "Wrong_Answer_3",
        "Wrong_Answer_4",
        "Wrong_Answer_5"
    ]
    master_csv_path = target_subject_dir / f"{stem}.csv"
    with open(master_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f" [✓] Created CSV:  {master_csv_path.name}")

    # C. <slug>_all_ai.md
    ai_md_path = target_subject_dir / f"{stem}_ai.md"
    with open(ai_md_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(ai_md_lines) + "\n")
    print(f" [✓] Created AI Prompt: {ai_md_path.name}")

    # D. explanations.md & explanations.txt
    exp_md_path = target_subject_dir / "explanations.md"
    exp_txt_path = target_subject_dir / "explanations.txt"
    exp_content = "\n\n".join(explanations_md_lines) + "\n"
    with open(exp_md_path, "w", encoding="utf-8") as f:
        f.write(exp_content)
    with open(exp_txt_path, "w", encoding="utf-8") as f:
        f.write(exp_content)
    print(f" [✓] Created Explanations: explanations.md & explanations.txt")

    # --- Write topics/ CSV files ---
    topics_dir = target_subject_dir / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)
    # Clear existing topic files (html and csv) so stale files from previous builds don't linger
    for old_f in list(topics_dir.glob("*.html")) + list(topics_dir.glob("*.csv")):
        try:
            old_f.unlink()
        except Exception:
            pass

    topics_dict = {}
    for r in csv_rows:
        top = clean_str(r.get("Chapter_or_Section")) or "عام"
        topics_dict.setdefault(top, []).append(r)

    distinct_topics = sorted(list(topics_dict.keys()))
    for top_name, top_rows in topics_dict.items():
        clean_top = sanitize_filename(top_name)
        top_csv_file = topics_dir / f"{stem}_{clean_top}.csv"
        with open(top_csv_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
            writer.writeheader()
            writer.writerows(top_rows)
    print(f" [✓] Created Topics CSVs: {len(topics_dict)} file(s) in topics/")

    # --- Write sessions/ CSV files ---
    sessions_dir = target_subject_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    for old_f in list(sessions_dir.glob("*.html")) + list(sessions_dir.glob("*.csv")):
        try:
            old_f.unlink()
        except Exception:
            pass

    sessions_dict = {}
    for r in csv_rows:
        sess = clean_str(r.get("Exam_Date")) or "غير_محدد"
        sessions_dict.setdefault(sess, []).append(r)

    for sess_name, sess_rows in sessions_dict.items():
        clean_sess = sanitize_filename(sess_name)
        sess_csv_file = sessions_dir / f"{stem}_{clean_sess}.csv"
        with open(sess_csv_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
            writer.writeheader()
            writer.writerows(sess_rows)
    print(f" [✓] Created Sessions CSVs: {len(sessions_dict)} file(s) in sessions/")

    # --- Write topics_md/ files ---
    topics_md_dir = target_subject_dir / "topics_md"
    topics_md_dir.mkdir(parents=True, exist_ok=True)
    for old_f in topics_md_dir.glob("*.md"):
        try:
            old_f.unlink()
        except Exception:
            pass

    # 1. Master explained file: <stem>_explained.md
    master_explained_file = topics_md_dir / f"{stem}_explained.md"
    with open(master_explained_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(explained_master_lines) + "\n")

    # 2. Per-topic explained files: <stem>_<topic>.md
    topic_explained_dict = {}
    for idx, (q, expl_line) in enumerate(zip(questions_raw, explained_master_lines)):
        top = clean_str(q.get("topic_name")) or "عام"
        topic_explained_dict.setdefault(top, []).append(expl_line)

    for top_name, blocks in topic_explained_dict.items():
        clean_top = sanitize_filename(top_name)
        top_md_file = topics_md_dir / f"{stem}_{clean_top}.md"
        with open(top_md_file, "w", encoding="utf-8") as f:
            f.write("\n\n".join(blocks) + "\n")
    print(f" [✓] Created topics_md: {len(topic_explained_dict) + 1} file(s) in topics_md/")

    # Clean legacy years/ folder if present
    legacy_years = target_subject_dir / "years"
    if legacy_years.exists():
        try:
            shutil.rmtree(legacy_years)
        except Exception:
            pass

    # --- Generate Printable Master HTML File (for direct export to PDF) ---
    pdf_maker_dir = base_dir / "pdf_maker"
    if (pdf_maker_dir / "generator.py").exists():
        try:
            sys.path.insert(0, str(pdf_maker_dir))
            import generator
            generator.process_single_file(master_json_path, export_years=False)
            print(f" [✓] Created Printable HTML: {stem}.html (Ready to print as PDF)")
        except Exception as e:
            print(f" [!] Warning generating HTML: {e}")

    # --- Update final/manifest.json ---
    manifest_path = target_subject_dir.parent / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            manifest.setdefault("subjects", {})
            manifest["subjects"][slug] = {
                "subject_name": subject_name,
                "folder": f"final/{slug}",
                "questions_count": len(json_items),
                "files": {
                    "csv": f"{stem}.csv",
                    "json": f"{stem}.json",
                    "ai_prompt": f"{stem}_ai.md",
                    "explained_master": f"topics_md/{stem}_explained.md",
                    "topics_md_folder": "topics_md/"
                },
                "topics": distinct_topics
            }
            manifest["subjects_count"] = len(manifest["subjects"])
            manifest["total_questions"] = sum(s.get("questions_count", 0) for s in manifest["subjects"].values())

            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            print(f" [✓] Updated manifest.json (Total Subjects: {manifest['subjects_count']}, Total Qs: {manifest['total_questions']})")
        except Exception as e:
            print(f" [!] Warning: Could not update manifest.json: {e}")

    print(f"\n=======================================================")
    print(f" [SUCCESS] Subject '{subject_name}' built in '{target_subject_dir}'")
    print(f"=======================================================\n")
    return target_subject_dir


def select_file_gui():
    """Opens native file picker to select an MD file."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(
            title="TealMED - Select Questions Template Markdown File",
            filetypes=[
                ("Markdown Files", "*.md"),
                ("Text Files", "*.txt"),
                ("All Files", "*.*")
            ]
        )
        root.destroy()
        return file_path
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown Template to Complete TealMED final/ Subject Package")
    parser.add_argument("file", nargs="?", default="", help="Path to Markdown template file (e.g. QUESTION_TEMPLATE.md)")
    parser.add_argument("--slug", "-s", default=None, help="Subject slug/prefix (e.g. cardio, endo)")
    parser.add_argument("--name", "-n", default=None, help="Subject Arabic name (e.g. القلبية, الغدية)")
    parser.add_argument("--out", "-o", default=None, help="Output final directory (default: final/)")
    args = parser.parse_args()

    input_file = args.file
    if not input_file:
        input_file = select_file_gui()

    if not input_file or not Path(input_file).exists():
        print("[!] No valid Markdown file provided.")
        sys.exit(1)

    build_subject_package(
        md_file_path=Path(input_file),
        output_final_dir=Path(args.out) if args.out else None,
        subject_slug_override=args.slug,
        subject_name_override=args.name
    )


if __name__ == "__main__":
    main()
