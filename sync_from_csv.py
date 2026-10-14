#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TealMED Master CSV-to-All Synchronizer
======================================
Automated propagation engine: When you edit any subject's CSV file (e.g., in final/<subject>/),
this tool automatically updates:
1. Companion JSON file (updating options, stems, explanations, adding/removing options or questions).
2. Clean AI Markdown file (_all_ai.md) without explanations and with '(الصحيح)' marker.
3. Universal punctuation standards (: on questions, . on options, no duplicates).
4. Synchronization into all_<subject>/ (CSV, JSON, AI.md, explanations.txt).
5. Regeneration of sliced topic files in all_<subject>/topics/ (CSV and JSON).
6. Automatic execution of pdf_maker/generator.py to update HTML & PDF views.
7. Automatic update of final/manifest.json question counts.
"""

import os
import sys
import re
import csv
import json
import shutil
import datetime
import argparse
from pathlib import Path
from collections import OrderedDict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
FINAL_DIR = BASE_DIR / "final"
MANIFEST_PATH = FINAL_DIR / "manifest.json"
PDF_MAKER_DIR = BASE_DIR / "pdf_maker"
GENERATOR_SCRIPT = PDF_MAKER_DIR / "generator.py"

LETTERS_POOL = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']

MONTH_MAP = {
    'كانون الثاني': 1,
    'شباط': 2,
    'اذار': 3,
    'آذار': 3,
    'نيسان': 4,
    'ايار': 5,
    'أيار': 5,
    'حزيران': 6,
    'تموز': 7,
    'اب': 8,
    'آب': 8,
    'ايلول': 9,
    'أيلول': 9,
    'تشرين الاول': 10,
    'تشرين الأول': 10,
    'تشرين الثاني': 11,
    'كانون الاول': 12,
    'كانون الأول': 12,
    'تشرين': 10.5,
    'كانون': 12,
    'دكتوراه': 13,
    'فصل اول': 4,
    'فصل أول': 4,
    'فصل ثاني': 7,
    'فصل ثان': 7,
    'دورة اولى': 4,
    'دورة أولى': 4,
    'دورة ثانية': 7,
    'تكميلية': 9.5,
    'استثنائية': 9.6,
    'ربيع': 4,
    'صيف': 7,
    'خريف': 10,
    'شتاء': 1
}

SYLLABUS_TOPIC_ORDERS = {
    "cardio": [
        '01 — التظاهرات السريرية والفحص القلبي الوعائي',
        '02 — قصور القلب والصدمة القلبية',
        '03 — الغشي والخفقان وتوقف القلب والنفخات',
        '04 — اضطرابات النظم والنقل القلبي',
        '05 — داء الشرايين الإكليلية',
        '06 — أمراض الشرايين المحيطية والأبهر',
        '07 — فرط الضغط الشرياني',
        '08 — أمراض الصمامات القلبية والتهاب الشغاف',
        '09 — أمراض القلب الخلقية',
        '10 — أمراض العضلة القلبية والتأمور'
    ],
    "plastic": [
        'الحروق',
        'الجراحة الترميمية والتجميلية',
        'أورام الجلد'
    ],
    "ped_surgery": [
        'التشوهات الخلقية في الجهاز الهضمي والحجاب الحاجز',
        'الانسدادات المعوية وآفات جدار البطن والمنطقة الشرجية',
        'أورام الأطفال الجراحية ورتق الطرق الصفراوية'
    ],
    "onco": [
        'جراحة أورام الغدة الدرقية وجارات الدرق'
    ]
}

def parse_exam_date(text):
    if not text:
        return (0, 0.0)
    raw = str(text)
    norm = raw.replace('ـ', '')
    y_match = re.search(r'((?:19|20)\d\d)', norm)
    year = int(y_match.group(1)) if y_match else 0
    m_val = 0.0
    for name, weight in sorted(MONTH_MAP.items(), key=lambda x: -len(x[0])):
        if name in norm:
            m_val = float(weight)
            break
    return (year, m_val)

# -----------------------------------------------------------------------------
# Punctuation & Normalization Utilities
# -----------------------------------------------------------------------------

def clean_text(s):
    if not s:
        return ""
    return re.sub(r'[\s\.:：،,\(\)\[\]]+', '', s)

def norm_stem(s):
    if not s or not isinstance(s, str):
        return ""
    s = s.strip()
    # Remove any trailing "رأس" or similar artifact from extraction
    s = re.sub(r'[\s:：]*رأس\s*[:：]*$', '', s)
    s = re.sub(r'[\s:：؟?.]+$', '', s)
    return s + ':'

def norm_option(s):
    if not s or not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r'[\s.:：]+$', '', s)
    return s + '.'

def normalize_explanation_text(text):
    if not text or not isinstance(text, str):
        return ""
    
    t = text.strip()
    
    # 0. Heal accidental splits like "(خلايا \n\n C)"
    t = re.sub(r'\(خلايا\s*\n*\s*C\)\s*', '(خلايا C) ', t)
    
    # 1. Standardize section headers on dedicated lines
    headers = [
        'التعليل السريري', 'التعليل', 'الشرح',
        'الخيارات الأخرى', 'تفنيد الخيارات',
        'ترميم امتحاني', 'الترميم الشامل',
        'ملاحظة سريرية', 'ملاحظة'
    ]
    for hdr in headers:
        t = re.sub(
            rf'(?:\n\s*)*\s*(?:-\s*)?({hdr})\s*[:：]\s*',
            rf'\n\n- \1:\n',
            t
        )
    t = t.strip()
    
    # 2. In options sections, separate options [A-F][.)] onto distinct paragraphs
    parts = re.split(r'(\n\n-\s*(?:الخيارات\s+الأخرى|تفنيد\s+الخيارات)\s*[:：]\s*\n)', t)
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            sec_header = parts[i]
            sec_body = parts[i+1] if i+1 < len(parts) else ""
            next_sec_m = re.search(r'\n\n-\s*[\u0600-\u06FF]', sec_body)
            if next_sec_m:
                opts_part = sec_body[:next_sec_m.start()]
                after_part = sec_body[next_sec_m.start():]
            else:
                opts_part = sec_body
                after_part = ""
                
            opts_part = re.sub(r'(?:(?<=[\n.؛;!])|^)\s*(?<!\()([A-F])[:.)ـ]\s*', r'\n\n\1) ', opts_part).strip()
            opts_part = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', lambda m: m.group(1) + '.\u200F' + m.group(2), opts_part)
            
            parts[i] = sec_header
            parts[i+1] = opts_part + ('\n\n' + after_part.strip() if after_part else '')
        t = ''.join(parts).strip()
    else:
        opts_found = list(re.finditer(r'(?:(?<=[\n.؛;!])|^)\s*(?<!\()([A-F])[:.)ـ]\s*', t))
        if len(opts_found) > 1:
            t = re.sub(r'(?:(?<=[\n.؛;!])|^)\s*(?<!\()([A-F])[:.)ـ]\s*', r'\n\n\1) ', t).strip()
            t = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', lambda m: m.group(1) + '.\u200F' + m.group(2), t)

    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

def create_backup(file_path):
    p = Path(file_path)
    if not p.exists():
        return None
    backup_dir = p.parent / ".backup"
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    b_path = backup_dir / f"{p.stem}_{timestamp}{p.suffix}"
    shutil.copyfile(p, b_path)
    return b_path

def sanitize_filename(name: str) -> str:
    if not name:
        return "غير_محدد"
    clean = re.sub(r'[^\w\u0600-\u06FF]+', '_', str(name).strip())
    clean = clean.strip('._')
    return clean or "عام"


def export_sliced_csvs(parent_folder: Path, csv_rows: list, fieldnames: list, verbose: bool = True):
    stem = parent_folder.name + "_all"

    # 1. Remove years/ folder if present
    years_dir = parent_folder / "years"
    if years_dir.exists():
        shutil.rmtree(years_dir)

    # 3. Export topics/ as CSV files
    topics_dir = parent_folder / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)
    for h in topics_dir.glob("*.html"):
        try:
            h.unlink()
        except Exception:
            pass

    topics_dict = OrderedDict()
    for r in csv_rows:
        t = (r.get("Chapter_or_Section") or "عام").strip() or "عام"
        topics_dict.setdefault(t, []).append(r)

    created_topic_files = set()
    for top_name, top_rows in topics_dict.items():
        clean_top = sanitize_filename(top_name)
        out_csv = topics_dir / f"{stem}_{clean_top}.csv"
        created_topic_files.add(out_csv.name)
        with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(top_rows)

    for old_file in topics_dir.glob(f"{stem}_*.csv"):
        if old_file.name not in created_topic_files:
            try:
                old_file.unlink()
            except Exception:
                pass

    # 4. Export sessions/ as CSV files
    sessions_dir = parent_folder / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    for h in sessions_dir.glob("*.html"):
        try:
            h.unlink()
        except Exception:
            pass

    sessions_dict = OrderedDict()
    for r in csv_rows:
        s = (r.get("Exam_Date") or "غير_محدد").strip() or "غير_محدد"
        sessions_dict.setdefault(s, []).append(r)

    created_session_files = set()
    for sess_name, sess_rows in sessions_dict.items():
        clean_sess = sanitize_filename(sess_name)
        out_csv = sessions_dir / f"{stem}_{clean_sess}.csv"
        created_session_files.add(out_csv.name)
        with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(sess_rows)

    for old_file in sessions_dir.glob(f"{stem}_*.csv"):
        if old_file.name not in created_session_files:
            try:
                old_file.unlink()
            except Exception:
                pass

    if verbose:
        print(f"[✓] Sliced CSVs updated: topics/ ({len(topics_dict)} files), sessions/ ({len(sessions_dict)} files).")


# -----------------------------------------------------------------------------
# Core Engine: Synchronize a Single Subject from CSV
# -----------------------------------------------------------------------------
def sync_subject_from_csv(csv_file_path, run_generator=False, verbose=True, sort_topics=True):
    csv_path = Path(csv_file_path).resolve()
    if not csv_path.exists():
        print(f"[!] Error: File not found: {csv_path}")
        return False

    parent_folder = csv_path.parent
    stem = csv_path.stem
    if stem.endswith('_all'):
        subject_slug = stem[:-4]
    else:
        subject_slug = stem

    companion_json = parent_folder / f"{stem}.json"
    companion_ai_md = parent_folder / f"{stem}_ai.md"

    # Identify companion in all_<subject>/ if current is in final/
    all_subject_dir = BASE_DIR / f"all_{subject_slug}"

    if verbose:
        print(f"\n=======================================================")
        print(f" Processing: {csv_path.name} (Subject: {subject_slug})")
        print(f"=======================================================")

    # 1. Load CSV
    create_backup(csv_path)
    csv_rows = None
    fieldnames = None
    for enc in ['utf-8-sig', 'utf-8', 'cp1256']:
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames)
                csv_rows = list(reader)
                break
        except Exception:
            continue

    if csv_rows is None or not fieldnames:
        print(f"[!] Failed to read CSV: {csv_path}")
        return False

    # Strip any stray BOM characters from fieldnames and row keys
    fieldnames = [c.lstrip('\ufeff') for c in fieldnames]
    has_edu_col = any(c.strip().lower() in ['educational_objective', 'الهدف_من_السؤال', 'الهدف من السؤال', 'الهدف_التعليمي', 'الهدف التعليمي'] for c in fieldnames)
    if not has_edu_col:
        hy_idx = next((i for i, c in enumerate(fieldnames) if c.strip().lower() in ['high_yield_note', 'الفكرة_من_السؤال', 'الفكرة من السؤال', 'نقطة_عالية_الأهمية', 'نقطة عالية الأهمية']), -1)
        if hy_idx != -1:
            fieldnames.insert(hy_idx + 1, 'Educational_Objective')
        else:
            exp_idx = next((i for i, c in enumerate(fieldnames) if c.strip().lower() in ['explanation', 'التعليل', 'الشرح']), -1)
            if exp_idx != -1:
                fieldnames.insert(exp_idx + 1, 'Educational_Objective')
            else:
                fieldnames.append('Educational_Objective')

    cleaned_rows = []
    for r in csv_rows:
        cleaned_rows.append({(k.lstrip('\ufeff') if isinstance(k, str) else k): v for k, v in r.items()})
    csv_rows = cleaned_rows

    id_col = 'Question_ID' if 'Question_ID' in fieldnames else fieldnames[0]

    # 3. Load Existing JSON if available
    old_json_items = []
    old_by_id = {}
    old_by_stem = {}
    if companion_json.exists():
        create_backup(companion_json)
        try:
            with open(companion_json, 'r', encoding='utf-8') as f:
                old_json_items = json.load(f)
            for it in old_json_items:
                qid = it.get('id')
                if qid:
                    old_by_id[qid] = it
                st = (it.get('title') or '').strip()
                if st:
                    old_by_stem[st] = it
        except Exception as e:
            print(f"[!] Warning reading existing JSON: {e}")

    # Fallback to all_<subject>/ companion if old_json_items is empty
    if not old_json_items and all_subject_dir.exists():
        alt_json = all_subject_dir / companion_json.name
        if alt_json.exists():
            try:
                with open(alt_json, 'r', encoding='utf-8') as f:
                    old_json_items = json.load(f)
                for it in old_json_items:
                    qid = it.get('id')
                    if qid:
                        old_by_id[qid] = it
                    st = (it.get('title') or '').strip()
                    if st:
                        old_by_stem[st] = it
            except Exception:
                pass

    # 2. Normalize punctuation in CSV rows & Map to old JSON items BEFORE sorting/renumbering
    csv_repaired = False
    row_to_old_item = {}
    for idx, r in enumerate(csv_rows, start=1):
        raw_qid = r.get(id_col) or r.get('Question_ID') or r.get('\ufeffQuestion_ID') or f"q_{subject_slug}_{idx:02d}"
        old_item = old_by_id.get(raw_qid)
        if not old_item:
            stem_candidate = norm_stem(r.get('Question_Text', ''))
            if stem_candidate in old_by_stem:
                old_item = old_by_stem[stem_candidate]
        row_to_old_item[id(r)] = old_item

        # Recover #NAME? Excel formula errors & clean Excel formula escaping artifacts (e.g. "'-")
        for col_name in fieldnames:
            if col_name in r and isinstance(r[col_name], str) and "'-" in r[col_name]:
                r[col_name] = r[col_name].replace("'-", "-")
                csv_repaired = True

        for field_k, json_k in [('Explanation', 'explanation'), ('High_Yield_Note', 'high_yield_note'), ('Educational_Objective', 'educational_objective')]:
            val = r.get(field_k, '')
            old_val = (old_item.get(json_k) or '') if old_item else ''
            if ('#NAME?' in str(val) or not (val or '').strip()) and old_val and '#NAME?' not in str(old_val):
                r[field_k] = old_val.strip()
                csv_repaired = True
        r['Explanation'] = normalize_explanation_text(r.get('Explanation', ''))
        r['Question_Text'] = norm_stem(r.get('Question_Text', ''))
        for opt_col in ['Correct_Answer', 'Wrong_Answer_1', 'Wrong_Answer_2', 'Wrong_Answer_3', 'Wrong_Answer_4', 'Wrong_Answer_5']:
            val = r.get(opt_col, '')
            if val and val.strip():
                r[opt_col] = norm_option(val)
            else:
                r[opt_col] = ''

    # 3. Sort by Topic and Exam Date (from newest to oldest) if requested
    if sort_topics:
        topic_order = []
        if subject_slug in SYLLABUS_TOPIC_ORDERS:
            topic_order = list(SYLLABUS_TOPIC_ORDERS[subject_slug])
        elif MANIFEST_PATH.exists():
            try:
                with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                sub_info = manifest_data.get('subjects', {}).get(subject_slug, {})
                topic_order = list(sub_info.get('topics', []))
            except Exception:
                pass

        grouped_topics = OrderedDict()
        for t in topic_order:
            grouped_topics[t] = []

        for r in csv_rows:
            t = (r.get('Chapter_or_Section') or 'عام').strip()
            grouped_topics.setdefault(t, []).append(r)

        sorted_rows = []
        for t, q_rows in grouped_topics.items():
            if not q_rows:
                continue
            # Sort within topic chronologically by exam date from newest to oldest (stable sort)
            q_rows.sort(key=lambda r: parse_exam_date(r.get('Exam_Date', '')), reverse=True)
            sorted_rows.extend(q_rows)

        csv_rows = sorted_rows

        # Renumber Question_ID sequentially
        num_width = 3 if len(csv_rows) >= 100 else 2
        for idx, r in enumerate(csv_rows, start=1):
            new_qid = f"q_{subject_slug}_{idx:0{num_width}d}"
            r[id_col] = new_qid
            if 'Question_ID' in r:
                r['Question_ID'] = new_qid

    # Save normalized and repaired CSV
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    if verbose:
        status_msg = "CSV normalized, sorted & saved" if sort_topics else ("CSV normalized, repaired & saved" if csv_repaired else "CSV normalized & saved")
        print(f"[✓] {status_msg} ({len(csv_rows)} questions).")

    # 4. Build Updated JSON from CSV
    updated_json = []
    num_width = 3 if len(csv_rows) >= 100 else 2
    for idx, r in enumerate(csv_rows, start=1):
        raw_qid = r.get(id_col) or r.get('Question_ID') or r.get('\ufeffQuestion_ID') or f"q_{subject_slug}_{idx:0{num_width}d}"
        stem_txt = norm_stem(r.get('Question_Text', ''))
        subject_name = r.get('Medical_Subject') or "المادة الطبية"
        topic_name = (r.get('Chapter_or_Section') or "عام").strip()
        exam_period = (r.get('Exam_Date') or "").strip()
        explanation = (r.get('Explanation') or '').strip()
        high_yield_note = (r.get('High_Yield_Note') or '').strip()
        educational_objective = ""
        for ek in ['Educational_Objective', 'educational_objective', 'الهدف_من_السؤال', 'الهدف من السؤال', 'الهدف_التعليمي', 'الهدف التعليمي']:
            val_e = r.get(ek)
            if val_e and str(val_e).strip():
                educational_objective = str(val_e).strip()
                break

        # Find matching old JSON question using pre-mapped reference
        old_item = row_to_old_item.get(id(r))
        if not old_item:
            old_item = old_by_id.get(raw_qid)
            if not old_item and stem_txt in old_by_stem:
                old_item = old_by_stem[stem_txt]


        # Extract options from CSV
        correct_txt = norm_option(r.get('Correct_Answer', ''))
        csv_wrongs = []
        for k in range(1, 6):
            w = (r.get(f'Wrong_Answer_{k}') or '').strip()
            if w:
                csv_wrongs.append(norm_option(w))

        # Build options array
        new_options = []
        if old_item and old_item.get('options'):
            old_opts = old_item.get('options', [])
            cor_opt_old = next((o for o in old_opts if o.get('is_correct')), None)
            wrong_opts_old = [o for o in old_opts if not o.get('is_correct')]

            # Update correct option
            c_letter = cor_opt_old.get('letter', 'A') if cor_opt_old else 'A'
            
            # Map existing wrong options
            mapped_options = []
            for w_idx, w_text in enumerate(csv_wrongs):
                if w_idx < len(wrong_opts_old):
                    let = wrong_opts_old[w_idx].get('letter', LETTERS_POOL[len(mapped_options)])
                    mapped_options.append({
                        "letter": let,
                        "text": w_text,
                        "is_correct": False
                    })
                else:
                    # New wrong option added
                    mapped_options.append({
                        "letter": None, # will be assigned
                        "text": w_text,
                        "is_correct": False
                    })

            # Re-assemble with correct option
            all_assembled = []
            cor_inserted = False
            for o in old_opts:
                if o.get('is_correct'):
                    all_assembled.append({
                        "letter": o.get('letter'),
                        "text": correct_txt,
                        "is_correct": True
                    })
                    cor_inserted = True
                else:
                    if mapped_options:
                        mapped_opt = mapped_options.pop(0)
                        mapped_opt['letter'] = o.get('letter')
                        all_assembled.append(mapped_opt)

            # If any new wrong options remain (e.g. Option E or F added)
            used_letters = {o['letter'] for o in all_assembled if o.get('letter')}
            for extra_opt in mapped_options:
                next_let = next((l for l in LETTERS_POOL if l not in used_letters), f"Opt_{len(all_assembled)+1}")
                extra_opt['letter'] = next_let
                used_letters.add(next_let)
                all_assembled.append(extra_opt)

            if not cor_inserted:
                c_letter = next((l for l in LETTERS_POOL if l not in used_letters), "A")
                all_assembled.append({
                    "letter": c_letter,
                    "text": correct_txt,
                    "is_correct": True
                })

            # Sort by letter
            all_assembled.sort(key=lambda o: LETTERS_POOL.index(o['letter']) if o['letter'] in LETTERS_POOL else 99)
            new_options = all_assembled
        else:
            # Brand new question: create standard options (Correct is A, others B..E)
            new_options.append({
                "letter": "A",
                "text": correct_txt,
                "is_correct": True
            })
            for w_idx, w_text in enumerate(csv_wrongs, start=1):
                let = LETTERS_POOL[w_idx]
                new_options.append({
                    "letter": let,
                    "text": w_text,
                    "is_correct": False
                })

        correct_letter = next((o['letter'] for o in new_options if o['is_correct']), "A")

        # Create or update item
        if old_item:
            item = dict(old_item)
        else:
            ed_obj = ""
            if raw_qid == "q_optho_191":
                ed_obj = "معرفة مضادات الاستطباب والتدبير العلاجي الدوائي لالتهاب العنبة الأمامي الحاد."
            elif raw_qid == "q_optho_192":
                ed_obj = "معرفة خصائص وتدبير الحروق الكيميائية للعين والتمييز بين الحروق الحمضية والقلوية."
            if not ed_obj and explanation:
                obj_m = re.search(r'(?:EDUCATIONAL\s+OBJECTIVE|الهدف\s+التعليمي)\s*:\s*(.*?)(?=(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|EXPLANATION|الشرح|التعليل)\s*:|$)', explanation, re.DOTALL | re.IGNORECASE)
                if obj_m:
                    ed_obj = obj_m.group(1).strip()
            if not high_yield_note and explanation:
                hy_m = re.search(r'(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|الفكرة\s+من\s+السؤال)\s*:\s*(.*?)(?=(?:EXPLANATION|الشرح|التعليل)\s*:|$)', explanation, re.DOTALL | re.IGNORECASE)
                if hy_m:
                    high_yield_note = hy_m.group(1).strip()
            item = {
                "difficulty": "متوسط",
                "exam_type": "national_board",
                "points": 10,
                "is_free": 1,
                "vignette": None,
                "attending_clue": None,
                "educational_objective": ed_obj
            }

        item['id'] = raw_qid
        item['subject_name'] = subject_name
        item['topic_name'] = topic_name
        item['exam_period'] = exam_period
        item['title'] = stem_txt
        item['explanation'] = explanation
        item['high_yield_note'] = high_yield_note
        if educational_objective:
            item['educational_objective'] = educational_objective
        elif old_item and old_item.get('educational_objective'):
            item['educational_objective'] = old_item.get('educational_objective')
        elif 'educational_objective' not in item:
            item['educational_objective'] = ""
        item['options'] = new_options
        item['correct_option'] = correct_letter

        updated_json.append(item)

    # Save JSON
    with open(companion_json, 'w', encoding='utf-8') as f:
        json.dump(updated_json, f, ensure_ascii=False, indent=2)
    if verbose:
        print(f"[✓] Companion JSON updated: {companion_json.name} ({len(updated_json)} items).")

    # 5. Build AI Prompt Markdown (_all_ai.md)
    ai_lines = []
    num_width = 3 if len(updated_json) >= 100 else 2
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

    ai_content = "\n".join(ai_lines).strip() + "\n"
    with open(companion_ai_md, 'w', encoding='utf-8') as f:
        f.write(ai_content)
    if verbose:
        print(f"[✓] Clean AI Markdown updated: {companion_ai_md.name} (no explanations).")

    companion_ai_temp_md = parent_folder / f"{stem}_ai_temp.md"
    if companion_ai_temp_md.exists():
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

        with open(companion_ai_temp_md, 'w', encoding='utf-8') as f:
            f.write("\n".join(ai_temp_lines).strip() + "\n")
        if verbose:
            print(f"[✓] Full-explanation AI Markdown updated: {companion_ai_temp_md.name}.")

    # 6. Synchronize explanations.txt in parent folder (e.g. final/<subject>/)
    parent_exp_file = parent_folder / "explanations.txt"
    if parent_exp_file.exists() or "final" in str(parent_folder):
        create_backup(parent_exp_file)
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

        exp_content = "\n".join(exp_lines).strip() + "\n"
        with open(parent_exp_file, 'w', encoding='utf-8') as f:
            f.write(exp_content)
        parent_exp_md = parent_folder / "explanations.md"
        if parent_exp_md.exists() or "final" in str(parent_folder):
            create_backup(parent_exp_md)
            with open(parent_exp_md, 'w', encoding='utf-8') as f:
                f.write(exp_content)
        if verbose:
            print(f"[✓] Explanations file updated: {parent_exp_file.name} ({len(updated_json)} items).")

    # Synchronize into all_<subject>/ if in final/
    if "final" in str(parent_folder) and all_subject_dir.exists():
        # Copy main files
        shutil.copyfile(csv_path, all_subject_dir / csv_path.name)
        shutil.copyfile(companion_json, all_subject_dir / companion_json.name)
        shutil.copyfile(companion_ai_md, all_subject_dir / companion_ai_md.name)

        with open(all_subject_dir / "explanations.txt", 'w', encoding='utf-8') as f:
            f.write(exp_content)

        # Regenerate all_<subject>/topics/
        topics_dir = all_subject_dir / "topics"
        if topics_dir.exists():
            topics_map_json = {}
            for it in updated_json:
                t = it.get("topic_name", "عام")
                topics_map_json.setdefault(t, []).append(it)

            topics_map_csv = {}
            for r in csv_rows:
                t = r.get("Chapter_or_Section", "عام")
                topics_map_csv.setdefault(t, []).append(r)

            # Detect existing topic filenames to preserve numbering prefix if present
            existing_files = list(topics_dir.glob("*.json"))
            prefix_map = {}
            for ef in existing_files:
                # e.g., ent_01_topic.json or rheuma_topic.json
                m = re.match(r'^([a-z]+_\d{2}_)(.+)\.json$', ef.name)
                if m:
                    topic_part = m.group(2).replace('_', ' ')
                    prefix_map[topic_part] = m.group(1)

            for t_idx, (t_name, t_items) in enumerate(topics_map_json.items(), start=1):
                safe_t = t_name.replace(" ", "_")
                if t_name in prefix_map:
                    file_stem = f"{prefix_map[t_name]}{safe_t}"
                else:
                    file_stem = f"{subject_slug}_{safe_t}"

                j_out = topics_dir / f"{file_stem}.json"
                c_out = topics_dir / f"{file_stem}.csv"

                with open(j_out, 'w', encoding='utf-8') as f:
                    json.dump(t_items, f, ensure_ascii=False, indent=2)

                c_items = topics_map_csv.get(t_name, [])
                with open(c_out, 'w', encoding='utf-8-sig', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=fieldnames)
                    w.writeheader()
                    w.writerows(c_items)

        if verbose:
            print(f"[✓] Synchronized into {all_subject_dir.name}/ (csv, json, ai.md, explanations, topics).")

    # 7. Update manifest.json
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Remove any stale subjects that no longer exist in final/
            existing_sub_dirs = {d.name for d in FINAL_DIR.iterdir() if d.is_dir()}
            for stale_key in list(manifest.get('subjects', {}).keys()):
                if stale_key not in existing_sub_dirs:
                    del manifest['subjects'][stale_key]

            if subject_slug in manifest.get('subjects', {}):
                manifest['subjects'][subject_slug]['questions_count'] = len(updated_json)
                ordered_topics = []
                for q in updated_json:
                    t = q.get("topic_name")
                    if t and t not in ordered_topics:
                        ordered_topics.append(t)
                manifest['subjects'][subject_slug]['topics'] = ordered_topics
            tot = sum(s.get('questions_count', 0) for s in manifest.get('subjects', {}).values())
            manifest['total_questions'] = tot
            with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            if verbose:
                print(f"[✓] Manifest updated: {subject_slug} = {len(updated_json)} (Total: {tot}).")
        except Exception as e:
            print(f"[!] Warning updating manifest: {e}")

    # 8. Rebuild sliced topics/ and sessions/ CSV files
    export_sliced_csvs(parent_folder, csv_rows, fieldnames, verbose=verbose)

    # 9. Build master printable HTML file for subject (can be printed directly as PDF)
    if GENERATOR_SCRIPT.exists():
        if verbose:
            print(f"[>] Generating printable master HTML file via generator.py...")
        try:
            sys.path.insert(0, str(PDF_MAKER_DIR))
            import generator
            res = generator.process_single_file(companion_json, export_years=False)
            if verbose:
                print(f"[✓] Printable master HTML generated: {companion_json.stem}.html (Ready to print as PDF)")
        except Exception as e:
            if verbose:
                print(f"[!] Warning generating HTML: {e}")

    # 9. Rebuild Explained Topics Markdown files (topics_md/)
    try:
        sys.path.insert(0, str(BASE_DIR / "tools"))
        import export_explained_topics_md
        export_explained_topics_md.export_subject_explained_topics(parent_folder, verbose=verbose)
        if verbose:
            print(f"[✓] Explained Topics Markdown (topics_md/) updated successfully.")
    except Exception as e:
        if verbose:
            print(f"[!] Warning updating topics_md: {e}")

    print(f"\n[SUCCESS] Successfully synced {subject_slug} from CSV to all companion formats!\n")
    return True

# -----------------------------------------------------------------------------
# Batch Synchronization: All Subjects in final/
# -----------------------------------------------------------------------------
def sync_all_subjects(force=False):
    print("=" * 65)
    print(" TealMED Sync All: Scanning all Master Subjects in final/ ")
    print("=" * 65)
    if not FINAL_DIR.exists():
        print("[!] Error: final/ directory not found.")
        return

    subjects_found = []
    for sub_dir in sorted(FINAL_DIR.iterdir()):
        if sub_dir.is_dir():
            csv_files = list(sub_dir.glob("*_all.csv"))
            if csv_files:
                subjects_found.append((sub_dir.name, csv_files[0]))

    print(f"Found {len(subjects_found)} subjects in final/.\n")
    synced_count = 0
    for name, csv_path in subjects_found:
        companion_json = csv_path.with_suffix('.json')
        needs_sync = force
        if not companion_json.exists():
            needs_sync = True
        elif csv_path.stat().st_mtime > companion_json.stat().st_mtime:
            needs_sync = True

        if needs_sync:
            print(f"--> Syncing: {name} (CSV -> JSON, AI.md, topics/sessions CSVs)...")
            ok = sync_subject_from_csv(csv_path, run_generator=False, verbose=False)
            if ok:
                synced_count += 1
                print(f"    [✓] {name}: Synchronized successfully.")
        else:
            print(f"    {name:18s}: Already up to date.")

    print(f"\n[✓] Completed: {synced_count} subjects synchronized successfully.")

# -----------------------------------------------------------------------------
# Interactive CLI Menu
# -----------------------------------------------------------------------------
def interactive_menu():
    print("=" * 65)
    print(" TealMED CSV-to-All Master Synchronizer ")
    print("=" * 65)
    print("تحديث وتوليد ملفات JSON و AI.md وملفات CSV للأبواب والدورات تلقائياً عند تعديل أي ملف CSV\n")

    subjects = []
    if FINAL_DIR.exists():
        for sub_dir in sorted(FINAL_DIR.iterdir()):
            if sub_dir.is_dir():
                csv_files = list(sub_dir.glob("*_all.csv"))
                if csv_files:
                    subjects.append((sub_dir.name, csv_files[0]))

    for idx, (name, csv_path) in enumerate(subjects, start=1):
        mtime = datetime.datetime.fromtimestamp(csv_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  [{idx:2d}] {name:10s} (آخر تعديل: {mtime})")

    print("\nخيارات سريعة:")
    print("  [ A] مزامنة كافة المواد المعدلة تلقائياً (Sync All Modified)")
    print("  [ F] إعادة مزامنة وتوليد كافة المواد بالكامل (Force All)")
    print("  [ Q] خروج (Quit)")

    choice = input("\nأدخل رقم المادة أو الخيار: ").strip()
    if choice.upper() == 'Q':
        return
    elif choice.upper() == 'A':
        sync_all_subjects(force=False)
    elif choice.upper() == 'F':
        sync_all_subjects(force=True)
    elif choice.isdigit():
        num = int(choice)
        if 1 <= num <= len(subjects):
            name, csv_path = subjects[num - 1]
            sync_subject_from_csv(csv_path, run_generator=False, verbose=True)
        else:
            print("[!] رقم غير صحيح.")
    else:
        print("[!] اختيار غير صحيح.")

# -----------------------------------------------------------------------------
# Command-Line Entry Point
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="TealMED Master CSV-to-All Synchronizer")
    parser.add_argument("file", nargs="?", help="Path to .csv file to synchronize")
    parser.add_argument("--all", action="store_true", help="Sync all modified subjects in final/")
    parser.add_argument("--force", action="store_true", help="Force sync all subjects in final/")
    parser.add_argument("--html", action="store_true", help="Generate HTML/PDF views via generator.py (disabled by default)")
    parser.add_argument("--no-sort", action="store_true", help="Skip topic and chronological date sorting")
    args = parser.parse_args()

    if args.force:
        sync_all_subjects(force=True)
    elif args.all:
        sync_all_subjects(force=False)
    elif args.file:
        sync_subject_from_csv(args.file, run_generator=args.html, verbose=True, sort_topics=not args.no_sort)
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
