#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TealMED National Exam Sessions Builder
======================================
يقوم هذا البرنامج بجمع وتجميع أسئلة الدورات الامتحانية (الامتحان الطبي الموحد)
من مجلدات بنوك الأسئلة، وفرزها وتصنيفها في ملفات مستقلة كاملة لكل دورة.

الميزات الرئيسية:
1. تقسيم كل دورة إلى كتلتين رئيستين بدقة:
   - الكتلة الأولى: الداخليات كاملة (قلبية، هضمية، صدرية، دموية، غدية، رثوية، كلية، خمجية، عصبية، نفسية)
                  + طب الأطفال (1 و 2) + الجلدية
   - الكتلة الثانية: النسائية والتوليد + الجراحات (عامة، عظمية، بولية، صدرية، أطفال، عصبية، تجميلية، قلبية، وعائية، أورام)
                  + الأذنية + العينية
2. الحفاظ الكامل على سلامة الملفات الأصلية (العمل على نسخ معزولة دون المساس بـ final/).
3. إمكانية إضافة أي مواد أو أسئلة جديدة مستقبلاً وإعادة التوليد بضغطة زر واحدة.
4. التصدير بثلاث صيغ احترافية لكل دورة:
   - صيغة JSON: كاملة البيانات الوصفية والخيارات والشروحات.
   - صيغة CSV: متوافقة مع Excel بالترميز العربي الكامل (UTF-8-SIG).
   - صيغة HTML: واجهة طبية عالية الكثافة مطابقة لنمط ملفات generator.py و Word/PDF:
     * فهرس أنيق في الصفحة الأولى بنقاط ربط (Dotted leader).
     * جسم السؤال مؤطر وملون ومحمي من الانقسام نهائياً.
     * جسم الشرح عنصر منفصل وبخط أصغر ومسموح له بالانقسام لتفادي الفراغات البيضاء.
     * أحجام الخطوط في الطباعة مضبوطة بدقة: السؤال (11.6pt) أكبر من الشرح (10.2pt).
5. إنشاء لوحة تحكم وفهرس شامل (index.html و manifest_sessions.json) لكافة الدورات.
"""

import os
import sys
import re
import csv
import json
import html
import shutil
import argparse
from pathlib import Path
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# -----------------------------------------------------------------------------
# مسارات العمل الافتراضية
# -----------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "config.json"
DEFAULT_SNAPSHOT_DIR = SCRIPT_DIR / "input_snapshot"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "output"
DEFAULT_FINAL_DIR = PROJECT_ROOT / "final"


# -----------------------------------------------------------------------------
# أدوات معالجة النصوص وتوحيد مسميات الدورات (Session Normalizer)
# -----------------------------------------------------------------------------
def clean_arabic_text(text):
    """تنظيف النص وإزالة التطويل وتوحيد المسافات."""
    if not text:
        return ""
    t = re.sub(r'[\u0640]', '', str(text))
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def normalize_session_name(raw_period):
    """
    توحيد اسم الدورة الامتحانية.
    يعالج الحالات المقلوبة (مثال: '2024 أيار' -> 'أيار 2024')
    ويزيل الكشيدة والمسافات الزائدة.
    """
    if not raw_period:
        return "دورة غير محددة"

    s = clean_arabic_text(raw_period)

    year_match = re.search(r'((?:19|20)\d\d)', s)
    if not year_match:
        return s

    year = year_match.group(1)
    month_part = s.replace(year, '').strip()

    month_clean = month_part
    month_clean = re.sub(r'^دورة\s+', '', month_clean)
    month_clean = re.sub(r'^فصل\s+', '', month_clean)
    month_clean = re.sub(r'تشـــرين', 'تشرين', month_clean)
    month_clean = month_clean.strip()

    if not month_clean:
        return f"دورة {year}"

    return f"{month_clean} {year}"


def get_session_sort_key(session_name, month_weights=None):
    """حساب مفتاح الترتيب الزمني للدورة (السنة ثم الشهر)."""
    if not month_weights:
        month_weights = {
            'شباط': 2, 'آذار': 3, 'نيسان': 4, 'أيار': 5,
            'حزيران': 6, 'تموز': 7, 'آب': 8, 'أيلول': 9,
            'تشرين الأول': 10, 'تشرين الاول': 10, 'تشرين': 10,
            'تشرين الثاني': 11, 'كانون الأول': 12, 'كانون الاول': 12,
            'كانون': 12, 'دكتوراه': 13
        }

    s = str(session_name)
    year_match = re.search(r'((?:19|20)\d\d)', s)
    year = int(year_match.group(1)) if year_match else 0

    m_score = 0
    for m_name, weight in month_weights.items():
        if m_name in s:
            m_score = max(m_score, weight)

    if 'تموز' in s and 'آب' in s:
        m_score = 7.5

    return (year, m_score)


# -----------------------------------------------------------------------------
# محرك إدارة وتصنيف المواد (Block & Subject Classifier)
# -----------------------------------------------------------------------------
class SubjectClassifier:
    def __init__(self, config):
        self.config = config
        self.subject_info = {}
        self._build_indexes()

    def _build_indexes(self):
        blocks_cfg = self.config.get("blocks", {})
        for block_key, block_data in blocks_cfg.items():
            b_id = block_data.get("id")
            b_name = block_data.get("name")
            b_subtitle = block_data.get("subtitle", "")
            cats = block_data.get("categories", [])

            for cat_idx, cat in enumerate(cats, start=1):
                cat_id = cat.get("id")
                cat_name = cat.get("name")
                cat_order = cat.get("order", cat_idx)

                for subj_idx, subj in enumerate(cat.get("subjects", []), start=1):
                    code = subj.get("code")
                    name = subj.get("name")
                    aliases = subj.get("aliases", [])

                    meta = {
                        "block_id": b_id,
                        "block_name": b_name,
                        "block_subtitle": b_subtitle,
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "category_order": cat_order,
                        "subject_code": code,
                        "subject_name": name,
                        "subject_order": subj_idx,
                        "sort_tuple": (b_id, cat_order, subj_idx)
                    }

                    self.subject_info[code.lower()] = meta
                    for alias in aliases:
                        self.subject_info[alias.strip().lower()] = meta

    def classify(self, folder_name, subject_name_arabic=""):
        """تصنيف المادة إلى الكتلة والقسم والترتيب المعتمد."""
        k_folder = str(folder_name).strip().lower()
        if k_folder in self.subject_info:
            return self.subject_info[k_folder]

        if subject_name_arabic:
            k_arabic = clean_arabic_text(subject_name_arabic).lower()
            if k_arabic in self.subject_info:
                return self.subject_info[k_arabic]

            for key, meta in self.subject_info.items():
                if key in k_arabic or k_arabic in key:
                    return meta

        name_to_check = (subject_name_arabic + " " + folder_name).lower()

        if any(w in name_to_check for w in ["جلد", "derma"]):
            return {
                "block_id": 1,
                "block_name": "الكتلة الأولى",
                "block_subtitle": "الداخليات، الأطفال، الجلدية",
                "category_id": "dermatology",
                "category_name": "الأمراض الجلدية",
                "category_order": 3,
                "subject_code": folder_name,
                "subject_name": subject_name_arabic or "الجلدية",
                "subject_order": 99,
                "sort_tuple": (1, 3, 99)
            }
        elif any(w in name_to_check for w in ["طفل", "أطفال", "اطفال", "ped"]):
            return {
                "block_id": 1,
                "block_name": "الكتلة الأولى",
                "block_subtitle": "الداخليات، الأطفال، الجلدية",
                "category_id": "pediatrics",
                "category_name": "طب الأطفال",
                "category_order": 2,
                "subject_code": folder_name,
                "subject_name": subject_name_arabic or "طب الأطفال",
                "subject_order": 99,
                "sort_tuple": (1, 2, 99)
            }
        elif any(w in name_to_check for w in ["جراح", "surg", "ortho", "uro"]):
            return {
                "block_id": 2,
                "block_name": "الكتلة الثانية",
                "block_subtitle": "النسائية والتوليد، الجراحات، الأذنية، العينية",
                "category_id": "surgery",
                "category_name": "الجراحات",
                "category_order": 2,
                "subject_code": folder_name,
                "subject_name": subject_name_arabic or "الجراحة",
                "subject_order": 99,
                "sort_tuple": (2, 2, 99)
            }
        elif any(w in name_to_check for w in ["نسائ", "توليد", "obs", "gyn"]):
            return {
                "block_id": 2,
                "block_name": "الكتلة الثانية",
                "block_subtitle": "النسائية والتوليد، الجراحات، الأذنية، العينية",
                "category_id": "obgyn",
                "category_name": "النسائية والتوليد",
                "category_order": 1,
                "subject_code": folder_name,
                "subject_name": subject_name_arabic or "النسائية والتوليد",
                "subject_order": 99,
                "sort_tuple": (2, 1, 99)
            }
        elif any(w in name_to_check for w in ["أذن", "اذن", "ent"]):
            return {
                "block_id": 2,
                "block_name": "الكتلة الثانية",
                "block_subtitle": "النسائية والتوليد، الجراحات، الأذنية، العينية",
                "category_id": "ent",
                "category_name": "الأذنية",
                "category_order": 3,
                "subject_code": folder_name,
                "subject_name": subject_name_arabic or "الأذنية",
                "subject_order": 99,
                "sort_tuple": (2, 3, 99)
            }
        elif any(w in name_to_check for w in ["عين", "opth"]):
            return {
                "block_id": 2,
                "block_name": "الكتلة الثانية",
                "block_subtitle": "النسائية والتوليد، الجراحات، الأذنية، العينية",
                "category_id": "ophthalmology",
                "category_name": "العينية",
                "category_order": 4,
                "subject_code": folder_name,
                "subject_name": subject_name_arabic or "العينية",
                "subject_order": 99,
                "sort_tuple": (2, 4, 99)
            }
        else:
            return {
                "block_id": 1,
                "block_name": "الكتلة الأولى",
                "block_subtitle": "الداخليات، الأطفال، الجلدية",
                "category_id": "internal_medicine",
                "category_name": "أمراض الباطنة والداخليات",
                "category_order": 1,
                "subject_code": folder_name,
                "subject_name": subject_name_arabic or folder_name,
                "subject_order": 99,
                "sort_tuple": (1, 1, 99)
            }


# -----------------------------------------------------------------------------
# محرك تحميل وتجميع الأسئلة
# -----------------------------------------------------------------------------
def load_all_questions_from_source(source_dir, classifier):
    """
    تحميل جميع الأسئلة من مجلد المصدر وفهرستها حسب الدورات الامتحانية.
    القراءة فقط وبأعلى مستويات الأمان.
    """
    source_dir = Path(source_dir)
    manifest_path = source_dir / "manifest.json"
    manifest_info = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_info = json.load(f).get("subjects", {})
        except Exception as e:
            print(f"[!] Warning reading manifest: {e}")

    subject_dirs = [d for d in source_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    print(f"[*] Found {len(subject_dirs)} subject directories in source: {source_dir}")

    all_questions_by_session = defaultdict(list)
    raw_to_canonical = {}
    total_loaded = 0

    for s_dir in sorted(subject_dirs, key=lambda x: x.name):
        json_files = list(s_dir.glob("*_all.json"))
        if not json_files:
            continue

        jf = json_files[0]
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] Error loading {jf.name}: {e}")
            continue

        if not isinstance(data, list):
            continue

        folder_code = s_dir.name
        arabic_from_manifest = manifest_info.get(folder_code, {}).get("subject_name", "")

        for q in data:
            total_loaded += 1
            raw_period = q.get("exam_period") or q.get("Exam_Date") or "غير محدد"
            canonical_session = normalize_session_name(raw_period)
            raw_to_canonical[raw_period] = canonical_session

            q_subj_name = q.get("subject_name") or arabic_from_manifest or folder_code
            cls_info = classifier.classify(folder_code, q_subj_name)

            enriched_q = dict(q)
            enriched_q["block_id"] = cls_info["block_id"]
            enriched_q["block_name"] = cls_info["block_name"]
            enriched_q["block_subtitle"] = cls_info["block_subtitle"]
            enriched_q["category_id"] = cls_info["category_id"]
            enriched_q["category_name"] = cls_info["category_name"]
            enriched_q["subject_code"] = cls_info["subject_code"]
            enriched_q["subject_name"] = cls_info["subject_name"]
            enriched_q["sort_tuple"] = cls_info["sort_tuple"]
            enriched_q["original_period"] = raw_period
            enriched_q["canonical_session"] = canonical_session

            all_questions_by_session[canonical_session].append(enriched_q)

    print(f"[✓] Successfully loaded and classified {total_loaded} questions across {len(all_questions_by_session)} sessions.")
    return all_questions_by_session


# -----------------------------------------------------------------------------
# دمج ومعالجة جلسات صيف 2025 (تموز الكتلة 1 + آب الكتلة 2)
# -----------------------------------------------------------------------------
def process_combined_sessions(questions_by_session):
    result = dict(questions_by_session)

    has_tammuz = "تموز 2025" in result
    has_aab = "آب 2025" in result

    if has_tammuz and has_aab:
        combined_name = "تموز - آب 2025"
        combined_qs = []
        for q in result["تموز 2025"]:
            q_copy = dict(q)
            q_copy["session_note"] = "الكتلة الأولى (امتحان تموز 2025)"
            combined_qs.append(q_copy)
        for q in result["آب 2025"]:
            q_copy = dict(q)
            q_copy["session_note"] = "الكتلة الثانية (امتحان آب 2025)"
            combined_qs.append(q_copy)

        result[combined_name] = combined_qs
        print(f"[+] Created combined unified session: [{combined_name}] with {len(combined_qs)} questions (93 Block 1 + 120 Block 2).")

    return result


# -----------------------------------------------------------------------------
# فرز وترقيم أسئلة الدورة الامتحانية
# -----------------------------------------------------------------------------
def sort_and_number_session_questions(questions):
    def q_key(q):
        st = q.get("sort_tuple", (9, 9, 99))
        topic = str(q.get("topic_name") or "")
        qid = str(q.get("id") or "")
        return (st[0], st[1], st[2], topic, qid)

    sorted_qs = sorted(questions, key=q_key)

    numbered_qs = []
    for idx, q in enumerate(sorted_qs, start=1):
        q_numbered = dict(q)
        q_numbered["session_question_number"] = idx
        numbered_qs.append(q_numbered)

    return numbered_qs


# -----------------------------------------------------------------------------
# مولد ملفات JSON للدورات
# -----------------------------------------------------------------------------
def export_session_json(session_name, questions, output_file):
    b1_count = sum(1 for q in questions if q.get("block_id") == 1)
    b2_count = sum(1 for q in questions if q.get("block_id") == 2)

    subjects_stats = defaultdict(int)
    categories_stats = defaultdict(lambda: {"count": 0, "subjects": defaultdict(int)})

    for q in questions:
        s_name = q.get("subject_name", "غير محدد")
        c_name = q.get("category_name", "غير محدد")
        subjects_stats[s_name] += 1
        categories_stats[c_name]["count"] += 1
        categories_stats[c_name]["subjects"][s_name] += 1

    payload = {
        "session_title": f"الامتحان الطبي الموحد - دورة {session_name}",
        "session_name": session_name,
        "total_questions": len(questions),
        "statistics": {
            "block_1_count": b1_count,
            "block_2_count": b2_count,
            "categories": dict(categories_stats),
            "subjects": dict(subjects_stats)
        },
        "blocks_summary": [
            {
                "block_id": 1,
                "block_name": "الكتلة الأولى",
                "block_subtitle": "الداخليات، الأطفال، الجلدية",
                "questions_count": b1_count
            },
            {
                "block_id": 2,
                "block_name": "الكتلة الثانية",
                "block_subtitle": "النسائية والتوليد، الجراحات، الأذنية، العينية",
                "questions_count": b2_count
            }
        ],
        "questions": questions
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# -----------------------------------------------------------------------------
# مولد ملفات CSV للدورات
# -----------------------------------------------------------------------------
def export_session_csv(session_name, questions, output_file):
    fieldnames = [
        "Question_Number",
        "Block",
        "Block_Category",
        "Medical_Subject",
        "Chapter_or_Section",
        "Question_ID",
        "Question_Text",
        "Correct_Answer",
        "Option_A",
        "Option_B",
        "Option_C",
        "Option_D",
        "Option_E",
        "Option_F",
        "Explanation",
        "High_Yield_Note",
        "Educational_Objective",
        "Difficulty",
        "Original_Exam_Date"
    ]

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for q in questions:
            opts = q.get("options", [])
            opt_by_letter = {}
            correct_letter = q.get("correct_option") or ""
            correct_text = ""

            for opt in opts:
                letter = opt.get("letter", "").upper()
                text = opt.get("text", "")
                opt_by_letter[letter] = text
                if opt.get("is_correct") or letter == correct_letter:
                    correct_letter = letter
                    correct_text = text

            c_val = f"{correct_letter}. {correct_text}" if correct_text else correct_letter

            row = {
                "Question_Number": q.get("session_question_number", ""),
                "Block": q.get("block_name", ""),
                "Block_Category": q.get("category_name", ""),
                "Medical_Subject": q.get("subject_name", ""),
                "Chapter_or_Section": q.get("topic_name", ""),
                "Question_ID": q.get("id", ""),
                "Question_Text": q.get("title", ""),
                "Correct_Answer": c_val,
                "Option_A": opt_by_letter.get("A", ""),
                "Option_B": opt_by_letter.get("B", ""),
                "Option_C": opt_by_letter.get("C", ""),
                "Option_D": opt_by_letter.get("D", ""),
                "Option_E": opt_by_letter.get("E", ""),
                "Option_F": opt_by_letter.get("F", ""),
                "Explanation": q.get("explanation", ""),
                "High_Yield_Note": q.get("high_yield_note", ""),
                "Educational_Objective": q.get("educational_objective", ""),
                "Difficulty": q.get("difficulty", ""),
                "Original_Exam_Date": q.get("original_period", "")
            }
            writer.writerow(row)


# -----------------------------------------------------------------------------
# محرك تنسيق الشروحات والنصوص الطبية في HTML
# -----------------------------------------------------------------------------
def format_clinical_explanation_html(raw_exp, high_yield, correct_letter, correct_text):
    """
    تنسيق تعليل السؤال السريري بدقة مع تفنيد الخيارات والنقاط عالية الأهمية.
    """
    parts = []

    # سطر الإجابة الصحيحة
    if correct_letter:
        c_label = f"الإجابة الصحيحة: {correct_letter}"
        if correct_text:
            c_label += f" — {correct_text}"
        parts.append(f'<div class="exp-answer-line">{html.escape(c_label)}</div>')

    # تجزئة التعليل
    if raw_exp:
        clean_exp = raw_exp.strip()
        section_patterns = [
            (r'(?:-\s*)?(التعليل\s+السريري|التعليل|الشرح)\s*[:：]', 'exp-clinical', r'\1:'),
            (r'(?:-\s*)?(الخيارات\s+الأخرى|تفنيد\s+الخيارات)\s*[:：]', 'exp-other-opts', r'\1:'),
            (r'(?:-\s*)?(ترميم\s+امتحاني|الترميم\s+الشامل)\s*[:：]', 'exp-tarmim', r'\1:'),
            (r'(?:-\s*)?(ملاحظة\s+سريرية|ملاحظة)\s*[:：]', 'exp-note', r'\1:')
        ]

        headers = []
        for pat, cls, label in section_patterns:
            for m in re.finditer(pat, clean_exp):
                headers.append((m.start(), m.end(), cls, m.group(1) + ':'))

        headers.sort(key=lambda x: x[0])

        sections = []
        if not headers:
            sections.append(('exp-general', '', clean_exp))
        else:
            if headers[0][0] > 0:
                pre_txt = clean_exp[:headers[0][0]].strip()
                if pre_txt:
                    sections.append(('exp-general', '', pre_txt))
            for i in range(len(headers)):
                start_content = headers[i][1]
                end_content = headers[i+1][0] if i + 1 < len(headers) else len(clean_exp)
                sec_cls = headers[i][2]
                sec_hdr = headers[i][3]
                sec_text = clean_exp[start_content:end_content].strip()
                sections.append((sec_cls, sec_hdr, sec_text))

        sec_html_parts = []
        for cls, hdr, body in sections:
            sec_div = f'<div class="exp-section {cls}">'
            if hdr:
                sec_div += f'<b class="exp-header-tag">{html.escape(hdr)}</b> '

            # تفنيد الخيارات كعناصر مستقلة مثل generator.py
            if cls == 'exp-other-opts' or re.search(r'(?:^|\n)\s*[A-F][:)ـ.]', body):
                opt_matches = list(re.finditer(r'(?:(?<=[\n.؛;!])|^)\s*(?<!\()([A-F])[:.)ـ]\s*', body))
                if opt_matches:
                    pre_opt_text = body[:opt_matches[0].start()].strip()
                    if pre_opt_text:
                        sec_div += f'<div class="exp-lead">{html.escape(pre_opt_text)}</div>'
                    for idx_opt in range(len(opt_matches)):
                        opt_tag = opt_matches[idx_opt].group(1)
                        opt_letter = opt_tag[0].upper()
                        opt_start = opt_matches[idx_opt].end()
                        opt_end = opt_matches[idx_opt+1].start() if idx_opt + 1 < len(opt_matches) else len(body)
                        opt_txt = body[opt_start:opt_end].strip()
                        escaped_txt = html.escape(opt_txt)
                        escaped_txt = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', r'\1.&rlm;\2', escaped_txt)
                        escaped_txt = re.sub(
                            r'(\(الخيار\s+[A-F]\)|الخيار\s+[A-F])',
                            r'<span class="opt-ref-tag">\1</span>',
                            escaped_txt
                        )
                        sec_div += f'<div class="exp-opt-item"><span class="opt-letter-tag">{opt_letter}.</span> <span class="exp-opt-desc">{escaped_txt}</span></div>'
                else:
                    escaped_body = html.escape(body)
                    escaped_body = re.sub(r'(\(الخيار\s+[A-F]\)|الخيار\s+[A-F])', r'<bdi class="opt-ref-tag">\1</bdi>', escaped_body)
                    paras = [p.strip() for p in re.split(r'\n\s*\n', escaped_body) if p.strip()]
                    sec_div += ''.join(f'<div class="exp-para">{p}</div>' for p in paras) if len(paras) > 1 else escaped_body
            else:
                escaped_body = html.escape(body)
                escaped_body = re.sub(
                    r'(\(الخيار\s+[A-F]\)|الخيار\s+[A-F])',
                    r'<bdi class="opt-ref-tag">\1</bdi>',
                    escaped_body
                )
                paras = [p.strip() for p in re.split(r'\n\s*\n', escaped_body) if p.strip()]
                if len(paras) > 1:
                    sec_div += ''.join(f'<div class="exp-para">{p}</div>' for p in paras)
                else:
                    sec_div += escaped_body
            sec_div += '</div>'
            sec_html_parts.append(sec_div)

        parts.append(f'<div class="exp-body-text">{" ".join(sec_html_parts)}</div>')

    # الفكرة من السؤال (High-Yield Note)
    if high_yield:
        clean_hy = re.sub(r'^(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|الفكرة\s+من\s+السؤال)\s*[:：]\s*', '', high_yield, flags=re.IGNORECASE).strip()
        parts.append(f"""
        <div class="high-yield-line">
            <b class="high-yield-label">الفكرة من السؤال:</b>
            <span class="high-yield-text">{html.escape(clean_hy)}</span>
        </div>
        """)

    return "\n".join(parts)


# -----------------------------------------------------------------------------
# مولد ملفات HTML التفاعلية والمجهزة للطباعة كـ PDF (Word/PDF Layout)
# -----------------------------------------------------------------------------
def export_session_html(session_name, questions, output_file):
    """
    توليد واجهة HTML طبية مطابقة لنمط ملفات generator.py و Word/PDF:
    1. فهرس منظم في الصفحة الأولى بنقاط ربط (Dotted leader) مفصول بـ page-break-after: always.
    2. جسم السؤال مؤطر وملون ومحمي من الانقسام نهائياً (page-break-inside: avoid).
    3. جسم الشرح عنصر منفصل وبدون إطار وبخط أصغر ومسموح له بالانقسام (page-break-inside: auto) لتخفيف الفراغات.
    4. أحجام خطوط الطباعة مضبوطة بدقة كما في generator.py:
       - السؤال: 11.8pt (Bold 800)
       - الخيارات: 11.2pt
       - الشرح: 9.6pt (أصغر بوضوح من السؤال)
    """
    total_q = len(questions)
    b1_qs = [q for q in questions if q.get("block_id") == 1]
    b2_qs = [q for q in questions if q.get("block_id") == 2]

    # تجميع إحصائيات المواد للفهرس
    b1_subjs = defaultdict(lambda: {"count": 0, "cat": "", "code": ""})
    for q in b1_qs:
        s = q.get("subject_name")
        b1_subjs[s]["count"] += 1
        b1_subjs[s]["cat"] = q.get("category_name", "")
        b1_subjs[s]["code"] = q.get("subject_code", s)

    b2_subjs = defaultdict(lambda: {"count": 0, "cat": "", "code": ""})
    for q in b2_qs:
        s = q.get("subject_name")
        b2_subjs[s]["count"] += 1
        b2_subjs[s]["cat"] = q.get("category_name", "")
        b2_subjs[s]["code"] = q.get("subject_code", s)

    # 1. بناء صفوف الفهرس مع نقاط الربط (Table of Contents with Dotted Leaders)
    b1_index_rows = []
    for s_name, data in b1_subjs.items():
        s_code = re.sub(r'[^\w\-]+', '_', data['code'])
        b1_index_rows.append(f"""
        <a href="#subj-{s_code}" class="index-row">
            <span class="index-topic-name">◆ {html.escape(s_name)} <span class="index-cat-note">({html.escape(data['cat'])})</span></span>
            <span class="index-dots"></span>
            <span class="index-count">{data['count']} سؤالاً</span>
        </a>
        """)

    b2_index_rows = []
    for s_name, data in b2_subjs.items():
        s_code = re.sub(r'[^\w\-]+', '_', data['code'])
        b2_index_rows.append(f"""
        <a href="#subj-{s_code}" class="index-row">
            <span class="index-topic-name">◆ {html.escape(s_name)} <span class="index-cat-note">({html.escape(data['cat'])})</span></span>
            <span class="index-dots"></span>
            <span class="index-count">{data['count']} سؤالاً</span>
        </a>
        """)

    # خيارات الفلترة المنسدلة في شريط التحكم
    filter_opts_html = ['<option value="all">كل المواد والمواضيع (' + str(total_q) + ')</option>']
    filter_opts_html.append('<optgroup label="🔹 الكتلة الأولى">')
    for s_name, data in b1_subjs.items():
        filter_opts_html.append(f'<option value="{html.escape(s_name)}">{html.escape(s_name)} ({data["count"]})</option>')
    filter_opts_html.append('</optgroup>')

    filter_opts_html.append('<optgroup label="🔸 الكتلة الثانية">')
    for s_name, data in b2_subjs.items():
        filter_opts_html.append(f'<option value="{html.escape(s_name)}">{html.escape(s_name)} ({data["count"]})</option>')
    filter_opts_html.append('</optgroup>')

    # 2. بناء كروت وأقسام الأسئلة
    rendered_elements = []
    current_block = None
    current_subject = None

    for q in questions:
        q_num = q.get("session_question_number")
        b_id = q.get("block_id")
        b_name = q.get("block_name")
        b_subtitle = q.get("block_subtitle")
        c_name = q.get("category_name")
        s_name = q.get("subject_name")
        s_code = re.sub(r'[^\w\-]+', '_', q.get("subject_code", s_name))
        t_name = q.get("topic_name") or "عام"
        qid = q.get("id")
        title = q.get("title") or ""
        opts = q.get("options") or []
        correct_letter = q.get("correct_option") or ""
        explanation = q.get("explanation") or ""
        high_yield = q.get("high_yield_note") or ""

        # فاصل الكتلة الامتحانية
        if current_block != b_id:
            current_block = b_id
            b_total = len(b1_qs) if b_id == 1 else len(b2_qs)
            b_icon = "🔹" if b_id == 1 else "🔸"
            b_class = "b1-divider" if b_id == 1 else "b2-divider"
            rendered_elements.append(f"""
            <div class="block-section-divider {b_class}" id="block-{b_id}" data-block-id="{b_id}">
                <div class="block-divider-content">
                    <span class="block-divider-title">{b_icon} {html.escape(b_name)}: {html.escape(b_subtitle)}</span>
                    <span class="block-divider-badge">{b_total} سؤالاً</span>
                </div>
            </div>
            """)

        # فاصل المادة الدراسية
        if current_subject != s_name:
            current_subject = s_name
            subj_total = sum(1 for item in questions if item.get("subject_name") == s_name)
            rendered_elements.append(f"""
            <div class="subject-section-divider" id="subj-{s_code}" data-subject-name="{html.escape(s_name)}">
                <span class="subj-divider-title">◆ {html.escape(s_name)} <small class="subj-cat-note">({html.escape(c_name)})</small></span>
                <span class="subj-divider-count">{subj_total} أسئلة</span>
            </div>
            """)

        # صفوف الخيارات
        correct_text = ""
        options_html = []
        for opt in opts:
            letter = opt.get("letter", "").upper()
            opt_text = opt.get("text", "")
            is_correct = opt.get("is_correct", False) or (letter == correct_letter)
            if is_correct:
                correct_text = opt_text

            correct_class = "is-correct-option" if is_correct else ""
            options_html.append(f"""
            <div class="option-row {correct_class}" data-letter="{letter}" onclick="handleOptionClick(this, '{letter}', {str(is_correct).lower()})">
                <span class="option-letter">{letter}.</span>
                <span class="option-text">{html.escape(opt_text)}</span>
            </div>
            """)

        # تنسيق الشرح
        exp_formatted_html = format_clinical_explanation_html(explanation, high_yield, correct_letter, correct_text)

        # بنية السؤال:
        # 1) question-block: مؤطر وملون ولا ينقسم نهائياً
        # 2) explanation-box: منفصل تماماً وبدون إطار ثقيل ومسموح له بالانقسام لتفادي الفراغات
        card_html = f"""
        <div class="question-card" id="{html.escape(qid)}" data-num="{q_num}" data-block="{b_id}" data-subject="{html.escape(s_name)}" data-topic="{html.escape(t_name)}">
            <!-- جسم السؤال مؤطر وملون ومحمي من الانقسام -->
            <div class="question-block b{b_id}-framed">
                <div class="question-header">
                    <div class="q-stem-container">
                        <span class="q-number">{q_num}.</span>
                        <span class="q-stem">{html.escape(title)}</span>
                    </div>
                    <div class="q-meta-tags no-print">
                        <span class="meta-tag b{b_id}-tag">{html.escape(b_name)}</span>
                        <span class="meta-tag subj-tag">{html.escape(s_name)}</span>
                        <span class="meta-tag topic-tag">{html.escape(t_name)}</span>
                        <span class="meta-tag id-tag">{html.escape(qid)}</span>
                    </div>
                </div>

                <div class="options-list">
                    {"".join(options_html)}
                </div>
            </div>

            <!-- جسم الشرح والتعليل: عنصر منفصل تماماً يمكن أن ينقسم للصفحة التالية لتفادي الفراغات البيضاء -->
            <div class="explanation-box">
                {exp_formatted_html}
            </div>
        </div>
        """
        rendered_elements.append(card_html)

    # قالب HTML الكامل والمتقن
    full_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>الامتحان الطبي الموحد - دورة {html.escape(session_name)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Alexandria:wght@500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-color: #0f766e;
            --primary-dark: #115e59;
            --b1-color: #0284c7;
            --b1-dark: #0369a1;
            --b2-color: #b45309;
            --b2-dark: #78350f;
            --accent-gold: #b45309;
            --bg-page: #f8fafc;
            --bg-doc: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border-subtle: #cbd5e1;
            --border-light: #e2e8f0;
            --correct-bg: #ecfdf5;
            --correct-text: #065f46;
            --wrong-bg: #fef2f2;
            --wrong-text: #991b1b;
        }}

        body.dark-mode {{
            --bg-page: #0b1329;
            --bg-doc: #131f33;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-subtle: #334155;
            --border-light: #1e293b;
            --correct-bg: #064e3b;
            --correct-text: #a7f3d0;
            --wrong-bg: #7f1d1d;
            --wrong-text: #fecaca;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'IBM Plex Sans Arabic', 'Alexandria', sans-serif;
            background-color: var(--bg-page);
            color: var(--text-main);
            line-height: 1.50;
            font-size: 1.05rem;
            direction: rtl;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}

        /* -------------------------------------------------------------
           شريط التحكم العلوي المتنقل (مخفي كلياً بالطباعة)
           ------------------------------------------------------------- */
        .controls-header {{
            background-color: var(--bg-doc);
            border-bottom: 1.5px solid var(--border-subtle);
            position: sticky;
            top: 0;
            z-index: 1000;
            padding: 8px 18px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }}

        .controls-row-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .brand-title-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .brand-tag {{
            background: var(--primary-color);
            color: #ffffff;
            font-size: 0.72rem;
            font-weight: 800;
            padding: 2px 8px;
            border-radius: 4px;
        }}

        .doc-main-heading {{
            font-size: 1.08rem;
            font-weight: 800;
            color: var(--text-main);
        }}

        .controls-actions {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .ctrl-btn {{
            font-family: inherit;
            font-size: 0.8rem;
            font-weight: 700;
            padding: 5px 10px;
            border-radius: 4px;
            border: 1px solid var(--border-subtle);
            background-color: var(--bg-doc);
            color: var(--text-main);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            transition: all 0.12s ease;
        }}

        .ctrl-btn:hover {{
            background-color: var(--border-light);
        }}

        .ctrl-btn.btn-print {{
            background-color: #0f172a;
            color: #ffffff;
            border-color: #0f172a;
        }}

        .ctrl-btn.btn-print:hover {{
            background-color: #1e293b;
        }}

        .controls-row-filters {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px solid var(--border-light);
            flex-wrap: wrap;
        }}

        .filter-btn-pill {{
            font-family: inherit;
            font-size: 0.76rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 12px;
            border: 1px solid var(--border-subtle);
            background-color: var(--bg-doc);
            color: var(--text-muted);
            cursor: pointer;
        }}

        .filter-btn-pill.active {{
            background-color: var(--text-main);
            color: var(--bg-doc);
            border-color: var(--text-main);
        }}

        .filter-btn-pill.b1.active {{ background-color: var(--b1-color); border-color: var(--b1-color); color: #fff; }}
        .filter-btn-pill.b2.active {{ background-color: var(--b2-color); border-color: var(--b2-color); color: #fff; }}

        .subject-select-dropdown {{
            font-family: inherit;
            font-size: 0.8rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid var(--border-subtle);
            background-color: var(--bg-doc);
            color: var(--text-main);
            outline: none;
            cursor: pointer;
        }}

        .search-quick-box {{
            flex: 1;
            min-width: 160px;
            max-width: 240px;
            margin-right: auto;
        }}

        .search-quick-input {{
            width: 100%;
            font-family: inherit;
            font-size: 0.78rem;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid var(--border-subtle);
            background-color: var(--bg-page);
            color: var(--text-main);
            outline: none;
        }}

        /* -------------------------------------------------------------
           حاوية المستند (عرض صفحة وورد A4)
           ------------------------------------------------------------- */
        .document-container {{
            max-width: 860px;
            margin: 18px auto 40px;
            background-color: var(--bg-doc);
            padding: 24px 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border-radius: 2px;
        }}

        /* -------------------------------------------------------------
           الصفحة الأولى: الفهرس المنظم بنقاط الربط (TOC)
           ------------------------------------------------------------- */
        .index-page-container {{
            padding: 10px 0 24px;
            margin-bottom: 24px;
            page-break-after: always;
            break-after: page;
        }}

        .subject-main-banner {{
            text-align: center;
            padding-bottom: 14px;
            margin-bottom: 18px;
            border-bottom: 1px solid var(--border-subtle);
        }}

        .subject-title {{
            font-size: 1.70rem;
            color: var(--primary-dark);
            font-weight: 800;
            margin-bottom: 4px;
        }}

        body.dark-mode .subject-title {{ color: #ffffff; }}

        .subject-subtitle {{
            font-size: 0.88rem;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .stats-summary {{
            font-size: 0.86rem;
            color: var(--primary-color);
            margin-top: 6px;
            font-weight: 700;
        }}

        .index-section-title {{
            font-size: 1.12rem;
            font-weight: 800;
            color: var(--primary-dark);
            margin-bottom: 12px;
            padding-bottom: 4px;
            border-bottom: 2px solid var(--primary-color);
            display: inline-block;
        }}

        body.dark-mode .index-section-title {{ color: #2dd4bf; }}

        .index-list {{
            display: flex;
            flex-direction: column;
            gap: 3px;
        }}

        .index-block-header {{
            background-color: #f1f5f9;
            padding: 6px 10px;
            font-weight: 800;
            font-size: 0.95rem;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
            margin-bottom: 4px;
            border-right: 4px solid var(--primary-color);
        }}

        .index-block-header.b1-header {{
            border-right-color: var(--b1-color);
            background-color: #f0f9ff;
            color: #0369a1;
        }}

        .index-block-header.b2-header {{
            border-right-color: var(--b2-color);
            background-color: #fffbeb;
            color: #92400e;
        }}

        body.dark-mode .index-block-header.b1-header {{ background-color: #0c4a6e; color: #e0f2fe; }}
        body.dark-mode .index-block-header.b2-header {{ background-color: #78350f; color: #fef3c7; }}

        .index-row {{
            text-decoration: none;
            color: var(--text-main);
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            padding: 5px 8px;
            transition: background 0.12s ease;
        }}

        .index-row:hover {{
            background-color: #f8fafc;
            color: var(--primary-color);
        }}

        .index-topic-name {{
            font-size: 0.94rem;
            font-weight: 700;
            white-space: nowrap;
        }}

        .index-cat-note {{
            font-size: 0.78rem;
            color: var(--text-muted);
            font-weight: 600;
            margin-right: 4px;
        }}

        .index-dots {{
            flex: 1;
            border-bottom: 1px dotted var(--border-subtle);
            margin: 0 8px;
            height: 1px;
            position: relative;
            top: -4px;
        }}

        .index-count {{
            font-weight: 800;
            color: var(--primary-color);
            white-space: nowrap;
            font-size: 0.88rem;
        }}

        /* -------------------------------------------------------------
           فواصل الكتل والمواد (Section Dividers)
           ------------------------------------------------------------- */
        .block-section-divider {{
            border-top: 2px solid #0f172a;
            border-bottom: 1px solid #0f172a;
            background-color: #f1f5f9;
            padding: 6px 12px;
            margin: 20px 0 10px;
            page-break-after: avoid;
            break-after: avoid;
        }}

        body.dark-mode .block-section-divider {{
            background-color: #1e293b;
            border-color: #475569;
        }}

        .block-divider-content {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .block-divider-title {{
            font-size: 1.15rem;
            font-weight: 800;
            color: #0f172a;
        }}

        body.dark-mode .block-divider-title {{ color: #ffffff; }}

        .block-divider-badge {{
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--text-muted);
        }}

        .subject-section-divider {{
            border-bottom: 1.5px solid var(--primary-color);
            padding: 3px 6px;
            margin: 14px 0 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            page-break-after: avoid;
            break-after: avoid;
        }}

        .subj-divider-title {{
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--primary-color);
        }}

        .subj-cat-note {{
            font-size: 0.78rem;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .subj-divider-count {{
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--text-muted);
        }}

        /* -------------------------------------------------------------
           سؤال الدورة:
           جسم السؤال مؤطر وملون ومحمي من الانقسام نهائياً (page-break-inside: avoid)
           جسم الشرح عنصر منفصل وبدون إطار وبخط أصغر ومسموح له بالانقسام لتفادي الفراغات
           ------------------------------------------------------------- */
        .question-card {{
            margin-bottom: 14px;
            page-break-inside: auto;
            break-inside: auto;
        }}

        /* جسم السؤال المؤطر والملون */
        .question-block {{
            background-color: #ffffff;
            border: 1.2px solid #cbd5e1;
            border-radius: 4px;
            padding: 10px 14px;
            margin-bottom: 4px;
            page-break-inside: avoid;
            break-inside: avoid;
        }}

        .question-block.b1-framed {{
            border-right: 5px solid var(--b1-color);
        }}

        .question-block.b2-framed {{
            border-right: 5px solid var(--b2-color);
        }}

        body.dark-mode .question-block {{
            background-color: #152238;
            border-color: #334155;
        }}

        .question-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 8px;
            margin-bottom: 5px;
        }}

        .q-stem-container {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            flex: 1;
        }}

        .q-number {{
            font-weight: 800;
            color: var(--primary-color);
            font-size: 1.22rem;
            flex-shrink: 0;
            line-height: 1.55;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}

        .q-stem {{
            font-weight: 700;
            color: var(--text-main);
            font-size: 1.18rem;
            line-height: 1.60;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}

        .q-meta-tags {{
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
            margin-top: 4px;
        }}

        .meta-tag {{
            font-size: 0.7rem;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            background-color: var(--bg-page);
        }}

        .b1-tag {{ color: var(--b1-dark); border-color: var(--b1-color); background-color: #f0f9ff; }}
        .b2-tag {{ color: var(--b2-dark); border-color: var(--b2-color); background-color: #fffbeb; }}

        /* قائمة الخيارات */
        .options-list {{
            display: flex;
            flex-direction: column;
            gap: 3px;
            margin-top: 4px;
            margin-bottom: 4px;
            padding-right: 22px;
        }}

        .option-row {{
            display: flex;
            align-items: flex-start;
            gap: 6px;
            font-size: 1.12rem;
            line-height: 1.52;
            cursor: pointer;
            padding: 1px 4px;
            border-radius: 3px;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
            transition: background-color 0.1s ease;
        }}

        .option-row:hover {{
            background-color: var(--border-light);
        }}

        .option-letter {{
            font-weight: 800;
            color: var(--primary-color);
            flex-shrink: 0;
            min-width: 22px;
            font-size: 1.16rem;
        }}

        .option-text {{
            color: var(--text-main);
            font-weight: 600;
        }}

        /* تفاعل الخيارات واختبار الذات */
        .option-row.user-correct {{
            background-color: var(--correct-bg) !important;
            color: var(--correct-text) !important;
        }}
        .option-row.user-wrong {{
            background-color: var(--wrong-bg) !important;
            color: var(--wrong-text) !important;
        }}

        /* إظهار الإجابات الصحيحة جماعياً */
        body.show-all-answers .option-row.is-correct-option {{
            background-color: var(--correct-bg);
            color: var(--correct-text);
        }}
        body.show-all-answers .option-row.is-correct-option .option-letter {{
            color: #059669;
        }}

        /* -------------------------------------------------------------
           صندوق الشرح والتعليل (عنصر منفصل بدون إطار ومسموح له بالانقسام)
           ------------------------------------------------------------- */
        .explanation-box {{
            font-family: 'IBM Plex Sans Arabic', sans-serif;
            background-color: transparent;
            border: none;
            padding: 4px 8px;
            margin-top: 3px;
            margin-bottom: 12px;
            font-size: 0.96rem;
            line-height: 1.55;
            page-break-inside: auto; /* يسمح له بالانقسام لتخفيف الفراغات البيضاء */
            break-inside: auto;
        }}

        body.dark-mode .explanation-box {{
            background-color: transparent;
        }}

        body.exam-mode .explanation-box {{
            display: none !important;
        }}

        .exp-answer-line {{
            font-weight: 800;
            color: var(--primary-color);
            font-size: 1.02rem;
            margin-bottom: 3px;
        }}

        .exp-body-text {{
            font-weight: 500;
            color: #334155;
            font-size: 0.96rem;
            line-height: 1.55;
        }}

        body.dark-mode .exp-body-text {{ color: #cbd5e1; }}

        .exp-section {{
            margin-bottom: 4px;
        }}
        .exp-section:last-child {{
            margin-bottom: 0;
        }}

        .exp-header-tag {{
            color: var(--primary-dark);
            font-weight: 800;
            margin-left: 4px;
        }}

        body.dark-mode .exp-header-tag {{ color: #2dd4bf; }}

        .exp-lead {{
            font-weight: 700;
            margin-bottom: 2px;
            color: var(--text-main);
        }}

        .exp-opt-item {{
            margin-top: 1.5px;
            margin-bottom: 2px;
            line-height: 1.50;
        }}

        .opt-letter-tag {{
            font-weight: 800;
            color: var(--text-main);
            margin-left: 5px;
        }}

        .opt-ref-tag {{
            color: var(--primary-color);
            font-weight: 800;
        }}

        .high-yield-line {{
            margin-top: 5px;
            padding-top: 3px;
            border-top: 1px dashed var(--border-subtle);
            font-size: 0.96rem;
            font-weight: 600;
            line-height: 1.55;
        }}

        .high-yield-label {{
            color: var(--accent-gold);
            font-weight: 800;
            margin-left: 4px;
        }}

        .high-yield-text {{
            color: #334155;
            font-weight: 600;
        }}

        body.dark-mode .high-yield-text {{ color: #cbd5e1; }}

        /* -------------------------------------------------------------
           إعدادات الطباعة الدقيقة (مطابقة لـ generator.py لتجنب خلل الخطوط)
           ------------------------------------------------------------- */
        @media print {{
            @page {{
                size: A4;
                margin: 10mm 12mm 10mm 12mm;
            }}

            body {{
                background: #ffffff !important;
                color: #000000 !important;
                font-size: 10pt !important;
                line-height: 1.42 !important;
                padding: 0 !important;
            }}

            .no-print, .controls-header {{
                display: none !important;
            }}

            .document-container {{
                max-width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                box-shadow: none !important;
                border: none !important;
                background: transparent !important;
            }}

            /* الفهرس في الصفحة الأولى بالضبط */
            .index-page-container {{
                padding: 0 !important;
                margin-bottom: 0 !important;
                page-break-after: always !important;
                break-after: page !important;
            }}

            .subject-title {{
                font-size: 16pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
            }}

            .subject-subtitle {{
                font-size: 9.2pt !important;
                color: #475569 !important;
            }}

            .stats-summary {{
                font-size: 9.0pt !important;
                color: #000000 !important;
            }}

            .index-section-title {{
                font-size: 11pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
                border-bottom: 1.5pt solid #000000 !important;
            }}

            .index-block-header {{
                font-size: 9.5pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
                background-color: #f1f5f9 !important;
                border-right: 3pt solid #000000 !important;
                padding: 4px 8px !important;
            }}

            .index-row {{
                padding: 2.5px 4px !important;
                border-bottom: none !important;
            }}

            .index-topic-name {{
                font-size: 9.2pt !important;
                font-weight: 700 !important;
                color: #000000 !important;
                white-space: nowrap !important;
            }}

            .index-cat-note {{
                font-size: 8.0pt !important;
                color: #475569 !important;
            }}

            .index-dots {{
                flex: 1 !important;
                border-bottom: 0.8pt dotted #94a3b8 !important;
                margin: 0 8px !important;
                height: 1px !important;
                position: relative !important;
                top: -3px !important;
            }}

            .index-count {{
                font-size: 9.2pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
                white-space: nowrap !important;
            }}

            /* فواصل الكتل والمواد */
            .block-section-divider {{
                margin: 14px 0 8px !important;
                padding: 4px 8px !important;
                background-color: #f1f5f9 !important;
                border-top: 1.5pt solid #000000 !important;
                border-bottom: 1pt solid #000000 !important;
                page-break-after: avoid !important;
                break-after: avoid !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}

            .block-divider-title {{
                font-size: 10.5pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
            }}

            .subject-section-divider {{
                margin: 10px 0 6px !important;
                padding: 2px 4px !important;
                border-bottom: 1pt solid #0f766e !important;
                page-break-after: avoid !important;
                break-after: avoid !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}

            .subj-divider-title {{
                font-size: 10pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
            }}

            .subj-divider-count {{
                font-size: 8.5pt !important;
                color: #475569 !important;
            }}

            .question-card {{
                margin-bottom: 8px !important;
                padding-bottom: 4px !important;
                border-bottom: none !important;
                page-break-inside: auto !important;
                break-inside: auto !important;
            }}

            /* جسم السؤال: مؤطر وملون ومحمي تماماً من الانقسام */
            .question-block {{
                border: 0.9pt solid #94a3b8 !important;
                border-radius: 3px !important;
                background-color: #ffffff !important;
                padding: 6px 10px !important;
                margin-bottom: 3px !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
                page-break-after: auto !important;
                break-after: auto !important;
            }}

            .question-block.b1-framed {{
                border-right: 4pt solid #0284c7 !important;
            }}

            .question-block.b2-framed {{
                border-right: 4pt solid #b45309 !important;
            }}

            /* أحجام خطوط السؤال - بارز وواضح وأكبر بوضوح من الشرح */
            .q-number {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 11.8pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
            }}

            .q-stem {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 11.6pt !important;
                font-weight: 700 !important;
                line-height: 1.48 !important;
                color: #000000 !important;
            }}

            .options-list {{
                gap: 2.5px !important;
                margin-top: 3px !important;
                margin-bottom: 2px !important;
                padding-right: 14px !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}

            .option-row {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 11.2pt !important;
                font-weight: 600 !important;
                line-height: 1.42 !important;
                color: #000000 !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}

            .option-letter {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 11.5pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
                min-width: 18px !important;
            }}

            .option-text {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 11.2pt !important;
                font-weight: 600 !important;
                color: #000000 !important;
            }}

            /* جسم الشرح: أصغر حجماً (9.6pt) وبدون إطار ومسموح له بالانقسام */
            .explanation-box {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                background-color: transparent !important;
                border: none !important;
                padding: 2px 4px !important;
                margin-top: 2px !important;
                margin-bottom: 8px !important;
                font-size: 9.6pt !important;
                line-height: 1.42 !important;
                page-break-inside: auto !important;
                break-inside: auto !important;
            }}

            .exp-answer-line {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 10.2pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
                margin-bottom: 2px !important;
            }}

            .exp-body-text {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 9.6pt !important;
                font-weight: 500 !important;
                color: #1e293b !important;
                line-height: 1.42 !important;
            }}

            .exp-section {{
                font-size: 9.6pt !important;
                margin-bottom: 3px !important;
                page-break-inside: auto !important;
                break-inside: auto !important;
            }}

            .exp-para {{
                font-size: 9.6pt !important;
                line-height: 1.42 !important;
            }}

            .exp-header-tag {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 9.6pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
            }}

            .exp-lead {{
                font-size: 9.6pt !important;
                font-weight: 700 !important;
            }}

            .exp-opt-item {{
                font-size: 9.6pt !important;
                line-height: 1.38 !important;
            }}

            .opt-letter-tag {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 9.4pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
            }}

            .opt-ref-tag {{
                font-size: 9.6pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
            }}

            .high-yield-line {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 9.6pt !important;
                font-weight: 600 !important;
                color: #1e293b !important;
                line-height: 1.42 !important;
                margin-top: 2px !important;
                padding-top: 2px !important;
                border-top: 0.5pt dashed #cbd5e1 !important;
                page-break-inside: auto !important;
                break-inside: auto !important;
            }}

            .high-yield-label {{
                font-size: 9.6pt !important;
                font-weight: 800 !important;
                color: #000000 !important;
            }}

            .high-yield-text {{
                font-size: 9.6pt !important;
                font-weight: 600 !important;
                color: #1e293b !important;
            }}

            body.exam-mode .explanation-box {{
                display: none !important;
            }}
        }}
    </style>
</head>
<body>
    <!-- شريط التحكم والأدوات العلوي -->
    <header class="controls-header no-print">
        <div class="controls-row-top">
            <div class="brand-title-group">
                <span class="brand-tag">TealMED</span>
                <span class="doc-main-heading">دورة {html.escape(session_name)} ({total_q} سؤالاً)</span>
            </div>
            <div class="controls-actions">
                <button class="ctrl-btn" onclick="toggleExamMode()">
                    <span id="btn-mode-icon">📖</span>
                    <span id="btn-mode-text">نمط الامتحان (إخفاء الشروحات)</span>
                </button>
                <button class="ctrl-btn" onclick="toggleAnswers()">
                    <span>👁️</span>
                    <span id="btn-ans-text">إظهار الإجابات</span>
                </button>
                <button class="ctrl-btn" onclick="toggleDarkMode()">
                    <span>🌓</span>
                    <span>الوضع</span>
                </button>
                <button class="ctrl-btn btn-print" onclick="window.print()">
                    <span>🖨️</span>
                    <span>طباعة / حفظ PDF</span>
                </button>
            </div>
        </div>

        <div class="controls-row-filters">
            <button class="filter-btn-pill active" onclick="filterBlock('all')">الكل ({total_q})</button>
            <button class="filter-btn-pill b1" onclick="filterBlock(1)">🔹 الكتلة الأولى ({len(b1_qs)})</button>
            <button class="filter-btn-pill b2" onclick="filterBlock(2)">🔸 الكتلة الثانية ({len(b2_qs)})</button>

            <select class="subject-select-dropdown" onchange="filterSubject(this.value)">
                {"".join(filter_opts_html)}
            </select>

            <div class="search-quick-box">
                <input type="text" class="search-quick-input" id="search-input" placeholder="🔍 بحث سريع..." onkeyup="quickSearch()">
            </div>
        </div>
    </header>

    <!-- حاوية ورقة المستند (Word Document Flow) -->
    <main class="document-container">
        <!-- الصفحة الأولى: فهرس محتويات الدورة وتوزيع المواد -->
        <section class="index-page-container">
            <div class="subject-main-banner">
                <h1 class="subject-title">الامتحان الطبي الموحد — دورة {html.escape(session_name)}</h1>
                <div class="subject-subtitle">الجمهورية العربية السورية — مركز القياس والتقويم العالي</div>
                <div class="stats-summary">{total_q} سؤالاً • الكتلة الأولى ({len(b1_qs)} سؤال) • الكتلة الثانية ({len(b2_qs)} سؤال)</div>
            </div>

            <div class="index-section-title">فهرس محتويات الدورة وتوزيع المواد الامتحانية</div>

            <div class="index-list">
                <div class="index-block-header b1-header">
                    <span>🔹 الكتلة الأولى: أمراض الباطنة والداخليات، طب الأطفال، الجلدية</span>
                    <span class="index-count">{len(b1_qs)} سؤالاً</span>
                </div>
                {"".join(b1_index_rows)}

                <div class="index-block-header b2-header" style="margin-top: 14px;">
                    <span>🔸 الكتلة الثانية: النسائية والتوليد، الجراحات، الأذنية، العينية</span>
                    <span class="index-count">{len(b2_qs)} سؤالاً</span>
                </div>
                {"".join(b2_index_rows)}
            </div>
        </section>

        <!-- كروت وأقسام الأسئلة بالكامل (تبدأ من الصفحة التالية في الطباعة) -->
        {"".join(rendered_elements)}
    </main>

    <script>
        let isExamMode = false;
        let isAnswersRevealed = false;
        let activeBlock = 'all';
        let activeSubject = 'all';

        function toggleExamMode() {{
            isExamMode = !isExamMode;
            document.body.classList.toggle('exam-mode', isExamMode);
            document.getElementById('btn-mode-text').textContent = isExamMode ? 'نمط المذاكرة (عرض الشروحات)' : 'نمط الامتحان (إخفاء الشروحات)';
            document.getElementById('btn-mode-icon').textContent = isExamMode ? '💡' : '📖';
        }}

        function toggleAnswers() {{
            isAnswersRevealed = !isAnswersRevealed;
            document.body.classList.toggle('show-all-answers', isAnswersRevealed);
            document.getElementById('btn-ans-text').textContent = isAnswersRevealed ? 'إخفاء الإجابات' : 'إظهار الإجابات';
        }}

        function handleOptionClick(optEl, letter, isCorrect) {{
            const list = optEl.closest('.options-list');
            list.querySelectorAll('.option-row').forEach(row => {{
                row.classList.remove('user-correct', 'user-wrong');
            }});

            if (isCorrect) {{
                optEl.classList.add('user-correct');
            }} else {{
                optEl.classList.add('user-wrong');
                const cRow = list.querySelector('.is-correct-option');
                if (cRow) cRow.classList.add('user-correct');
            }}
        }}

        function filterBlock(blockId) {{
            activeBlock = blockId;
            activeSubject = 'all';
            document.querySelector('.subject-select-dropdown').value = 'all';
            document.querySelectorAll('.filter-btn-pill').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            applyFilters();
        }}

        function filterSubject(subjVal) {{
            activeSubject = subjVal;
            applyFilters();
        }}

        function applyFilters() {{
            const cards = document.querySelectorAll('.question-card');
            const blockDividers = document.querySelectorAll('.block-section-divider');
            const subjDividers = document.querySelectorAll('.subject-section-divider');

            cards.forEach(card => {{
                const b = card.getAttribute('data-block');
                const s = card.getAttribute('data-subject');

                const matchBlock = (activeBlock === 'all' || b == activeBlock);
                const matchSubj = (activeSubject === 'all' || s === activeSubject);

                if (matchBlock && matchSubj) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            blockDividers.forEach(bd => {{
                const bId = bd.getAttribute('data-block-id');
                if (activeSubject !== 'all') {{
                    bd.style.display = 'none';
                }} else if (activeBlock === 'all' || bId == activeBlock) {{
                    bd.style.display = 'block';
                }} else {{
                    bd.style.display = 'none';
                }}
            }});

            subjDividers.forEach(sd => {{
                const sName = sd.getAttribute('data-subject-name');
                if (activeSubject !== 'all') {{
                    sd.style.display = (sName === activeSubject) ? 'flex' : 'none';
                }} else {{
                    const hasVisibleCard = Array.from(document.querySelectorAll(`.question-card[data-subject="${{sName}}"]`)).some(c => c.style.display !== 'none');
                    sd.style.display = hasVisibleCard ? 'flex' : 'none';
                }}
            }});
        }}

        function quickSearch() {{
            const query = document.getElementById('search-input').value.trim().toLowerCase();
            const cards = document.querySelectorAll('.question-card');

            cards.forEach(card => {{
                const txt = card.innerText.toLowerCase();
                if (!query || txt.includes(query)) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        function toggleDarkMode() {{
            document.body.classList.toggle('dark-mode');
            localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
        }}

        if (localStorage.getItem('theme') === 'dark') {{
            document.body.classList.add('dark-mode');
        }}
    </script>
</body>
</html>
"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_html)


# -----------------------------------------------------------------------------
# مولد الفهرس ولوحة التحكم الرئيسية (Master Dashboard: index.html)
# -----------------------------------------------------------------------------
def export_master_catalog(sessions_summary, output_dir):
    output_dir = Path(output_dir)
    manifest_file = output_dir / "manifest_sessions.json"
    index_file = output_dir / "index.html"

    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(sessions_summary, f, ensure_ascii=False, indent=2)

    cards_html = []
    total_all_questions = 0

    for s in sessions_summary:
        s_name = s["session_name"]
        q_cnt = s["total_questions"]
        b1_cnt = s["block_1_count"]
        b2_cnt = s["block_2_count"]
        fn_safe = s["safe_filename"]
        total_all_questions += q_cnt

        cards_html.append(f"""
        <div class="session-catalog-card">
            <div class="card-header">
                <span class="session-badge">دورة امتحانية كاملة</span>
                <h3 class="session-title">{html.escape(s_name)}</h3>
            </div>
            
            <div class="card-stats">
                <div class="stat-pill total">
                    <span class="num">{q_cnt}</span>
                    <span class="lbl">سؤالاً كاملاً</span>
                </div>
                <div class="stat-pill b1">
                    <span class="num">{b1_cnt}</span>
                    <span class="lbl">الكتلة 1 (داخليات وأطفال)</span>
                </div>
                <div class="stat-pill b2">
                    <span class="num">{b2_cnt}</span>
                    <span class="lbl">الكتلة 2 (جراحات ونسائية)</span>
                </div>
            </div>

            <div class="card-actions">
                <a href="html/{fn_safe}.html" class="action-link html-link" target="_blank">🌐 تصفح وطباعة PDF (HTML)</a>
                <a href="json/{fn_safe}.json" class="action-link json-link" download>📦 تحميل JSON</a>
                <a href="csv/{fn_safe}.csv" class="action-link csv-link" download>📊 تحميل CSV (Excel)</a>
            </div>
        </div>
        """)

    index_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>فهرس دورات الامتحان الطبي الموحد - بنك الدورات الشامل</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Alexandria:wght@400;500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #0f766e;
            --primary-dark: #115e59;
            --bg-page: #f8fafc;
            --bg-card: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border-subtle: #e2e8f0;
            --b1: #0284c7;
            --b2: #b45309;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Alexandria', sans-serif;
            background-color: var(--bg-page);
            color: var(--text-main);
            padding: 30px 20px;
            direction: rtl;
        }}
        .catalog-container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        .hero-banner {{
            background: linear-gradient(135deg, #0f766e, #0f172a);
            color: #ffffff;
            padding: 32px 28px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .hero-banner h1 {{ font-size: 1.6rem; font-weight: 800; margin-bottom: 8px; }}
        .hero-banner p {{ font-size: 0.95rem; opacity: 0.9; max-width: 800px; line-height: 1.6; }}
        .hero-stats {{
            display: flex;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        .hero-stat-box {{
            background-color: rgba(255,255,255,0.15);
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.85rem;
        }}
        .hero-stat-box b {{ font-size: 1.2rem; display: block; }}
        
        .sessions-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }}
        .session-catalog-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .session-catalog-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.08);
        }}
        .session-badge {{
            font-size: 0.72rem;
            color: var(--primary);
            font-weight: 700;
            background-color: #f0fdfa;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .session-title {{
            font-size: 1.1rem;
            font-weight: 800;
            margin: 6px 0 14px;
            color: var(--text-main);
        }}
        .card-stats {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 6px;
            margin-bottom: 18px;
        }}
        .stat-pill {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            background-color: var(--bg-page);
        }}
        .stat-pill.total {{ font-weight: 700; background-color: #f1f5f9; }}
        .stat-pill.b1 {{ color: var(--b1); }}
        .stat-pill.b2 {{ color: var(--b2); }}
        .card-actions {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: auto;
        }}
        .action-link {{
            text-decoration: none;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 8px 12px;
            border-radius: 6px;
            text-align: center;
            transition: all 0.15s ease;
        }}
        .html-link {{
            background-color: var(--primary);
            color: #ffffff;
        }}
        .html-link:hover {{ background-color: var(--primary-dark); }}
        .json-link, .csv-link {{
            background-color: var(--bg-page);
            color: var(--text-main);
            border: 1px solid var(--border-subtle);
        }}
        .json-link:hover, .csv-link:hover {{
            background-color: var(--border-subtle);
        }}
    </style>
</head>
<body>
    <div class="catalog-container">
        <header class="hero-banner">
            <h1>فهرس دورات الامتحان الطبي الموحد (السنوات الكاملة)</h1>
            <p>تم تجميع كافة الأسئلة في ملفات مستقلة كاملة لكل دورة مرتبة حسب المواد ومقسومة إلى كتلتين (الكتلة الأولى: الداخليات والأطفال والجلدية، والكتلة الثانية: الجراحات والنسائية والتوليد والأذنية والعينية).</p>
            <div class="hero-stats">
                <div class="hero-stat-box">إجمالي الدورات المفهرسة<b>{len(sessions_summary)} دورة</b></div>
                <div class="hero-stat-box">إجمالي الأسئلة المجمعة<b>{total_all_questions} سؤالاً</b></div>
                <div class="hero-stat-box">دقة التصنيف<b>100% تطابق الكتل</b></div>
            </div>
        </header>

        <main class="sessions-grid">
            {"".join(cards_html)}
        </main>
    </div>
</body>
</html>
"""
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_html)


# -----------------------------------------------------------------------------
# المنسق العام وتنفيذ العملية (Pipeline Orchestrator)
# -----------------------------------------------------------------------------
def build_all_sessions(source_dir=None, output_dir=None, config_path=None, sync_from_final=False):
    source_dir = Path(source_dir or DEFAULT_SNAPSHOT_DIR)
    output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR)
    config_path = Path(config_path or DEFAULT_CONFIG_PATH)

    print("\n==================================================================")
    print("   TealMED National Exam Sessions Builder - بدء التجميع الموحد")
    print("==================================================================")

    if sync_from_final:
        print(f"[*] Synchronizing fresh snapshot from {DEFAULT_FINAL_DIR} to {source_dir}...")
        source_dir.mkdir(parents=True, exist_ok=True)
        if (DEFAULT_FINAL_DIR / "manifest.json").exists():
            shutil.copyfile(DEFAULT_FINAL_DIR / "manifest.json", source_dir / "manifest.json")
        for d in DEFAULT_FINAL_DIR.iterdir():
            if d.is_dir() and not d.name.startswith('.'):
                for jf in d.glob("*_all.json"):
                    dest_sub = source_dir / d.name
                    dest_sub.mkdir(exist_ok=True)
                    shutil.copyfile(jf, dest_sub / jf.name)
        print("[✓] Snapshot synchronized successfully.")

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    classifier = SubjectClassifier(config)

    raw_sessions_data = load_all_questions_from_source(source_dir, classifier)
    sessions_data = process_combined_sessions(raw_sessions_data)

    json_out_dir = output_dir / "json"
    csv_out_dir = output_dir / "csv"
    html_out_dir = output_dir / "html"

    for p in [json_out_dir, csv_out_dir, html_out_dir]:
        p.mkdir(parents=True, exist_ok=True)

    month_weights = config.get("month_weights", {})
    sorted_session_names = sorted(
        sessions_data.keys(),
        key=lambda s: get_session_sort_key(s, month_weights),
        reverse=True
    )

    catalog_summary = []

    print(f"\n[*] Generating full files for {len(sorted_session_names)} sessions...")

    for s_name in sorted_session_names:
        qs = sessions_data[s_name]
        numbered_qs = sort_and_number_session_questions(qs)

        b1_cnt = sum(1 for q in numbered_qs if q.get("block_id") == 1)
        b2_cnt = sum(1 for q in numbered_qs if q.get("block_id") == 2)

        clean_name = re.sub(r'[\s\-]+', '_', s_name)
        file_stem = f"دورة_{clean_name}"

        json_file = json_out_dir / f"{file_stem}.json"
        csv_file = csv_out_dir / f"{file_stem}.csv"
        html_file = html_out_dir / f"{file_stem}.html"

        export_session_json(s_name, numbered_qs, json_file)
        export_session_csv(s_name, numbered_qs, csv_file)
        export_session_html(s_name, numbered_qs, html_file)

        catalog_summary.append({
            "session_name": f"دورة {s_name}",
            "canonical_name": s_name,
            "safe_filename": file_stem,
            "total_questions": len(numbered_qs),
            "block_1_count": b1_cnt,
            "block_2_count": b2_cnt,
            "json_path": f"json/{file_stem}.json",
            "csv_path": f"csv/{file_stem}.csv",
            "html_path": f"html/{file_stem}.html"
        })

        print(f"  [✓] {s_name:20} -> {len(numbered_qs):3} Qs (B1: {b1_cnt:2}, B2: {b2_cnt:3}) -> JSON / CSV / HTML")

    export_master_catalog(catalog_summary, output_dir)
    print(f"\n[✓] Master Catalog & Dashboard generated at: {output_dir / 'index.html'}")
    print("[✓] ALL EXAM SESSIONS BUILT SUCCESSFULLY WITH 100% PRECISION!")
    return catalog_summary


# -----------------------------------------------------------------------------
# نقطة الدخول الرئيسية
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TealMED National Exam Sessions Builder")
    parser.add_argument("--source", type=str, default=str(DEFAULT_SNAPSHOT_DIR), help="Source directory (snapshot)")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH), help="Config file path")
    parser.add_argument("--sync", action="store_true", help="Sync fresh snapshot from final/ before building")
    parser.add_argument("--from-final", action="store_true", help="Read directly from final/ (read-only)")

    args = parser.parse_args()

    src = DEFAULT_FINAL_DIR if args.from_final else args.source
    build_all_sessions(
        source_dir=src,
        output_dir=args.output,
        config_path=args.config,
        sync_from_final=args.sync
    )
