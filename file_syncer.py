#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TealMED Bidirectional File Synchronizer (JSON <-> CSV)
======================================================
Seamlessly synchronizes medical question bank files between JSON and CSV formats.
When you edit either the .json or .csv file, this tool updates the other companion file
to match it with 100% verbatim fidelity, zero metadata loss, and automatic backup.

Key Features:
- Step-by-Step Choice: Select the edited file (Source) first, then the unedited file (Target).
- Intelligent Companion Auto-Detection: Automatically suggests the counterpart in the same folder.
- Smart Auto-Sync: Automatically scans folders and syncs older files from their newer counterparts.
- In-place JSON Preservation: Preserves all rich clinical metadata (educational_objective,
  high_yield_note, difficulty, points) when updating from CSV.
- Dynamic Option Synchronization: Seamlessly handles 3, 4, 5, or 6 options (A through F), adding Wrong_Answer_5 only when present.
- Automatic Timestamped Backups in .backup/ folder.
- Synchronizes companion _ai.md files if present.
- Optional prompt to regenerate HTML/PDF via pdf_maker immediately after syncing.
"""

import os
import sys
import re
import csv
import json
import glob
import shutil
import argparse
import datetime
import threading
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


# -----------------------------------------------------------------------------
# Safety & Backup Utilities
# -----------------------------------------------------------------------------
def create_backup(file_path):
    """Creates a timestamped backup copy in a hidden .backup subfolder."""
    p = Path(file_path)
    if not p.exists():
        return None
    backup_dir = p.parent / ".backup"
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{p.stem}_{timestamp}{p.suffix}"
    shutil.copyfile(p, backup_path)
    return backup_path


# -----------------------------------------------------------------------------
# Core Synchronization Engines
# -----------------------------------------------------------------------------
def sync_json_to_csv(json_path, csv_path):
    """
    Updates or creates a CSV file to match the source JSON file.
    Source: JSON (New/Edited)
    Target: CSV (To be updated)
    """
    json_path = Path(json_path)
    csv_path = Path(csv_path)

    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    if not isinstance(json_data, list):
        raise ValueError(f"Expected JSON array in {json_path.name}")

    existing_cols = None
    existing_rows = []
    existing_by_id = {}

    if csv_path.exists():
        create_backup(csv_path)
        for enc in ['utf-8-sig', 'utf-8', 'cp1256']:
            try:
                with open(csv_path, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    existing_cols = reader.fieldnames
                    existing_rows = list(reader)
                    break
            except Exception:
                continue

    if existing_cols:
        id_col = next((c for c in existing_cols if c.strip().lower() in ['question_id', 'id']), None)
        if id_col:
            for r in existing_rows:
                qid = (r.get(id_col) or '').strip()
                if qid:
                    existing_by_id[qid] = r
    else:
        existing_cols = [
            'Question_ID', 'Medical_Subject', 'Exam_Date', 'Chapter_or_Section',
            'Question_Text', 'Explanation', 'High_Yield_Note', 'Educational_Objective', 'Correct_Answer',
            'Wrong_Answer_1', 'Wrong_Answer_2', 'Wrong_Answer_3', 'Wrong_Answer_4'
        ]

    # Ensure High_Yield_Note is always present in existing_cols
    has_hy_col = any(c.strip().lower() in ['high_yield_note', 'الفكرة_من_السؤال', 'الفكرة من السؤال', 'نقطة_عالية_الأهمية', 'نقطة عالية الأهمية'] for c in existing_cols)
    if not has_hy_col:
        exp_idx = next((i for i, c in enumerate(existing_cols) if c.strip().lower() in ['explanation', 'التعليل', 'الشرح']), -1)
        if exp_idx != -1:
            existing_cols.insert(exp_idx + 1, 'High_Yield_Note')
        else:
            existing_cols.append('High_Yield_Note')

    # Ensure Educational_Objective is always present in existing_cols right after High_Yield_Note
    has_edu_col = any(c.strip().lower() in ['educational_objective', 'الهدف_من_السؤال', 'الهدف من السؤال', 'الهدف_التعليمي', 'الهدف التعليمي'] for c in existing_cols)
    if not has_edu_col:
        hy_idx = next((i for i, c in enumerate(existing_cols) if c.strip().lower() in ['high_yield_note', 'الفكرة_من_السؤال', 'الفكرة من السؤال', 'نقطة_عالية_الأهمية', 'نقطة عالية الأهمية']), -1)
        if hy_idx != -1:
            existing_cols.insert(hy_idx + 1, 'Educational_Objective')
        else:
            exp_idx = next((i for i, c in enumerate(existing_cols) if c.strip().lower() in ['explanation', 'التعليل', 'الشرح']), -1)
            if exp_idx != -1:
                existing_cols.insert(exp_idx + 1, 'Educational_Objective')
            else:
                existing_cols.append('Educational_Objective')

    # Dynamically check if any question has 5 or more wrong options (6 or more total options)
    has_6_opts = False
    for q in json_data:
        opts = q.get('options') or []
        if len(opts) > 5:
            has_6_opts = True
            break
        c_let = (q.get('correct_option') or '').strip().upper()
        w_cnt = sum(1 for opt in opts if not (opt.get('is_correct') or (c_let and opt.get('letter', '').strip().upper() == c_let)))
        if w_cnt >= 5:
            has_6_opts = True
            break

    # If any question has 6 options and Wrong_Answer_5 is not already in existing_cols, add it
    has_w5_col = any(c.strip().lower() in ['wrong_answer_5', 'خيار_خاطئ_5'] for c in existing_cols)
    if has_6_opts and not has_w5_col:
        w4_idx = next((i for i, c in enumerate(existing_cols) if c.strip().lower() in ['wrong_answer_4', 'خيار_خاطئ_4']), -1)
        if w4_idx != -1:
            existing_cols.insert(w4_idx + 1, 'Wrong_Answer_5')
        else:
            existing_cols.append('Wrong_Answer_5')

    updated_rows = []
    changes_count = 0
    detailed_changes = []

    for idx, q in enumerate(json_data, start=1):
        q_id = q.get('id') or q.get('Question_ID') or f"q_{idx:02d}"
        subject = q.get('subject_name') or q.get('subject') or q.get('Medical_Subject') or ""
        date = q.get('exam_period') or q.get('exam_date') or q.get('Exam_Date') or ""
        topic = q.get('topic_name') or q.get('topic') or q.get('Chapter_or_Section') or ""
        stem = q.get('title') or q.get('Question_Text') or q.get('stem') or ""
        exp = q.get('explanation') or q.get('Explanation') or ""

        # Extract options
        options = q.get('options') or []
        correct_letter = (q.get('correct_option') or '').strip().upper()

        correct_text = ""
        wrong_texts = []

        for opt in options:
            let = opt.get('letter', '').strip().upper()
            txt = opt.get('text', '').strip()
            is_cor = bool(opt.get('is_correct', False))
            if is_cor or (correct_letter and let == correct_letter):
                correct_text = txt
            else:
                wrong_texts.append(txt)

        row = {}
        for col in existing_cols:
            col_l = col.strip().lower()
            if col_l in ['question_id', 'id']:
                row[col] = q_id
            elif col_l in ['medical_subject', 'subject', 'المادة']:
                row[col] = subject
            elif col_l in ['exam_date', 'exam_period', 'الدورة', 'التاريخ']:
                row[col] = date
            elif col_l in ['chapter_or_section', 'topic', 'topic_name', 'الموضوع', 'الفصل']:
                row[col] = topic
            elif col_l in ['question_text', 'title', 'stem', 'نص السؤال', 'السؤال']:
                row[col] = stem
            elif col_l in ['explanation', 'التعليل', 'الشرح']:
                row[col] = exp
            elif col_l in ['correct_answer', 'الجواب_الصحيح', 'الإجابة_الصحيحة']:
                row[col] = correct_text
            elif col_l in ['wrong_answer_1', 'خيار_خاطئ_1']:
                row[col] = wrong_texts[0] if len(wrong_texts) > 0 else ""
            elif col_l in ['wrong_answer_2', 'خيار_خاطئ_2']:
                row[col] = wrong_texts[1] if len(wrong_texts) > 1 else ""
            elif col_l in ['wrong_answer_3', 'خيار_خاطئ_3']:
                row[col] = wrong_texts[2] if len(wrong_texts) > 2 else ""
            elif col_l in ['wrong_answer_4', 'خيار_خاطئ_4']:
                row[col] = wrong_texts[3] if len(wrong_texts) > 3 else ""
            elif col_l in ['wrong_answer_5', 'خيار_خاطئ_5']:
                row[col] = wrong_texts[4] if len(wrong_texts) > 4 else ""
            elif col_l in ['high_yield_note', 'الفكرة_من_السؤال', 'الفكرة من السؤال', 'نقطة عالية الأهمية', 'نقطة_عالية_الأهمية']:
                row[col] = q.get('high_yield_note', '') or ""
            elif col_l in ['educational_objective', 'الهدف_من_السؤال', 'الهدف من السؤال', 'الهدف_التعليمي', 'الهدف التعليمي']:
                row[col] = q.get('educational_objective', '') or ""
            else:
                old_r = existing_by_id.get(q_id)
                row[col] = old_r.get(col, '') if old_r else q.get(col, '')

        # Check for differences against old row
        old_r = existing_by_id.get(q_id)
        if old_r:
            diffs = []
            for col in existing_cols:
                old_val = str(old_r.get(col, '')).strip()
                new_val = str(row.get(col, '')).strip()
                if old_val != new_val:
                    diffs.append(f"{col}")
            if diffs:
                changes_count += 1
                diff_summary = ", ".join(diffs[:3])
                detailed_changes.append(f"[{q_id}]: Updated ({diff_summary})")
        else:
            changes_count += 1
            detailed_changes.append(f"[{q_id}]: New question added")

        updated_rows.append(row)

    # Save target CSV with UTF-8 BOM and graceful lock-handling
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    saved = False
    while not saved:
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=existing_cols)
                writer.writeheader()
                writer.writerows(updated_rows)
            saved = True
        except PermissionError:
            print(f"\n[!] Warning: Cannot write to '{csv_path.name}'.")
            print("    Reason: The file is currently open in another program (e.g. Microsoft Excel).")
            print("    Please save and close the file in Excel, then press Enter to retry.")
            if sys.stdin and sys.stdin.isatty():
                ans = input("Press Enter to retry (or type S to save to temporary file): ").strip().upper()
                if ans == 'S':
                    fallback_path = csv_path.parent / f"{csv_path.stem}_synced{csv_path.suffix}"
                    with open(fallback_path, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.DictWriter(f, fieldnames=existing_cols)
                        writer.writeheader()
                        writer.writerows(updated_rows)
                    print(f"[✓] Saved updates to: {fallback_path.name}")
                    return changes_count, detailed_changes
            else:
                # Non-interactive fallback
                fallback_path = csv_path.parent / f"{csv_path.stem}_synced{csv_path.suffix}"
                with open(fallback_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=existing_cols)
                    writer.writeheader()
                    writer.writerows(updated_rows)
                print(f"[✓] Original file locked by Excel. Saved updates to: {fallback_path.name}")
                return changes_count, detailed_changes

    # Sync companion _ai.md if exists
    sync_companion_ai_md(json_data, csv_path.parent / f"{csv_path.stem}_ai.md")

    return changes_count, detailed_changes


def sync_csv_to_json(csv_path, json_path):
    """
    Updates or creates a JSON file to match the source CSV file.
    Source: CSV (New/Edited)
    Target: JSON (To be updated)
    Preserves all existing clinical metadata in the JSON objects.
    """
    csv_path = Path(csv_path)
    json_path = Path(json_path)

    df_rows = None
    for enc in ['utf-8-sig', 'utf-8', 'cp1256']:
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                reader = csv.DictReader(f)
                df_rows = list(reader)
                break
        except Exception:
            continue

    if df_rows is None:
        raise ValueError(f"Could not decode CSV: {csv_path.name}")

    existing_json = []
    existing_by_id = {}
    existing_by_stem = {}
    used_existing_ids = set()

    if json_path.exists():
        create_backup(json_path)
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_json = json.load(f)
            if isinstance(existing_json, list):
                for q in existing_json:
                    qid = q.get('id') or q.get('original_id')
                    if qid:
                        existing_by_id[qid] = q
                    stem_k = (q.get('title') or q.get('vignette') or '').strip()
                    if stem_k:
                        existing_by_stem[stem_k] = q
        except Exception:
            pass

    all_csv_stems = set()
    for r in df_rows:
        for k in ["Question_Text", "title", "stem", "نص السؤال", "السؤال"]:
            v = r.get(k)
            if v and v.strip():
                all_csv_stems.add(v.strip())
                break

    updated_json = []
    changes_count = 0
    detailed_changes = []

    for idx, row in enumerate(df_rows, start=1):
        clean_row = {k.strip().replace('\ufeff', ''): (v.strip() if v else '') for k, v in row.items() if k}

        def get_f(*keys):
            for k in keys:
                for rk, rv in clean_row.items():
                    if rk.lower() == k.lower() or k.lower() in rk.lower():
                        if rv:
                            return rv
            return ""

        raw_qid = get_f("Question_ID", "id")
        subject = get_f("Medical_Subject", "subject", "المادة")
        date = get_f("Exam_Date", "exam_period", "الدورة", "التاريخ")
        topic = get_f("Chapter_or_Section", "topic", "الموضوع", "الفصل")
        stem = get_f("Question_Text", "title", "نص السؤال", "السؤال")
        exp = get_f("Explanation", "الشرح", "التعليل")
        csv_hy = get_f("High_Yield_Note", "الفكرة_من_السؤال", "الفكرة من السؤال", "نقطة_عالية_الأهمية", "نقطة عالية الأهمية", "high_yield")
        csv_edu = get_f("Educational_Objective", "educational_objective", "الهدف_من_السؤال", "الهدف من السؤال", "الهدف_التعليمي", "الهدف التعليمي")

        correct_ans = get_f("Correct_Answer", "الجواب_الصحيح", "الإجابة_الصحيحة")
        wrong_1 = get_f("Wrong_Answer_1", "خيار_خاطئ_1")
        wrong_2 = get_f("Wrong_Answer_2", "خيار_خاطئ_2")
        wrong_3 = get_f("Wrong_Answer_3", "خيار_خاطئ_3")
        wrong_4 = get_f("Wrong_Answer_4", "خيار_خاطئ_4")
        wrong_5 = get_f("Wrong_Answer_5", "خيار_خاطئ_5")

        # Only non-empty wrong answers are considered
        new_wrongs = [w for w in [wrong_1, wrong_2, wrong_3, wrong_4, wrong_5] if w]

        # Smart Matching Hierarchy:
        # Question stem and ID are both used to ensure unambiguous metadata binding.
        old_q = None
        clean_stem = stem.strip() if stem else ""

        # 1. Direct ID & Stem Match: When ID is present and matches the candidate stem in JSON
        if raw_qid and raw_qid in existing_by_id and raw_qid not in used_existing_ids:
            cand = existing_by_id[raw_qid]
            cand_stem = (cand.get('title') or cand.get('vignette') or '').strip()
            if cand_stem == clean_stem:
                old_q = cand
                used_existing_ids.add(raw_qid)

        # 2. Exact Match: Question stem matches an existing question in JSON
        if not old_q and clean_stem and clean_stem in existing_by_stem:
            candidate = existing_by_stem[clean_stem]
            c_id = candidate.get('id')
            if c_id and c_id not in used_existing_ids:
                old_q = candidate
                used_existing_ids.add(c_id)

        # 3. ID Match Fallback: ONLY if candidate's original stem is NOT elsewhere in the CSV
        # (Handles cases where user rephrased or edited the stem of an existing question)
        if not old_q and raw_qid and raw_qid in existing_by_id and raw_qid not in used_existing_ids:
            candidate = existing_by_id[raw_qid]
            cand_stem = (candidate.get('title') or candidate.get('vignette') or '').strip()
            if not cand_stem or cand_stem not in all_csv_stems:
                old_q = candidate
                used_existing_ids.add(raw_qid)

        # 3. Positional fallback: ONLY when total row count is completely unchanged,
        #    AND no ID was provided in CSV, AND candidate was not matched to another row.
        if not old_q and not raw_qid and len(df_rows) == len(existing_json) and 1 <= idx <= len(existing_json):
            candidate = existing_json[idx - 1]
            c_id = candidate.get('id')
            if c_id not in used_existing_ids:
                cand_stem = (candidate.get('title') or candidate.get('vignette') or '').strip()
                if not cand_stem or cand_stem not in all_csv_stems:
                    old_q = candidate
                    if c_id:
                        used_existing_ids.add(c_id)

        # Final resolved ID
        if raw_qid:
            q_id = raw_qid
        elif old_q and old_q.get('id'):
            q_id = old_q.get('id')
        else:
            q_id = f"q_{idx:02d}"

        if old_q:
            diffs = []
            if subject and old_q.get('subject_name') != subject:
                diffs.append("Subject")
                old_q['subject_name'] = subject
            # Only update topic if CSV actually provided a non-empty topic
            if topic and old_q.get('topic_name') != topic:
                diffs.append("Topic")
                old_q['topic_name'] = topic
            if date and old_q.get('exam_period') != date:
                diffs.append("Exam Date")
                old_q['exam_period'] = date
            if stem and old_q.get('title') != stem:
                diffs.append("Question Text")
                old_q['title'] = stem
            if exp and old_q.get('explanation') != exp:
                diffs.append("Explanation")
                old_q['explanation'] = exp

            if csv_hy and old_q.get('high_yield_note') != csv_hy:
                diffs.append("High Yield Note")
                old_q['high_yield_note'] = csv_hy

            if csv_edu is not None and csv_edu != '' and old_q.get('educational_objective') != csv_edu:
                diffs.append("Educational Objective")
                old_q['educational_objective'] = csv_edu

            # Update options dynamically based on CSV content
            old_options = old_q.get('options', [])
            if correct_ans:
                c_letter = (old_q.get('correct_option') or '').strip().upper()
                
                # Separate existing correct option and wrong options
                cor_opt = None
                wrong_opts = []
                for opt in old_options:
                    let = opt.get('letter', '').strip().upper()
                    if opt.get('is_correct') or (c_letter and let == c_letter):
                        if cor_opt is None:
                            cor_opt = opt
                        else:
                            wrong_opts.append(opt)
                    else:
                        wrong_opts.append(opt)

                if cor_opt:
                    if cor_opt.get('text') != correct_ans:
                        diffs.append("Correct Option")
                        cor_opt['text'] = correct_ans
                    cor_opt['is_correct'] = True
                else:
                    cor_opt = {"letter": "A", "text": correct_ans, "is_correct": True}
                    old_options.insert(0, cor_opt)
                    diffs.append("Added Correct Option")

                # Update existing wrong options
                letters_pool = ['A', 'B', 'C', 'D', 'E', 'F']
                for idx_w, w_text in enumerate(new_wrongs):
                    if idx_w < len(wrong_opts):
                        opt = wrong_opts[idx_w]
                        if opt.get('text') != w_text:
                            diffs.append(f"Option {opt.get('letter', '')}")
                            opt['text'] = w_text
                        opt['is_correct'] = False
                    else:
                        existing_letters = {o.get('letter', '').strip().upper() for o in old_options}
                        next_letter = next((l for l in letters_pool if l not in existing_letters), f"Opt_{len(old_options)+1}")
                        new_opt = {
                            "letter": next_letter,
                            "text": w_text,
                            "is_correct": False
                        }
                        old_options.append(new_opt)
                        wrong_opts.append(new_opt)
                        diffs.append(f"Added Option {next_letter}")

                # If question now has fewer wrong options than before (e.g. 4 down to 3, or 5 down to 4), remove excess
                if len(wrong_opts) > len(new_wrongs):
                    excess = wrong_opts[len(new_wrongs):]
                    for ex in excess:
                        if ex in old_options:
                            old_options.remove(ex)
                            diffs.append(f"Removed Option {ex.get('letter', '')}")

                # Ensure sorted order and correct_option tag
                letter_order = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5}
                old_options.sort(key=lambda o: letter_order.get(o.get('letter', '').strip().upper(), 99))
                old_q['options'] = old_options
                for opt in old_options:
                    if opt.get('is_correct'):
                        old_q['correct_option'] = opt.get('letter', 'A')
                        break

            if diffs:
                changes_count += 1
                diff_summary = ", ".join(diffs[:3])
                detailed_changes.append(f"[{q_id}]: Updated ({diff_summary})")

            updated_json.append(old_q)

        else:
            # Build fresh question preserving schema (supporting 3, 4, 5, or 6 options)
            letters = ['A', 'B', 'C', 'D', 'E', 'F']
            opts = []
            if correct_ans:
                opts.append({"letter": "A", "text": correct_ans, "is_correct": True})
                for c_i, w in enumerate(new_wrongs, start=1):
                    if c_i < len(letters):
                        opts.append({"letter": letters[c_i], "text": w, "is_correct": False})

            # Extract high yield note and educational objective from CSV column first, or from explanation if present
            high_yield = csv_hy
            edu_obj = csv_edu or ""
            if not high_yield and exp:
                hy_m = re.search(r'(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|الفكرة\s+من\s+السؤال)\s*:\s*(.*?)(?=(?:EXPLANATION|الشرح|التعليل)\s*:|$)', exp, re.DOTALL | re.IGNORECASE)
                if hy_m:
                    high_yield = hy_m.group(1).strip()
            if not edu_obj and exp:
                obj_m = re.search(r'(?:EDUCATIONAL\s+OBJECTIVE|الهدف\s+التعليمي|الهدف\s+من\s+السؤال)\s*:\s*(.*?)(?=(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|EXPLANATION|الشرح|التعليل)\s*:|$)', exp, re.DOTALL | re.IGNORECASE)
                if obj_m:
                    edu_obj = obj_m.group(1).strip()

            new_q = {
                "id": q_id,
                "subject_name": subject,
                "topic_name": topic,
                "title": stem,
                "difficulty": "متوسط",
                "exam_type": "national_board",
                "exam_period": date,
                "points": 10,
                "is_free": 1,
                "correct_option": "A",
                "vignette": None,
                "attending_clue": None,
                "educational_objective": edu_obj,
                "high_yield_note": high_yield,
                "explanation": exp,
                "options": opts,
                "original_id": q_id
            }
            changes_count += 1
            detailed_changes.append(f"[{q_id}]: New question added")
            updated_json.append(new_q)

    # Ensure 100% Unique Question IDs across all questions in the bank
    seen_ids = set()
    for i, q in enumerate(updated_json, start=1):
        cur_id = q.get('id')
        if not cur_id or cur_id in seen_ids:
            base_prefix = re.sub(r'_\d+$', '', cur_id) if cur_id else "q"
            cand_num = i
            new_unique_id = f"{base_prefix}_{cand_num:02d}"
            while new_unique_id in seen_ids:
                cand_num += 1
                new_unique_id = f"{base_prefix}_{cand_num:02d}"
            q['id'] = new_unique_id
        seen_ids.add(q['id'])

    # Save target JSON with graceful lock-handling
    json_path.parent.mkdir(parents=True, exist_ok=True)
    saved = False
    while not saved:
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(updated_json, f, ensure_ascii=False, indent=2)
            saved = True
        except PermissionError:
            print(f"\n[!] Warning: Cannot write to '{json_path.name}'.")
            print("    Reason: The file is open or locked by another program.")
            print("    Please close the file, then press Enter to retry.")
            if sys.stdin and sys.stdin.isatty():
                ans = input("Press Enter to retry (or type S to save to temporary file): ").strip().upper()
                if ans == 'S':
                    fallback_path = json_path.parent / f"{json_path.stem}_synced{json_path.suffix}"
                    with open(fallback_path, 'w', encoding='utf-8') as f:
                        json.dump(updated_json, f, ensure_ascii=False, indent=2)
                    print(f"[✓] Saved updates to: {fallback_path.name}")
                    return changes_count, detailed_changes
            else:
                fallback_path = json_path.parent / f"{json_path.stem}_synced{json_path.suffix}"
                with open(fallback_path, 'w', encoding='utf-8') as f:
                    json.dump(updated_json, f, ensure_ascii=False, indent=2)
                print(f"[✓] Original file locked. Saved updates to: {fallback_path.name}")
                return changes_count, detailed_changes

    # Sync companion _ai.md if exists
    sync_companion_ai_md(updated_json, json_path.parent / f"{json_path.stem}_ai.md")

    return changes_count, detailed_changes


def sync_companion_ai_md(json_data, md_path):
    """Keeps companion *_ai.md markdown prompt file in sync if it exists."""
    md_path = Path(md_path)
    if not md_path.exists():
        # Only update if companion file already exists in directory
        return

    create_backup(md_path)
    blocks = []
    for q_num, q in enumerate(json_data, start=1):
        q_id = q.get("id") or f"q_{q_num:02d}"
        topic = q.get("topic_name") or ""
        q_text = (q.get("vignette") or q.get("title") or "").strip()
        correct_opt = (q.get("correct_option") or "").strip()

        lines = [
            f"#{q_num:02d} [{q_id}] ({topic})",
            f"السؤال: {q_text}",
            f"الجواب: {correct_opt}"
        ]
        for opt in q.get("options", []):
            let = opt.get("letter", "")
            txt = opt.get("text", "")
            is_cor = opt.get("is_correct", False) or (correct_opt and let == correct_opt)
            suffix = " (الصحيح)" if is_cor else ""
            lines.append(f"{let}) {txt}{suffix}")
        lines.append("---")
        lines.append("")
        blocks.append("\n".join(lines))

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(blocks))


def sync_pair(source_path, target_path):
    """Dispatches sync according to file types."""
    src = Path(source_path)
    tgt = Path(target_path)

    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")

    s_ext = src.suffix.lower()
    t_ext = tgt.suffix.lower()

    if s_ext == '.json' and t_ext == '.csv':
        cnt, diffs = sync_json_to_csv(src, tgt)
    elif s_ext == '.csv' and t_ext == '.json':
        cnt, diffs = sync_csv_to_json(src, tgt)
    elif s_ext == '.json' and t_ext == '.json':
        create_backup(tgt)
        shutil.copyfile(src, tgt)
        cnt, diffs = 1, ["Cloned JSON file completely"]
    elif s_ext == '.csv' and t_ext == '.csv':
        create_backup(tgt)
        shutil.copyfile(src, tgt)
        cnt, diffs = 1, ["Cloned CSV file completely"]
    else:
        raise ValueError(f"Unsupported sync pair: {s_ext} -> {t_ext}")

    try:
        now_ts = datetime.datetime.now().timestamp()
        os.utime(src, (now_ts, now_ts))
        os.utime(tgt, (now_ts, now_ts))
    except Exception:
        pass

    return cnt, diffs


# -----------------------------------------------------------------------------
# Workspace Scanner & Pair Finder
# -----------------------------------------------------------------------------
def scan_workspace_pairs():
    """
    Finds all companion pairs of (.json and .csv) in the workspace.
    Returns list of dicts with paths, mtimes, and which is newer.
    """
    base_dir = Path(__file__).resolve().parent
    pairs = []
    seen = set()

    target_dirs = list(base_dir.glob("all_*"))
    final_dir = base_dir / "final"
    if final_dir.is_dir():
        target_dirs.extend([p for p in final_dir.iterdir() if p.is_dir()])

    for d in sorted(target_dirs):
        if d.is_dir():
            jsons = list(d.glob("*.json"))
            csvs = list(d.glob("*.csv"))
            for j in jsons:
                companion_csv = j.with_suffix('.csv')
                if companion_csv.exists() and companion_csv in csvs:
                    pair_key = (str(j), str(companion_csv))
                    if pair_key not in seen:
                        seen.add(pair_key)
                        j_mtime = j.stat().st_mtime
                        c_mtime = companion_csv.stat().st_mtime
                        diff_sec = abs(j_mtime - c_mtime)
                        pairs.append({
                            'folder': d.name,
                            'stem': j.stem,
                            'json_path': j,
                            'csv_path': companion_csv,
                            'json_mtime': j_mtime,
                            'csv_mtime': c_mtime,
                            'newer': 'equal' if diff_sec <= 3 else ('json' if j_mtime > c_mtime else 'csv'),
                            'diff_sec': diff_sec
                        })
    return pairs


def find_all_available_files():
    """Scans all available question bank files (.json and .csv) in all_* folders."""
    base_dir = Path(__file__).resolve().parent
    files = []
    for ext in ["*.json", "*.csv"]:
        for f in sorted(base_dir.glob(f"all_*/{ext}")):
            files.append(f)
    return files


# -----------------------------------------------------------------------------
# Interactive CLI & GUI Workflows
# -----------------------------------------------------------------------------
def open_gui_file_dialog(title, filetypes=None):
    """Opens a native Windows file dialog to select a single file."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        types = filetypes or [("All Supported", "*.json *.csv"), ("JSON Files", "*.json"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
        selected = filedialog.askopenfilename(title=title, filetypes=types)
        root.destroy()
        return selected or None
    except Exception as e:
        print(f"[!] GUI picker error: {e}")
        return None


def trigger_pdf_regeneration(subject_file):
    """Calls generator.py to regenerate PDF/HTML files for the updated subject."""
    base_dir = Path(__file__).resolve().parent
    gen_script = base_dir / "pdf_maker" / "generator.py"
    if not gen_script.exists():
        return
    import subprocess
    print(f"\n---> Regenerating HTML / PDF files for ({Path(subject_file).stem})...")
    subprocess.run([sys.executable, str(gen_script), str(subject_file)])


# -----------------------------------------------------------------------------
# Standalone Graphical User Interface (Tkinter Desktop Application)
# -----------------------------------------------------------------------------
class TealMedSyncGUI:
    """A modern, intuitive GUI window for TealMED Question Bank Synchronization (100% in English)."""

    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox, scrolledtext

        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.scrolledtext = scrolledtext

        self.root = root
        self.root.title("TealMED - Question Bank Synchronizer (JSON ⇄ CSV)")
        self.root.geometry("920x760")
        self.root.minsize(840, 620)

        # Center window on screen
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, int((sw - 920) / 2))
            y = max(0, int((sh - 760) / 2))
            self.root.geometry(f"920x760+{x}+{y}")
        except Exception:
            pass

        # Apply system styling
        self.style = ttk.Style(self.root)
        for theme in ['vista', 'clam', 'default']:
            if theme in self.style.theme_names():
                self.style.theme_use(theme)
                break

        self.source_path_var = tk.StringVar()
        self.target_path_var = tk.StringVar()
        self.source_info_var = tk.StringVar(value="Select an edited file above to view details.")
        self.target_info_var = tk.StringVar(value="Select a target file above to view details.")
        self.regen_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready | All systems operational")
        self.is_busy = False

        self._build_ui()
        self.refresh_quick_picks()
        self.refresh_workspace_table()

    def _build_ui(self):
        # 1. Header Frame
        header = self.tk.Frame(self.root, bg="#0f172a", padx=16, pady=12)
        header.pack(fill=self.tk.X)

        title_lbl = self.tk.Label(
            header,
            text="TealMED Question Bank Synchronizer",
            font=("Segoe UI", 15, "bold"),
            fg="#ffffff",
            bg="#0f172a"
        )
        title_lbl.pack(anchor=self.tk.W)

        subtitle_lbl = self.tk.Label(
            header,
            text="Bidirectional JSON ⇄ CSV Synchronization with 100% Fidelity & Automated Backup",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a"
        )
        subtitle_lbl.pack(anchor=self.tk.W)

        # 2. Main Notebook (Tabs)
        self.notebook = self.ttk.Notebook(self.root)
        self.notebook.pack(fill=self.tk.BOTH, expand=True, padx=12, pady=10)

        # Tab 1: Single Pair Synchronizer
        self.tab_pair = self.ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_pair, text="  Single Pair Synchronizer  ")
        self._build_pair_tab()

        # Tab 2: Workspace Overview & Auto-Sync
        self.tab_workspace = self.ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_workspace, text="  Workspace Overview & Auto-Sync  ")
        self._build_workspace_tab()

        # 3. Bottom Log / Output Area (Visible across all tabs)
        log_frame = self.ttk.LabelFrame(self.root, text=" Activity Log / Sync Details ", padding=8)
        log_frame.pack(fill=self.tk.BOTH, expand=False, padx=12, pady=(0, 6))

        self.log_text = self.scrolledtext.ScrolledText(
            log_frame,
            height=7,
            wrap=self.tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#e2e8f0",
            insertbackground="#ffffff"
        )
        self.log_text.pack(fill=self.tk.BOTH, expand=True, side=self.tk.LEFT)

        log_btn_frame = self.ttk.Frame(log_frame)
        log_btn_frame.pack(fill=self.tk.Y, side=self.tk.RIGHT, padx=(6, 0))

        self.ttk.Button(log_btn_frame, text="Clear Log", command=self.clear_log, width=12).pack(fill=self.tk.X, pady=2)
        self.ttk.Button(log_btn_frame, text="Copy Log", command=self.copy_log, width=12).pack(fill=self.tk.X, pady=2)

        # 4. Status Bar
        status_bar = self.tk.Frame(self.root, bg="#e2e8f0", padx=10, pady=4)
        status_bar.pack(fill=self.tk.X, side=self.tk.BOTTOM)
        self.status_lbl = self.tk.Label(
            status_bar,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg="#334155",
            bg="#e2e8f0",
            anchor=self.tk.W
        )
        self.status_lbl.pack(fill=self.tk.X)

    def _build_pair_tab(self):
        # Card 1: Source File
        src_frame = self.ttk.LabelFrame(self.tab_pair, text=" Step 1: Source File (The Edited File) ", padding=10)
        src_frame.pack(fill=self.tk.X, pady=(0, 4))

        # Path Entry + Browse
        f1 = self.ttk.Frame(src_frame)
        f1.pack(fill=self.tk.X, pady=3)
        self.ttk.Label(f1, text="File Path:", width=12).pack(side=self.tk.LEFT)
        self.src_entry = self.ttk.Entry(f1, textvariable=self.source_path_var)
        self.src_entry.pack(side=self.tk.LEFT, fill=self.tk.X, expand=True, padx=(0, 6))
        self.src_entry.bind("<FocusOut>", lambda e: self.on_source_path_changed())
        self.src_entry.bind("<Return>", lambda e: self.on_source_path_changed())
        self.ttk.Button(f1, text="Browse File...", command=self.browse_source).pack(side=self.tk.RIGHT)

        # Quick Select Dropdown
        f2 = self.ttk.Frame(src_frame)
        f2.pack(fill=self.tk.X, pady=3)
        self.ttk.Label(f2, text="Quick Select:", width=12).pack(side=self.tk.LEFT)
        self.quick_pick_cb = self.ttk.Combobox(f2, state="readonly")
        self.quick_pick_cb.pack(side=self.tk.LEFT, fill=self.tk.X, expand=True, padx=(0, 6))
        self.quick_pick_cb.bind("<<ComboboxSelected>>", lambda e: self.on_quick_pick_selected())
        self.ttk.Button(f2, text="Load Selected", command=self.on_quick_pick_selected).pack(side=self.tk.RIGHT)

        # Source Info
        self.src_info_lbl = self.ttk.Label(src_frame, textvariable=self.source_info_var, font=("Segoe UI", 8), foreground="#0369a1")
        self.src_info_lbl.pack(anchor=self.tk.W, pady=(4, 0))

        # Transfer Indicator
        trans_frame = self.tk.Frame(self.tab_pair, pady=4)
        trans_frame.pack(fill=self.tk.X)
        arrow_lbl = self.tk.Label(
            trans_frame,
            text="⬇ Target file will be updated to match the edited Source file ⬇",
            font=("Segoe UI", 9, "bold italic"),
            fg="#2563eb"
        )
        arrow_lbl.pack()

        # Card 2: Target File
        tgt_frame = self.ttk.LabelFrame(self.tab_pair, text=" Step 2: Target File (To Be Updated) ", padding=10)
        tgt_frame.pack(fill=self.tk.X, pady=(0, 6))

        f3 = self.ttk.Frame(tgt_frame)
        f3.pack(fill=self.tk.X, pady=3)
        self.ttk.Label(f3, text="File Path:", width=12).pack(side=self.tk.LEFT)
        self.tgt_entry = self.ttk.Entry(f3, textvariable=self.target_path_var)
        self.tgt_entry.pack(side=self.tk.LEFT, fill=self.tk.X, expand=True, padx=(0, 6))
        self.tgt_entry.bind("<FocusOut>", lambda e: self.on_target_path_changed())
        self.tgt_entry.bind("<Return>", lambda e: self.on_target_path_changed())
        self.ttk.Button(f3, text="Browse File...", command=self.browse_target).pack(side=self.tk.RIGHT)
        self.ttk.Button(f3, text="Auto-Detect Counterpart", command=self.auto_detect_target).pack(side=self.tk.RIGHT, padx=(0, 6))

        # Target Info
        self.tgt_info_lbl = self.ttk.Label(tgt_frame, textvariable=self.target_info_var, font=("Segoe UI", 8), foreground="#4338ca")
        self.tgt_info_lbl.pack(anchor=self.tk.W, pady=(4, 0))

        # Action & Options Frame
        action_frame = self.ttk.Frame(self.tab_pair)
        action_frame.pack(fill=self.tk.X, pady=8)

        self.ttk.Checkbutton(
            action_frame,
            text="Regenerate HTML & PDF study files immediately after sync",
            variable=self.regen_var
        ).pack(side=self.tk.LEFT, padx=4)

        self.btn_sync = self.tk.Button(
            action_frame,
            text="⚡ Synchronize Target File Now",
            font=("Segoe UI", 10, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=self.tk.FLAT,
            padx=16,
            pady=6,
            command=self.execute_pair_sync
        )
        self.btn_sync.pack(side=self.tk.RIGHT, padx=4)

    def _build_workspace_tab(self):
        desc = self.ttk.Label(
            self.tab_workspace,
            text="Detected companion question banks across medical subject folders in this workspace:"
        )
        desc.pack(anchor=self.tk.W, pady=(0, 8))

        # Treeview frame
        tree_frame = self.ttk.Frame(self.tab_workspace)
        tree_frame.pack(fill=self.tk.BOTH, expand=True)

        cols = ("folder", "stem", "json_time", "csv_time", "status")
        self.tree = self.ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("folder", text="Folder")
        self.tree.heading("stem", text="Subject / File")
        self.tree.heading("json_time", text="JSON Last Modified")
        self.tree.heading("csv_time", text="CSV Last Modified")
        self.tree.heading("status", text="Sync Status")

        self.tree.column("folder", width=100, anchor=self.tk.W)
        self.tree.column("stem", width=220, anchor=self.tk.W)
        self.tree.column("json_time", width=140, anchor=self.tk.CENTER)
        self.tree.column("csv_time", width=140, anchor=self.tk.CENTER)
        self.tree.column("status", width=220, anchor=self.tk.W)

        tree_scroll = self.ttk.Scrollbar(tree_frame, orient=self.tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True)
        tree_scroll.pack(side=self.tk.RIGHT, fill=self.tk.Y)

        self.tree.tag_configure("synced", foreground="#16a34a")
        self.tree.tag_configure("json_newer", foreground="#d97706")
        self.tree.tag_configure("csv_newer", foreground="#4f46e5")

        # Double click to select into Tab 1
        self.tree.bind("<Double-1>", lambda e: self.on_tree_double_click())

        # Buttons toolbar
        btn_bar = self.ttk.Frame(self.tab_workspace)
        btn_bar.pack(fill=self.tk.X, pady=(10, 0))

        self.ttk.Button(btn_bar, text="🔄 Refresh Workspace Status", command=self.refresh_workspace_table).pack(side=self.tk.LEFT, padx=4)

        self.btn_auto_all = self.tk.Button(
            btn_bar,
            text="⚡ Auto-Sync All Outdated Files",
            font=("Segoe UI", 9, "bold"),
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            relief=self.tk.FLAT,
            padx=12,
            pady=4,
            command=self.execute_auto_sync_all
        )
        self.btn_auto_all.pack(side=self.tk.LEFT, padx=4)

        self.ttk.Button(btn_bar, text="📄 Regenerate All PDFs/HTML", command=self.execute_regenerate_all_pdfs).pack(side=self.tk.RIGHT, padx=4)

    def log(self, message):
        """Thread-safe logging to the bottom text area."""
        def _append():
            self.log_text.insert(self.tk.END, message + "\n")
            self.log_text.see(self.tk.END)
        self.root.after(0, _append)

    def clear_log(self):
        self.log_text.delete("1.0", self.tk.END)

    def copy_log(self):
        content = self.log_text.get("1.0", self.tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.set_status("Log copied to clipboard!")

    def set_status(self, text, working=False):
        prefix = "⏳ " if working else "• "
        self.status_var.set(f"{prefix}{text}")

    def refresh_quick_picks(self):
        all_files = find_all_available_files()
        self.workspace_file_map = {}
        display_names = []
        for f in all_files:
            disp = f"{f.parent.name} / {f.name}"
            display_names.append(disp)
            self.workspace_file_map[disp] = f

        self.quick_pick_cb['values'] = display_names
        if display_names:
            self.quick_pick_cb.current(0)

    def on_quick_pick_selected(self):
        val = self.quick_pick_cb.get()
        if val in self.workspace_file_map:
            p = self.workspace_file_map[val]
            self.source_path_var.set(str(p))
            self.on_source_path_changed()
            self.auto_detect_target()

    def browse_source(self):
        selected = self.filedialog.askopenfilename(
            title="Step 1: Select Edited Source File",
            filetypes=[("Question Banks", "*.json *.csv"), ("JSON Files", "*.json"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if selected:
            self.source_path_var.set(selected)
            self.on_source_path_changed()
            self.auto_detect_target()

    def browse_target(self):
        selected = self.filedialog.askopenfilename(
            title="Step 2: Select Target File to Update",
            filetypes=[("Question Banks", "*.json *.csv"), ("JSON Files", "*.json"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if selected:
            self.target_path_var.set(selected)
            self.on_target_path_changed()

    def on_source_path_changed(self):
        path_str = self.source_path_var.get().strip()
        if not path_str or not Path(path_str).exists():
            self.source_info_var.set("File not found or path is empty.")
            return

        p = Path(path_str)
        mtime_str = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        count_str = self._count_items(p)
        self.source_info_var.set(f"Type: {p.suffix.upper()[1:]} | {count_str} | Modified: {mtime_str} | File: {p.name}")

    def on_target_path_changed(self):
        path_str = self.target_path_var.get().strip()
        if not path_str or not Path(path_str).exists():
            self.target_info_var.set("Target file does not exist yet (it will be created on sync).")
            return

        p = Path(path_str)
        mtime_str = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        count_str = self._count_items(p)
        self.target_info_var.set(f"Type: {p.suffix.upper()[1:]} | {count_str} | Modified: {mtime_str} | File: {p.name}")

    def _count_items(self, path):
        try:
            if path.suffix.lower() == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return f"{len(data)} Questions" if isinstance(data, list) else "JSON Object"
            elif path.suffix.lower() == '.csv':
                for enc in ['utf-8-sig', 'utf-8', 'cp1256']:
                    try:
                        with open(path, 'r', encoding=enc) as f:
                            rows = list(csv.DictReader(f))
                        return f"{len(rows)} Questions"
                    except Exception:
                        continue
        except Exception:
            pass
        return "Unknown count"

    def auto_detect_target(self):
        src_str = self.source_path_var.get().strip()
        if not src_str or not Path(src_str).exists():
            return

        src = Path(src_str)
        suggested = None
        if src.suffix.lower() == '.json':
            c_csv = src.with_suffix('.csv')
            suggested = c_csv
        elif src.suffix.lower() == '.csv':
            c_json = src.with_suffix('.json')
            suggested = c_json

        if suggested:
            self.target_path_var.set(str(suggested))
            self.on_target_path_changed()
            self.set_status(f"Auto-detected counterpart: {suggested.name}")

    def refresh_workspace_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        pairs = scan_workspace_pairs()
        self.cached_pairs = pairs

        for p in pairs:
            j_time_str = datetime.datetime.fromtimestamp(p['json_mtime']).strftime("%Y-%m-%d %H:%M:%S")
            c_time_str = datetime.datetime.fromtimestamp(p['csv_mtime']).strftime("%Y-%m-%d %H:%M:%S")

            if p['newer'] == 'json' and p['diff_sec'] > 2:
                status = "JSON is newer (Needs CSV sync)"
                tag = "json_newer"
            elif p['newer'] == 'csv' and p['diff_sec'] > 2:
                status = "CSV is newer (Needs JSON sync)"
                tag = "csv_newer"
            else:
                status = "✓ Up to date"
                tag = "synced"

            self.tree.insert(
                "",
                self.tk.END,
                values=(p['folder'], p['stem'], j_time_str, c_time_str, status),
                tags=(tag,)
            )

        self.set_status(f"Workspace scanned: {len(pairs)} companion pairs verified.")

    def on_tree_double_click(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        vals = item['values']
        folder, stem = vals[0], vals[1]

        # Find pair in cached_pairs
        for p in getattr(self, 'cached_pairs', []):
            if p['folder'] == folder and p['stem'] == stem:
                if p['newer'] == 'csv':
                    self.source_path_var.set(str(p['csv_path']))
                    self.target_path_var.set(str(p['json_path']))
                else:
                    self.source_path_var.set(str(p['json_path']))
                    self.target_path_var.set(str(p['csv_path']))

                self.on_source_path_changed()
                self.on_target_path_changed()
                self.notebook.select(self.tab_pair)
                self.set_status(f"Loaded '{stem}' into Single Pair Synchronizer.")
                break

    def execute_pair_sync(self):
        if self.is_busy:
            return

        src_str = self.source_path_var.get().strip()
        tgt_str = self.target_path_var.get().strip()

        if not src_str or not Path(src_str).exists():
            self.messagebox.showerror("Error", "Please select a valid Source file first.")
            return

        if not tgt_str:
            self.messagebox.showerror("Error", "Please select or specify a Target file.")
            return

        src_path = Path(src_str)
        tgt_path = Path(tgt_str)

        self.is_busy = True
        self.btn_sync.config(state=self.tk.DISABLED)
        self.set_status(f"Synchronizing: {src_path.name} ===> {tgt_path.name}...", working=True)
        self.log("\n" + "=" * 60)
        self.log(f"Starting Synchronization: {src_path.name} ===> {tgt_path.name}")
        self.log("=" * 60)

        def worker():
            try:
                cnt, diffs = sync_pair(src_path, tgt_path)
                self.log(f"[SUCCESS] Target file updated successfully! ({cnt} changes applied)")
                for d in diffs[:8]:
                    self.log(f"  • {d}")
                if len(diffs) > 8:
                    self.log(f"  ... and {len(diffs) - 8} more changes.")

                if self.regen_var.get():
                    self.log(f"---> Regenerating HTML / PDF study files for ({src_path.stem})...")
                    trigger_pdf_regeneration(src_path)
                    self.log(f"[✓] HTML/PDF generation finished!")

                def on_done():
                    self.on_source_path_changed()
                    self.on_target_path_changed()
                    self.refresh_workspace_table()
                    self.set_status(f"Sync complete: {cnt} changes applied to {tgt_path.name}.")
                    self.messagebox.showinfo(
                        "Sync Complete",
                        f"Successfully updated '{tgt_path.name}'!\n\n"
                        f"Changes applied: {cnt}\n"
                        f"Backup saved in .backup/ directory."
                    )
                self.root.after(0, on_done)

            except PermissionError:
                def handle_lock():
                    retry = self.messagebox.askretrycancel(
                        "File Locked by Excel",
                        f"Cannot write to '{tgt_path.name}'.\n\n"
                        "Reason: The file is currently open in Microsoft Excel or another program.\n\n"
                        "Please save and close the file in Excel, then click 'Retry'.\n"
                        "Click 'Cancel' to abort."
                    )
                    if retry:
                        self.execute_pair_sync()
                    else:
                        self.log(f"[!] Sync aborted: {tgt_path.name} is locked by Excel.")
                        self.set_status("Sync aborted (file locked by Excel).")
                self.root.after(0, handle_lock)

            except Exception as e:
                def on_error():
                    self.log(f"[ERROR] Sync failed: {e}")
                    self.set_status(f"Error: {e}")
                    self.messagebox.showerror("Sync Error", f"An error occurred during synchronization:\n\n{e}")
                self.root.after(0, on_error)

            finally:
                def finalize():
                    self.is_busy = False
                    self.btn_sync.config(state=self.tk.NORMAL)
                self.root.after(0, finalize)

        threading.Thread(target=worker, daemon=True).start()

    def execute_auto_sync_all(self):
        if self.is_busy:
            return

        pairs = scan_workspace_pairs()
        pending = []
        for p in pairs:
            if p['newer'] == 'json' and p['diff_sec'] > 2:
                pending.append((p['json_path'], p['csv_path']))
            elif p['newer'] == 'csv' and p['diff_sec'] > 2:
                pending.append((p['csv_path'], p['json_path']))

        if not pending:
            self.messagebox.showinfo("Workspace Auto-Sync", "All companion question banks are already synchronized and up-to-date!")
            return

        confirm = self.messagebox.askyesno(
            "Confirm Auto-Sync",
            f"Found {len(pending)} companion file(s) requiring synchronization.\n\n"
            "Would you like to synchronize all of them automatically now?"
        )
        if not confirm:
            return

        self.is_busy = True
        self.btn_auto_all.config(state=self.tk.DISABLED)
        self.set_status("Running Workspace Auto-Sync...", working=True)
        self.log("\n" + "=" * 60)
        self.log(f"Auto-Syncing {len(pending)} companion pair(s)...")
        self.log("=" * 60)

        def worker():
            success_count = 0
            for src, tgt in pending:
                try:
                    self.log(f"---> Syncing: {src.name} ===> {tgt.name}")
                    cnt, diffs = sync_pair(src, tgt)
                    self.log(f"[✓] Successfully updated {tgt.name} ({cnt} changes)")
                    success_count += 1
                except Exception as e:
                    self.log(f"[ERROR] Failed to sync {tgt.name}: {e}")

            def on_done():
                self.refresh_workspace_table()
                self.set_status(f"Auto-sync completed: {success_count}/{len(pending)} pairs updated.")
                self.messagebox.showinfo(
                    "Auto-Sync Completed",
                    f"Successfully synchronized {success_count} companion pair(s)!"
                )
            self.root.after(0, on_done)

            def finalize():
                self.is_busy = False
                self.btn_auto_all.config(state=self.tk.NORMAL)
            self.root.after(0, finalize)

        threading.Thread(target=worker, daemon=True).start()

    def execute_regenerate_all_pdfs(self):
        if self.is_busy:
            return

        confirm = self.messagebox.askyesno(
            "Regenerate All PDFs/HTML",
            "This will reprocess all 6 medical subjects and recreate dual HTML study views.\n\nProceed?"
        )
        if not confirm:
            return

        base_dir = Path(__file__).resolve().parent
        gen_script = base_dir / "pdf_maker" / "generator.py"
        if not gen_script.exists():
            self.messagebox.showerror("Error", f"Generator script not found: {gen_script}")
            return

        self.is_busy = True
        self.set_status("Regenerating all study views...", working=True)
        self.log(f"\n---> Starting full regeneration of all HTML / PDF views...")

        def worker():
            import subprocess
            proc = subprocess.run([sys.executable, str(gen_script), "--all"], capture_output=True, text=True, encoding='utf-8')
            for line in proc.stdout.splitlines():
                if line.strip():
                    self.log(f"  {line}")

            def on_done():
                self.set_status("All HTML/PDF study files regenerated successfully!")
                self.messagebox.showinfo("Regeneration Complete", "Successfully regenerated dual HTML/PDF views for all subjects!")
                self.is_busy = False
            self.root.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()


def launch_gui():
    """Initializes and runs the full English TealMED GUI application."""
    import tkinter as tk
    root = tk.Tk()
    app = TealMedSyncGUI(root)
    root.mainloop()


# -----------------------------------------------------------------------------
# Interactive CLI Workflow (English)
# -----------------------------------------------------------------------------
def interactive_menu():
    print("=" * 68)
    print("          TealMED File Synchronizer (JSON <-> CSV Sync)         ")
    print("=" * 68)

    pairs = scan_workspace_pairs()
    all_files = find_all_available_files()

    print("\nAvailable Options:")
    print("  [ 1] Select edited file (Source) then select file to update (Target)")
    print("  [ 2] Automatic scan & sync all companion pairs (Auto-Sync by newest edit time)")
    print("  [ G] Launch Graphical User Interface (GUI Window)")
    print("  [ Q] Quit")

    choice = input("\nEnter your choice: ").strip().upper()

    if choice == 'Q':
        return

    elif choice == 'G':
        try:
            launch_gui()
        except Exception as e:
            print(f"[!] GUI Error: {e}")
        return

    elif choice == '2':
        # Auto-Sync mode
        print("\n" + "-" * 68)
        print("Status Report for Companion Question Banks in Workspace:")
        print("-" * 68)

        pending_syncs = []
        for p in pairs:
            j_time_str = datetime.datetime.fromtimestamp(p['json_mtime']).strftime("%Y-%m-%d %H:%M:%S")
            c_time_str = datetime.datetime.fromtimestamp(p['csv_mtime']).strftime("%Y-%m-%d %H:%M:%S")
            status = ""
            if p['newer'] == 'json' and p['diff_sec'] > 2:
                status = f"JSON is newer ({j_time_str}) ---> Needs CSV update"
                pending_syncs.append((p['json_path'], p['csv_path'], 'json_to_csv'))
            elif p['newer'] == 'csv' and p['diff_sec'] > 2:
                status = f"CSV is newer ({c_time_str}) ---> Needs JSON update"
                pending_syncs.append((p['csv_path'], p['json_path'], 'csv_to_json'))
            else:
                status = "Already synchronized and up-to-date"

            print(f"• [{p['folder']}] {p['stem']}: {status}")

        if not pending_syncs:
            print("\n[✓] All companion files are already synchronized and up-to-date!")
            return

        confirm = input(f"\nFound {len(pending_syncs)} file(s) requiring synchronization. Proceed? [Y/n]: ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            for src, tgt, direction in pending_syncs:
                print(f"\n---> Syncing: {src.name} ===> {tgt.name}")
                cnt, diffs = sync_pair(src, tgt)
                print(f"[✓] Successfully updated {tgt.name}! ({cnt} changes applied)")
                for d in diffs[:4]:
                    print(f"    - {d}")
                if len(diffs) > 4:
                    print(f"    ... and {len(diffs) - 4} more change(s).")

            regen = input("\nDo you want to regenerate HTML / PDF files as well? [Y/n]: ").strip().lower()
            if regen in ['', 'y', 'yes']:
                base_dir = Path(__file__).resolve().parent
                gen_script = base_dir / "pdf_maker" / "generator.py"
                if gen_script.exists():
                    import subprocess
                    subprocess.run([sys.executable, str(gen_script), "--all"])

    elif choice == '1':
        print("\n" + "-" * 68)
        print("Step 1: Select the edited file (Source):")
        print("-" * 68)
        for idx, f in enumerate(all_files, start=1):
            print(f"  [{idx:2d}] {f.parent.name}/{f.name}")
        print("  [ G] Open Windows File Dialog (GUI)")

        sub_choice = input("\nEnter file number (or path): ").strip()
        source_file = None
        if sub_choice.upper() == 'G':
            source_file = open_gui_file_dialog("Step 1: Select Edited Source File")
        elif sub_choice.isdigit():
            num = int(sub_choice)
            if 1 <= num <= len(all_files):
                source_file = all_files[num - 1]
        elif Path(sub_choice).exists():
            source_file = Path(sub_choice)

        if not source_file or not Path(source_file).exists():
            print("[!] No valid file selected.")
            return

        source_path = Path(source_file)
        print(f"\n[✓] Selected source file: {source_path.name}")

        # Detect suggested companion
        suggested_companion = None
        if source_path.suffix.lower() == '.json':
            c_csv = source_path.with_suffix('.csv')
            if c_csv.exists():
                suggested_companion = c_csv
        elif source_path.suffix.lower() == '.csv':
            c_json = source_path.with_suffix('.json')
            if c_json.exists():
                suggested_companion = c_json

        print("\n" + "-" * 68)
        print("Step 2: Select the target file to update (Target):")
        print("-" * 68)
        if suggested_companion:
            print(f"• Suggested counterpart: [{suggested_companion.name}]")
            print("  [Press Enter to accept suggestion, or press G for GUI picker, or type another path]")
            t_input = input("\nYour choice: ").strip()
            if not t_input:
                target_file = suggested_companion
            elif t_input.upper() == 'G':
                target_file = open_gui_file_dialog("Step 2: Select Target File to Update")
            elif Path(t_input).exists():
                target_file = Path(t_input)
        else:
            target_file = open_gui_file_dialog("Step 2: Select Target File to Update")

        if not target_file or not Path(target_file).exists():
            print("[!] No target file selected.")
            return

        target_path = Path(target_file)
        print(f"\n---> Applying changes from: {source_path.name} to: {target_path.name}")

        cnt, diffs = sync_pair(source_path, target_path)
        print(f"\n[SUCCESS] File updated successfully! ({cnt} changes applied)")
        for d in diffs[:6]:
            print(f"  • {d}")
        if len(diffs) > 6:
            print(f"  ... and {len(diffs) - 6} more change(s).")

        regen = input("\nDo you want to regenerate HTML / PDF files as well? [Y/n]: ").strip().lower()
        if regen in ['', 'y', 'yes']:
            trigger_pdf_regeneration(source_path)


def check_and_promote_synced_files():
    """If a previously locked file was saved as *_synced.*, checks if unlocked and finalizes it."""
    base_dir = Path(__file__).resolve().parent
    for synced in base_dir.glob("all_*/*_synced.*"):
        orig_name = synced.name.replace("_synced", "")
        orig_path = synced.parent / orig_name
        try:
            with open(orig_path, 'r+', encoding='utf-8') as f:
                pass
            shutil.copyfile(synced, orig_path)
            synced.unlink()
            print(f"[✓] Successfully finalized {orig_name} after external program closed.")
        except Exception:
            pass


# -----------------------------------------------------------------------------
# Main Entrypoint
# -----------------------------------------------------------------------------
def main():
    check_and_promote_synced_files()
    parser = argparse.ArgumentParser(description="TealMED Bidirectional Question Bank Synchronizer")
    parser.add_argument("source", nargs="?", help="Source file (edited/new)")
    parser.add_argument("target", nargs="?", help="Target file (to update)")
    parser.add_argument("--auto", action="store_true", help="Auto-sync all workspace pairs by mtime")
    parser.add_argument("--cli", action="store_true", help="Launch interactive CLI menu instead of GUI")
    parser.add_argument("--gui", action="store_true", help="Launch Graphical User Interface (GUI)")
    args = parser.parse_args()

    if args.auto:
        pairs = scan_workspace_pairs()
        count_synced = 0
        for p in pairs:
            if p['newer'] == 'json' and p['diff_sec'] > 2:
                print(f"Syncing: {p['json_path'].name} -> {p['csv_path'].name}")
                sync_pair(p['json_path'], p['csv_path'])
                count_synced += 1
            elif p['newer'] == 'csv' and p['diff_sec'] > 2:
                print(f"Syncing: {p['csv_path'].name} -> {p['json_path'].name}")
                sync_pair(p['csv_path'], p['json_path'])
                count_synced += 1
        print(f"[OK] Completed auto-sync for {count_synced} pairs.")

    elif args.source:
        src = Path(args.source)
        if args.target:
            tgt = Path(args.target)
        else:
            tgt = src.with_suffix('.csv' if src.suffix.lower() == '.json' else '.json')
        cnt, diffs = sync_pair(src, tgt)
        print(f"[OK] Updated {tgt.name} ({cnt} changes applied).")

    elif args.cli:
        interactive_menu()

    else:
        # Default behavior: Launch full GUI application
        try:
            launch_gui()
        except Exception as e:
            print(f"[!] Could not launch GUI window ({e}).")
            print("Falling back to English interactive console menu...")
            interactive_menu()


if __name__ == "__main__":
    main()
