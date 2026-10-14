#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TealMED PDF & HTML Medical Question Bank Generator (Premium Edition)
===================================================================
Produces high-density, beautifully styled HTML files optimized for direct
export to PDF (via Chrome/Edge Print -> Save as PDF).

Key Features:
- Dual execution: Batch convert all 10 final subjects or manual single-file picker
- Bold clinical explanation text (IBM Plex Sans Arabic 700) for maximum clarity
- Anti-orphan section headers: Topic title and its first question are physically linked
- Non-breaking question cards with compact print flow to fill pages without waste
- Balanced print-friendly margins (10mm top/bottom, 12mm left/right)
- Executive minimalist shading (soft tint, colored right accent border, single-color icons)
- Subtle high-transparency medical rhythm watermark on the left side to enliven RTL white space
- Dual interactive views: By Topics and By Sessions (Newest to Oldest)
"""

import os
import sys
import re
import csv
import json
import html
import glob
import shutil
import urllib.parse
import argparse
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# -----------------------------------------------------------------------------
# Academic Session Date Parser & Chronological Sorter
# -----------------------------------------------------------------------------
MONTH_WEIGHTS = {
    'كانون الثاني': 1,
    'شباط': 2,
    'آذار': 3,
    'نيسان': 4,
    'أيار': 5,
    'حزيران': 6,
    'تموز': 7,
    'آب': 8,
    'أيلول': 9,
    'تشرين الاول': 10,
    'تشرين الأول': 10,
    'تشرين الثاني': 11,
    'تشرين': 10.5,
    'كانون الاول': 12,
    'كانون الأول': 12,
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
}

def parse_date_score(date_str):
    if not date_str or not isinstance(date_str, str):
        return (0, 0)
    s = re.sub(r'[\u0640\s]+', ' ', date_str).strip()
    year_match = re.search(r'((?:19|20)\d\d)', s)
    year = int(year_match.group(1)) if year_match else 0
    m_score = 0
    for name, weight in MONTH_WEIGHTS.items():
        if name in s:
            m_score = max(m_score, weight)
    return (year, m_score)

# -----------------------------------------------------------------------------
# Color Themes Configuration (Minimalist, Executive, Single-Color Accents)
# -----------------------------------------------------------------------------
THEMES = {
    "cardio": {
        "name": "القلبية",
        "primary": "#8B1818",
        "primary_dark": "#5A0F0F",
        "primary_rgb": "139, 24, 24",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "gastro": {
        "name": "الهضمية",
        "primary": "#B45309",
        "primary_dark": "#78350F",
        "primary_rgb": "180, 83, 9",
        "accent_gold": "#D97706",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "pulmo": {
        "name": "الصدرية",
        "primary": "#0369A1",
        "primary_dark": "#073B5E",
        "primary_rgb": "3, 105, 161",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "nephro": {
        "name": "الكلية",
        "primary": "#5B21B6",
        "primary_dark": "#3B0764",
        "primary_rgb": "91, 33, 182",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "endo": {
        "name": "الغدية",
        "primary": "#A16207",
        "primary_dark": "#713F12",
        "primary_rgb": "161, 98, 7",
        "accent_gold": "#CA8A04",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "hema": {
        "name": "الدموية",
        "primary": "#9F1239",
        "primary_dark": "#4C0519",
        "primary_rgb": "159, 18, 57",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "rheuma": {
        "name": "المفصلية",
        "primary": "#0F766E",
        "primary_dark": "#134E4A",
        "primary_rgb": "15, 118, 110",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "peds": {
        "name": "الأطفال",
        "primary": "#0284C7",
        "primary_dark": "#0369A1",
        "primary_rgb": "2, 132, 199",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "obgyn": {
        "name": "النسائية والتوليد",
        "primary": "#9D174D",
        "primary_dark": "#700B34",
        "primary_rgb": "157, 23, 77",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "ent": {
        "name": "الأذنية",
        "primary": "#0D9488",
        "primary_dark": "#115E59",
        "primary_rgb": "13, 148, 136",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "plastic_onco": {
        "name": "الجراحة التجميلية والأورام",
        "primary": "#0D9488",
        "primary_dark": "#115E59",
        "primary_rgb": "13, 148, 136",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "plastic": {
        "name": "الجراحة التجميلية",
        "primary": "#0D9488",
        "primary_dark": "#115E59",
        "primary_rgb": "13, 148, 136",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "onco": {
        "name": "جراحة الأورام",
        "primary": "#4F46E5",
        "primary_dark": "#3730A3",
        "primary_rgb": "79, 70, 229",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "surgery01": {
        "name": "الجراحة 1",
        "primary": "#8B1818",
        "primary_dark": "#5A0F0F",
        "primary_rgb": "139, 24, 24",
        "accent_gold": "#B45309",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "orthopedics": {
        "name": "الجراحة العظمية",
        "primary": "#15803D",
        "primary_dark": "#14532D",
        "primary_rgb": "21, 128, 61",
        "accent_gold": "#D97706",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "urology": {
        "name": "الجراحة البولية",
        "primary": "#1E40AF",
        "primary_dark": "#1E3A8A",
        "primary_rgb": "30, 64, 175",
        "accent_gold": "#D97706",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "neurosurgery": {
        "name": "الجراحة العصبية",
        "primary": "#4338CA",
        "primary_dark": "#312E81",
        "primary_rgb": "67, 56, 202",
        "accent_gold": "#D97706",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "vascular_surgery": {
        "name": "جراحة الأوعية",
        "primary": "#991B1B",
        "primary_dark": "#7F1D1D",
        "primary_rgb": "153, 27, 27",
        "accent_gold": "#D97706",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    },
    "thoracic_surgery": {
        "name": "جراحة الصدر",
        "primary": "#0284C7",
        "primary_dark": "#075985",
        "primary_rgb": "2, 132, 199",
        "accent_gold": "#D97706",
        "bg_color": "#FCFCFC",
        "text_main": "#1E293B",
        "text_muted": "#64748B",
        "border_subtle": "#E2E8F0"
    }
}

def detect_theme(subject_name, filename=""):
    text = f"{subject_name} {filename}".lower()
    if any(k in text for k in ["عظم", "orthopedics", "ortho"]):
        return THEMES["orthopedics"]
    if any(k in text for k in ["عصب", "neurosurgery", "neuro"]):
        return THEMES["neurosurgery"]
    if any(k in text for k in ["بول", "urology", "urolog"]):
        return THEMES["urology"]
    if any(k in text for k in ["وعاء", "أوعية", "اوعية", "vascular"]):
        return THEMES["vascular_surgery"]
    if any(k in text for k in ["thoracic", "جراحة الصدر"]):
        return THEMES["thoracic_surgery"]
    if any(k in text for k in ["surgery01", "جراحة 1", "surgery1", "general_surgery", "جراحة عامة"]):
        return THEMES["surgery01"]
    if any(k in text for k in ["plastic_onco", "الجراحة التجميلية والأورام"]):
        return THEMES["plastic_onco"]
    if any(k in text for k in ["تجميل", "plastic"]):
        return THEMES["plastic"]
    if any(k in text for k in ["أورام", "اورام", "onco"]):
        return THEMES["onco"]
    if any(k in text for k in ["قلب", "cardio"]):
        return THEMES["cardio"]
    if any(k in text for k in ["هضم", "gastro"]):
        return THEMES["gastro"]
    if any(k in text for k in ["صدر", "pulmo"]):
        return THEMES["pulmo"]
    if any(k in text for k in ["كلي", "nephro", "renal"]):
        return THEMES["nephro"]
    if any(k in text for k in ["غد", "سكر", "endo"]):
        return THEMES["endo"]
    if any(k in text for k in ["دم", "hema"]):
        return THEMES["hema"]
    if any(k in text for k in ["مفصل", "رثي", "rheuma"]):
        return THEMES["rheuma"]
    if any(k in text for k in ["أطفال", "اطفال", "peds", "pediatric"]):
        return THEMES["peds"]
    if any(k in text for k in ["نسائي", "توليد", "obgyn", "obs", "gync", "gyne"]):
        return THEMES["obgyn"]
    if any(k in text for k in ["أذن", "اذن", "ent"]):
        return THEMES["ent"]
    return THEMES["cardio"]

def normalize_stem_punct(stem):
    if not stem or not isinstance(stem, str):
        return ""
    s = stem.strip()
    if not s:
        return ""
    # Strip any trailing colons, arabic colons, question marks, dots, or whitespace
    s = re.sub(r'[\s:：؟?.]+$', '', s)
    return s + ':'

def normalize_option_punct(text):
    if not text or not isinstance(text, str):
        return ""
    s = text.strip()
    if not s:
        return ""
    # Strip trailing dots, colons, arabic colons, or whitespace
    s = re.sub(r'[\s.:：]+$', '', s)
    return s + '.'

# -----------------------------------------------------------------------------
# Data Loader (Unified JSON and CSV Support)
# -----------------------------------------------------------------------------
def load_and_normalize(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # If CSV is selected, check if companion JSON exists in the same directory
    if path.suffix.lower() == '.csv':
        companion_json = path.with_suffix('.json')
        if companion_json.exists():
            return load_and_normalize(companion_json)

    # 1. Loading JSON
    if path.suffix.lower() == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        questions = []
        for idx, item in enumerate(raw_data, start=1):
            q_id = item.get('id') or f"q_{idx:03d}"
            subject = item.get('subject_name') or item.get('subject') or "المادة الطبية"
            topic = item.get('topic_name') or item.get('topic') or item.get('Chapter_or_Section') or "الموضوع العام"
            date = item.get('exam_period') or item.get('exam_date') or item.get('Exam_Date') or ""
            stem = normalize_stem_punct(item.get('title') or item.get('Question_Text') or item.get('stem') or "")
            
            raw_opts = item.get('options') or []
            options = []
            correct_letter = item.get('correct_option') or ""
            
            for opt in raw_opts:
                if isinstance(opt, dict):
                    letter = opt.get('letter', '').strip().upper()
                    text = normalize_option_punct(opt.get('text', ''))
                    is_correct = bool(opt.get('is_correct', False))
                    if is_correct and not correct_letter:
                        correct_letter = letter
                    options.append({
                        'letter': letter,
                        'text': text,
                        'is_correct': is_correct
                    })
            
            explanation = item.get('explanation') or ""
            high_yield = item.get('high_yield_note') or ""
            
            if not high_yield and "HIGH YIELD" in explanation.upper():
                hy_match = re.search(r'(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية)\s*:\s*(.*?)(?=(?:EXPLANATION|الشرح|التعليل)\s*:|$)', explanation, re.DOTALL | re.IGNORECASE)
                if hy_match:
                    high_yield = hy_match.group(1).strip()
            
            questions.append({
                'id': q_id,
                'subject': subject.strip(),
                'topic': topic.strip(),
                'date': date.strip(),
                'stem': stem.strip(),
                'options': options,
                'correct_letter': correct_letter.strip().upper(),
                'explanation': explanation.strip(),
                'high_yield_note': high_yield.strip()
            })
        return questions

    # 2. Loading CSV
    elif path.suffix.lower() == '.csv':
        encodings = ['utf-8-sig', 'utf-8', 'cp1256']
        rows = None
        for enc in encodings:
            try:
                with open(path, 'r', encoding=enc) as f:
                    rows = list(csv.DictReader(f))
                    break
            except Exception:
                continue

        if not rows:
            raise ValueError(f"Could not decode CSV file '{path.name}'.")

        questions = []
        for idx, row in enumerate(rows, start=1):
            q_id = row.get('Question_ID') or f"q_{idx:03d}"
            subject = row.get('Medical_Subject') or "المادة الطبية"
            topic = row.get('Chapter_or_Section') or "الموضوع العام"
            date = row.get('Exam_Date') or ""
            stem = normalize_stem_punct(row.get('Question_Text') or "")
            explanation = row.get('Explanation') or ""
            high_yield = row.get('High_Yield_Note') or ""

            correct_ans = normalize_option_punct(row.get('Correct_Answer') or "")
            wrong_answers = [
                normalize_option_punct(row.get(f'Wrong_Answer_{i}') or "")
                for i in range(1, 6)
                if (row.get(f'Wrong_Answer_{i}') or "").strip()
            ]

            options = []
            letters = ['A', 'B', 'C', 'D', 'E']
            all_opts = [correct_ans] + wrong_answers
            import random
            random.seed(idx)
            random.shuffle(all_opts)

            correct_letter = ""
            for l, txt in zip(letters, all_opts):
                is_c = (txt == correct_ans)
                if is_c:
                    correct_letter = l
                options.append({
                    'letter': l,
                    'text': txt,
                    'is_correct': is_c
                })

            questions.append({
                'id': q_id,
                'subject': subject.strip(),
                'topic': topic.strip(),
                'date': date.strip(),
                'stem': stem.strip(),
                'options': options,
                'correct_letter': correct_letter,
                'explanation': explanation.strip(),
                'high_yield_note': high_yield.strip()
            })
        return questions

    raise ValueError(f"Unsupported file type: {path.suffix}")

# -----------------------------------------------------------------------------
# Explanation Formatter (Executive Shading, Bold Typography, Clean Structure)
# -----------------------------------------------------------------------------
def format_explanation_html(q, theme):
    raw_exp = q.get('explanation') or ""
    high_yield = q.get('high_yield_note') or ""
    correct_letter = q.get('correct_letter') or ""
    
    correct_text = ""
    for opt in q.get('options', []):
        if opt.get('letter') == correct_letter:
            correct_text = opt.get('text', '')
            break

    # 1. Correct Answer line (clean text, no badge, no icon, IBM Plex Sans Arabic)
    correct_line = ""
    if correct_letter:
        c_label = f"الإجابة الصحيحة: {correct_letter}"
        if correct_text:
            c_label += f" — {correct_text}"
        correct_line = f'<div class="exp-answer-line">{html.escape(c_label)}</div>'

    # 2. Format explanation text naturally with BOLD body text, structured sections & Bidi isolation
    clean_exp = raw_exp.strip()
    
    section_patterns = [
        (r'(?:-\s*)?(التعليل\s+السريري|التعليل|الشرح)\s*[:：]', 'exp-clinical', r'\1:'),
        (r'(?:-\s*)?(الخيارات\s+الأخرى|تفنيد\s+الخيارات)\s*[:：]', 'exp-other-opts', r'\1:'),
        (r'(?:-\s*)?(ترميم\s+امتحاني|الترميم\s+الشامل)\s*[:：]', 'exp-tarmim', r'\1:'),
        (r'(?:-\s*)?(ملاحظة\s+سريرية\s*\(Clinical\s+Error\s+Flag\)|CLINICAL\s+ERROR\s+FLAG)\s*[:：]', 'exp-flag', r'\1:'),
        (r'(?:-\s*)?(ملاحظة\s+\w+|ملاحظة)\s*[:：]', 'exp-note', r'\1:')
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
            sec_header = headers[i][3]
            sec_text = clean_exp[start_content:end_content].strip()
            sections.append((sec_cls, sec_header, sec_text))
            
    html_parts = []
    for cls, hdr, body in sections:
        part = f'<div class="exp-section {cls}">'
        if hdr:
            part += f'<b class="exp-header-tag">{html.escape(hdr)}</b> '
            
        # Format options as dedicated block items in 'exp-other-opts' or if options list detected
        if cls == 'exp-other-opts' or re.search(r'(?:^|\n)\s*[A-F][:)ـ.]', body):
            opt_matches = list(re.finditer(r'(?:(?<=[\n.؛;!])|^)\s*(?<!\()([A-F])[:.)ـ]\s*', body))
            if opt_matches:
                pre_opt_text = body[:opt_matches[0].start()].strip()
                if pre_opt_text:
                    part += f'<div class="exp-lead">{html.escape(pre_opt_text)}</div>'
                    
                for idx in range(len(opt_matches)):
                    opt_tag = opt_matches[idx].group(1)
                    opt_letter = opt_tag[0].upper()
                    opt_start = opt_matches[idx].end()
                    opt_end = opt_matches[idx+1].start() if idx + 1 < len(opt_matches) else len(body)
                    opt_txt = body[opt_start:opt_end].strip()
                    escaped_txt = html.escape(opt_txt)
                    escaped_txt = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', r'\1.&rlm;\2', escaped_txt)
                    escaped_txt = re.sub(
                        r'(\(الخيار\s+[A-F]\)|الخيار\s+[A-F])',
                        r'<span class="opt-ref-tag">\1</span>',
                        escaped_txt
                    )
                    part += f'<div class="exp-opt-item"><span class="opt-letter-tag">{opt_letter}.</span> <span class="exp-opt-desc">{escaped_txt}</span></div>'
            else:
                part += html.escape(body)
        else:
            escaped_body = html.escape(body)
            # Highlight references like (الخيار E) or الخيار A with bidi isolation
            escaped_body = re.sub(
                r'(\(الخيار\s+[A-F]\)|الخيار\s+[A-F])',
                r'<bdi class="opt-ref-tag">\1</bdi>',
                escaped_body
            )
            # Handle paragraphs
            paras = [p.strip() for p in re.split(r'\n\s*\n', escaped_body) if p.strip()]
            if len(paras) > 1:
                part += ''.join(f'<div class="exp-para">{p}</div>' for p in paras)
            else:
                part += escaped_body
                
        part += '</div>'
        html_parts.append(part)
        
    exp_body_html = f'<div class="exp-body-text">{" ".join(html_parts)}</div>' if html_parts else ""

    # 3. High-Yield Note: "الفكرة من السؤال: [الملاحظة]" (merged cleanly inside explanation box)
    high_yield_html = ""
    if high_yield:
        clean_hy = re.sub(r'^(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|الفكرة\s+من\s+السؤال)\s*[:：]\s*', '', high_yield, flags=re.IGNORECASE).strip()
        high_yield_html = f"""
        <div class="high-yield-line">
            <b class="high-yield-label">الفكرة من السؤال:</b>
            <span class="high-yield-text">{html.escape(clean_hy)}</span>
        </div>"""

    return f"""
    <div class="explanation-box">
        {correct_line}
        {exp_body_html}
        {high_yield_html}
    </div>"""

def render_question_card(q_num, q, group_by, theme):
    badge_text = q.get('topic', '') if group_by == 'session' else q.get('date', '')
    badge_html = ""
    if badge_text:
        badge_html = f'<span class="q-date-badge">{html.escape(badge_text)}</span>'

    opts_html = ""
    for opt_item in q.get('options', []):
        let = opt_item.get('letter', '')
        txt = opt_item.get('text', '')
        opts_html += f"""
            <div class="option-row">
                <span class="option-letter">{let}.</span>
                <span class="option-text">{html.escape(txt)}</span>
            </div>"""

    exp_html = format_explanation_html(q, theme)

    q_year, _ = parse_date_score(q.get('date', ''))
    year_attr = str(q_year) if q_year > 1900 else ""

    return f"""
    <div class="question-card" id="{q['id']}" data-year="{year_attr}">
        <div class="question-block">
            <div class="question-header">
                <div class="q-stem-container">
                    <span class="q-number">{q_num}.</span>
                    <span class="q-stem">{html.escape(q['stem'])}</span>
                </div>
                {badge_html}
            </div>
            <div class="options-list">
                {opts_html}
            </div>
        </div>
        {exp_html}
    </div>"""

# -----------------------------------------------------------------------------
# Main HTML Document Generator
# -----------------------------------------------------------------------------
def generate_html_document(questions, output_path, group_by='topic', custom_title=None, switch_link=None):
    if not questions:
        print("[!] No questions provided.")
        return

    first_sub = questions[0].get('subject') or "المادة الطبية"
    theme = detect_theme(first_sub, os.path.basename(output_path))
    doc_title = custom_title or f"بنك الأسئلة - {first_sub}"

    total_questions = len(questions)
    
    # Calculate overall years range
    all_years = []
    for q in questions:
        y, m = parse_date_score(q.get('date', ''))
        if y > 2000:
            all_years.append(y)
    
    year_range_str = "جميع الدورات"
    if all_years:
        min_y, max_y = min(all_years), max(all_years)
        year_range_str = f"{min_y} - {max_y}" if min_y != max_y else f"{min_y}"

    group_meta = []

    if group_by == 'session':
        sessions_dict = {}
        for q in questions:
            sess = (q.get('date') or "").strip() or "دورات غير محددة"
            if sess not in sessions_dict:
                sessions_dict[sess] = []
            sessions_dict[sess].append(q)

        sorted_session_names = sorted(sessions_dict.keys(), key=parse_date_score, reverse=True)
        for idx, s_name in enumerate(sorted_session_names, start=1):
            s_qs = sessions_dict[s_name]
            s_id = f"session-{idx}"
            sub_topics = sorted(list(set(q.get('topic') for q in s_qs if q.get('topic'))))
            topic_count_str = f"{len(sub_topics)} مواضيع" if len(sub_topics) > 1 else (sub_topics[0] if sub_topics else "موضوع عام")
            s_title = s_name if (s_name.startswith("دورة") or s_name == "دورات غير محددة") else f"دورة {s_name}"
            s_year, _ = parse_date_score(s_name)
            s_year_val = str(s_year) if s_year > 1900 else ""

            group_meta.append({
                'id': s_id,
                'name': s_name,
                'title_display': s_title,
                'count': len(s_qs),
                'range': topic_count_str,
                'year': s_year_val,
                'questions': s_qs
            })
            
        index_section_title = "فهرس الدورات الامتحانية (مرتبة من الأحدث إلى الأقدم)"
        subtitle_str = "مرتب حسب الدورات الامتحانية"
        stats_summary_str = f"{total_questions} سؤال • {len(group_meta)} دورة امتحانية • {year_range_str}"

    else:
        topics_dict = {}
        for q in questions:
            top = (q.get('topic') or "").strip() or "الموضوع العام"
            if top not in topics_dict:
                topics_dict[top] = []
            topics_dict[top].append(q)

        # Sort questions chronologically from NEWEST to OLDEST within each topic
        for top in topics_dict:
            topics_dict[top].sort(key=lambda q: parse_date_score(q.get('date', '')), reverse=True)

        for idx, (t_name, t_qs) in enumerate(topics_dict.items(), start=1):
            t_id = f"topic-{idx}"
            t_years = [parse_date_score(q.get('date', ''))[0] for q in t_qs if parse_date_score(q.get('date', ''))[0] > 1900]
            t_range = f"{min(t_years)} - {max(t_years)}" if t_years else "دورات مجمعة"
            t_years_str = " ".join(sorted(set(str(y) for y in t_years), reverse=True))
            group_meta.append({
                'id': t_id,
                'name': t_name,
                'title_display': t_name,
                'count': len(t_qs),
                'range': t_range,
                'year': t_years_str,
                'questions': t_qs
            })

        index_section_title = "فهرس المواضيع والتصنيفات"
        subtitle_str = "مرتب حسب المواضيع"
        stats_summary_str = f"{total_questions} سؤال • {len(group_meta)} مواضيع • {year_range_str}"

    if group_by == 'session':
        filter_label_text = "الدورة:"
        select_default_text = f"جميع الدورات (الكل - {total_questions} سؤال)"
        initial_btn_text = "تحميل الدورة المحددة (HTML)"

        year_to_sessions = {}
        for gm in group_meta:
            y = gm.get('year') or 'غير محدد'
            year_to_sessions.setdefault(y, []).append(gm)

        item_options_html = f'                    <option value="all">{select_default_text}</option>\n'
        for y in sorted(year_to_sessions.keys(), reverse=True):
            y_sessions = year_to_sessions[y]
            total_y_qs = sum(s['count'] for s in y_sessions)
            item_options_html += f'                    <optgroup label="دورات سنة {y} ({total_y_qs} سؤال)">\n'
            item_options_html += f'                        <option value="year_{y}">📅 جميع دورات {y} ({total_y_qs} سؤال)</option>\n'
            for s in y_sessions:
                item_options_html += f'                        <option value="{s["id"]}">{html.escape(s["title_display"])} ({s["count"]} سؤال)</option>\n'
            item_options_html += f'                    </optgroup>\n'
    else:
        filter_label_text = "التصنيف:"
        select_default_text = f"جميع التصنيفات (الكل - {total_questions} سؤال)"
        initial_btn_text = "تحميل التصنيف المحدد (HTML)"
        item_options_html = f'                    <option value="all">{select_default_text}</option>\n'
        for gm in group_meta:
            item_options_html += f'                    <option value="{gm["id"]}">{html.escape(gm["name"])} ({gm["count"]} سؤال)</option>\n'

    switch_btn_html = ""
    if switch_link:
        switch_btn_html = f'<a href="{switch_link["href"]}" class="btn btn-switch" style="text-decoration: none;">{switch_link["label"]}</a>'

    html_out = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(doc_title)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Alexandria:wght@400;500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700;800&family=Noto+Sans+Arabic:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-color: {theme['primary']};
            --primary-dark: {theme['primary_dark']};
            --primary-rgb: {theme['primary_rgb']};
            --accent-gold: {theme['accent_gold']};
            --text-main: #1E293B;
            --text-muted: #64748B;
            --border-subtle: #E2E8F0;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Alexandria', 'IBM Plex Sans Arabic', sans-serif;
            background-color: #ffffff;
            color: var(--text-main);
            line-height: 1.45;
            font-size: 0.95rem;
            padding-bottom: 30px;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
            position: relative;
        }}

        /* Subtle High-Transparency Decorative Rhythm on the Left Margin */
        .left-watermark-pulse {{
            position: fixed;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            width: 40px;
            height: 70vh;
            color: var(--primary-color);
            opacity: 0.045;
            pointer-events: none;
            z-index: 0;
        }}

        /* Minimalist Controls Bar */
        .controls-header {{
            background-color: #ffffff;
            border-bottom: 1px solid var(--border-subtle);
            padding: 10px 24px;
            position: sticky;
            top: 0;
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .header-title-container h1 {{
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--primary-dark);
        }}

        .header-actions-container {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .filter-wrapper {{
            display: flex;
            align-items: center;
            gap: 6px;
            background: #f8fafc;
            border: 1.5px solid var(--primary-color);
            border-radius: 4px;
            padding: 3px 8px;
        }}

        .filter-label {{
            font-size: 0.80rem;
            font-weight: 700;
            color: var(--primary-dark);
            white-space: nowrap;
        }}

        .filter-select {{
            font-family: inherit;
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--text-main);
            background: transparent;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 2px 4px;
        }}

        .filter-select:focus {{
            outline: none;
        }}

        .btn-group {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .btn-download {{
            background: #059669 !important;
            color: #ffffff !important;
            border-color: #059669 !important;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
        }}

        .btn-download:hover {{
            background: #047857 !important;
            border-color: #047857 !important;
        }}

        .filter-hidden {{
            display: none !important;
        }}

        .index-row-wrapper {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px dotted var(--border-subtle);
            transition: background 0.15s ease;
        }}

        .index-row-wrapper:hover {{
            background-color: #f8fafc;
        }}

        .index-row-wrapper .index-row {{
            flex: 1;
            border-bottom: none;
        }}

        .btn-index-download {{
            font-family: inherit;
            font-size: 0.74rem;
            font-weight: 700;
            padding: 3px 8px;
            background: #ecfdf5;
            color: #047857;
            border: 1px solid #a7f3d0;
            border-radius: 4px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.15s ease;
            margin-left: 6px;
        }}

        .btn-index-download:hover {{
            background: #059669;
            color: #ffffff;
            border-color: #059669;
        }}

        .btn {{
            font-family: inherit;
            font-weight: 600;
            font-size: 0.82rem;
            padding: 5px 12px;
            border: 1px solid var(--border-subtle);
            background: #ffffff;
            color: var(--text-main);
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .btn:hover {{
            background: #f8fafc;
            border-color: #cbd5e1;
        }}

        .btn-active {{
            background: var(--primary-color) !important;
            color: #ffffff !important;
            border-color: var(--primary-color) !important;
        }}

        .btn-print {{
            background: #0f172a;
            color: #ffffff;
            border-color: #0f172a;
        }}

        .btn-switch {{
            background: #f8fafc;
            color: var(--primary-color) !important;
            border-color: var(--primary-color) !important;
            font-weight: 700;
        }}

        .btn-switch:hover {{
            background: var(--primary-color) !important;
            color: #ffffff !important;
        }}

        .btn-print:hover {{
            background: #1e293b;
        }}

        .container {{
            max-width: 880px;
            margin: 16px auto;
            padding: 0 16px;
            position: relative;
            z-index: 1;
        }}

        /* -------------------------------------------------------------
           FIRST PAGE: Minimalist Table of Contents (Single Column)
           ------------------------------------------------------------- */
        .index-page-container {{
            padding: 24px 0;
            margin-bottom: 30px;
            page-break-after: always;
            break-after: page;
        }}

        .subject-main-banner {{
            text-align: center;
            padding-bottom: 16px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-subtle);
        }}

        .subject-title {{
            font-size: 1.75rem;
            color: var(--primary-dark);
            font-weight: 800;
            margin-bottom: 4px;
        }}

        .subject-subtitle {{
            font-size: 0.88rem;
            color: var(--text-muted);
            font-weight: 500;
        }}

        .stats-summary {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 6px;
            font-weight: 600;
        }}

        .index-section-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--primary-dark);
            margin-bottom: 14px;
            padding-bottom: 6px;
            border-bottom: 2px solid var(--primary-color);
            display: inline-block;
        }}

        .index-list {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .index-row {{
            text-decoration: none;
            color: var(--text-main);
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 7px 10px;
            border-bottom: 1px dotted var(--border-subtle);
            transition: background 0.15s ease;
        }}

        .index-row:hover {{
            background-color: #f8fafc;
            color: var(--primary-color);
        }}

        .index-topic-name {{
            font-size: 0.92rem;
            font-weight: 600;
        }}

        .index-topic-meta {{
            font-size: 0.78rem;
            color: var(--text-muted);
            display: flex;
            gap: 10px;
            align-items: center;
        }}

        .index-count {{
            font-weight: 700;
            color: var(--primary-color);
        }}

        /* -------------------------------------------------------------
           SECTION TITLE & FIRST QUESTION ANCHOR (No Orphans Ever!)
           ------------------------------------------------------------- */
        .topic-container {{
            margin-bottom: 24px;
        }}

        .topic-header-anchor {{
            page-break-inside: auto;
            break-inside: auto;
        }}

        .topic-header {{
            text-align: center;
            margin-top: 24px;
            margin-bottom: 14px;
            page-break-after: avoid;
            break-after: avoid;
            scroll-margin-top: 70px;
        }}

        .topic-title-text {{
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--primary-color);
            display: inline-block;
            padding-bottom: 2px;
            border-bottom: 2px solid var(--primary-color);
        }}

        .topic-counter {{
            font-size: 0.76rem;
            color: var(--text-muted);
            font-weight: 600;
            display: block;
            margin-top: 3px;
        }}

        /* -------------------------------------------------------------
           QUESTION CARD (Compact Flow, Elegant Typography)
           ------------------------------------------------------------- */
        .question-card {{
            background: transparent;
            border: none;
            box-shadow: none;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid #f1f5f9;
        }}

        .question-block {{
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .question-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 8px;
            margin-bottom: 8px;
        }}

        .q-stem-container {{
            display: flex;
            align-items: flex-start;
            gap: 10px;
            flex: 1;
        }}

        .q-number {{
            font-weight: 800;
            color: var(--primary-color);
            font-size: 1.22rem;
            flex-shrink: 0;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}

        .q-stem {{
            font-weight: 700;
            color: #0f172a;
            font-size: 1.20rem;
            line-height: 1.66;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}

        .q-date-badge {{
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-muted);
            white-space: nowrap;
            flex-shrink: 0;
            margin-top: 4px;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}

        .options-list {{
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 8px;
            padding-right: 22px;
        }}

        .option-row {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            font-size: 1.15rem;
            line-height: 1.60;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}

        .option-letter {{
            font-weight: 800;
            color: var(--primary-color);
            flex-shrink: 0;
            min-width: 22px;
            font-size: 1.18rem;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}

        .option-text {{
            color: #1e293b;
            font-weight: 700;
            font-size: 1.15rem;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}

        /* -------------------------------------------------------------
           EXPLANATION BOX (Full Border Encompassing Box, Bold Typography)
           ------------------------------------------------------------- */
        .explanation-box {{
            font-family: 'IBM Plex Sans Arabic', sans-serif;
            background-color: transparent;
            border: 1.5px solid var(--primary-color);
            border-radius: 4px;
            margin-top: 8px;
            padding: 10px 14px;
            font-size: 1.08rem;
            line-height: 1.68;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .exp-answer-line {{
            font-family: 'IBM Plex Sans Arabic', sans-serif;
            font-weight: 800;
            color: var(--primary-color);
            font-size: 1.12rem;
            margin-bottom: 5px;
        }}

        .exp-body-text {{
            font-family: 'IBM Plex Sans Arabic', sans-serif;
            color: #0f172a;
            font-weight: 700; /* BOLD as requested */
            font-size: 1.08rem;
            line-height: 1.68;
            margin-top: 4px;
        }}

        .exp-section {{
            margin-bottom: 6px;
        }}
        .exp-section:last-child {{
            margin-bottom: 0;
        }}

        .exp-header-tag {{
            color: var(--primary-dark);
            font-weight: 800;
            margin-left: 4px;
        }}

        .exp-flag .exp-header-tag {{
            color: #dc2626;
        }}

        .exp-lead {{
            margin-bottom: 3px;
            font-weight: 700;
        }}

        .exp-opt-item {{
            display: block;
            margin-top: 1.5px;
            margin-bottom: 2px;
            padding-right: 0;
            line-height: 1.58;
            unicode-bidi: isolate;
        }}

        .opt-letter-tag {{
            color: #1e293b;
            font-weight: 800;
            margin-left: 6px;
            font-size: 1.0rem;
        }}

        .exp-opt-desc {{
            unicode-bidi: isolate;
        }}

        .opt-ref-tag {{
            color: #1e293b;
            font-weight: 800;
        }}

        .exp-para {{
            margin-top: 5px;
            margin-bottom: 5px;
            line-height: 1.68;
        }}

        /* HIGH-YIELD NOTE (Merged seamlessly inside explanation box) */
        .high-yield-line {{
            font-family: 'IBM Plex Sans Arabic', sans-serif;
            margin-top: 7px;
            font-size: 1.08rem;
            line-height: 1.68;
            font-weight: 700;
        }}

        .high-yield-label {{
            font-weight: 800;
            color: var(--accent-gold);
            margin-left: 4px;
        }}

        .high-yield-text {{
            color: #1e293b;
            font-weight: 700;
        }}

        /* Exam Mode (Hides Explanation) */
        .exam-mode .explanation-box {{
            display: none !important;
        }}

        /* -------------------------------------------------------------
           PRINT STYLING (@media print): Balanced Margins, Compact Filling
           ------------------------------------------------------------- */
        @media print {{
            @page {{
                size: A4;
                margin: 10mm 12mm 10mm 12mm; /* Balanced print-friendly margins */
            }}

            body {{
                background: #ffffff !important;
                color: #000000 !important;
                font-size: 10.0pt !important;
                line-height: 1.42 !important;
                padding-bottom: 0 !important;
            }}

            .left-watermark-pulse {{
                position: fixed !important;
                left: 2mm !important;
                top: 50% !important;
                transform: translateY(-50%) !important;
                width: 32px !important;
                height: 70vh !important;
                opacity: 0.035 !important;
                color: var(--primary-color) !important;
                pointer-events: none !important;
                z-index: -1 !important;
            }}

            .no-print, .controls-header, .filter-hidden, .btn-index-download {{
                display: none !important;
            }}

            .container {{
                max-width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }}

            .index-page-container {{
                padding: 10px 0 !important;
                page-break-after: always !important;
                break-after: page !important;
            }}

            .subject-title {{
                font-size: 16pt !important;
            }}

            .topic-container {{
                margin-bottom: 14px !important;
            }}

            .topic-header-anchor {{
                page-break-inside: auto !important;
                break-inside: auto !important;
            }}

            .topic-header {{
                margin-top: 14px !important;
                margin-bottom: 6px !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
                page-break-after: avoid !important;
                break-after: avoid !important;
            }}

            .topic-title-text {{
                font-size: 11pt !important;
            }}

            .question-card {{
                margin-bottom: 8px !important;
                padding-bottom: 6px !important;
                border-bottom: 1px solid #e2e8f0 !important;
                page-break-inside: auto !important;
                break-inside: auto !important;
            }}

            .question-block {{
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}

            .question-header {{
                page-break-inside: avoid !important;
                break-inside: avoid !important;
                page-break-after: avoid !important;
                break-after: avoid !important;
            }}

            .q-stem-container {{
                gap: 6px !important;
            }}

            .q-number {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 11.6pt !important;
                font-weight: 800 !important;
            }}

            .q-stem {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 11.6pt !important;
                font-weight: 700 !important;
                line-height: 1.48 !important;
            }}

            .q-date-badge {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 8.0pt !important;
                margin-top: 2px !important;
            }}

            .options-list {{
                page-break-inside: avoid !important;
                break-inside: avoid !important;
                gap: 3px !important;
                margin-bottom: 5px !important;
                padding-right: 16px !important;
            }}

            .option-row {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 11.5pt !important;
                font-weight: 700 !important;
                line-height: 1.44 !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}

            .option-letter {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-weight: 800 !important;
                font-size: 11.6pt !important;
                min-width: 20px !important;
            }}

            .option-text {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-weight: 700 !important;
                font-size: 11.5pt !important;
            }}

            .explanation-box {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                background-color: transparent !important;
                border: 0.9pt solid var(--primary-color) !important;
                border-radius: 3px !important;
                margin-top: 4px !important;
                padding: 7px 11px !important;
                font-size: 10.5pt !important;
                line-height: 1.46 !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}

            .exp-answer-line {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-weight: 800 !important;
                color: var(--primary-color) !important;
                font-size: 10.6pt !important;
                margin-bottom: 4px !important;
            }}

            .exp-body-text {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                font-size: 10.5pt !important;
                font-weight: 700 !important; /* BOLD in print */
                color: #0f172a !important;
                line-height: 1.46 !important;
                margin-top: 3px !important;
            }}

            .exp-section {{
                margin-bottom: 4px !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}

            .exp-opt-item {{
                margin-top: 1px !important;
                margin-bottom: 1.5px !important;
                padding-right: 0 !important;
                line-height: 1.40 !important;
            }}

            .opt-letter-tag {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                color: #0f172a !important;
                font-size: 10.0pt !important;
                font-weight: 800 !important;
                margin-left: 5px !important;
            }}

            .opt-ref-tag {{
                color: #0f172a !important;
                font-weight: 800 !important;
            }}

            .high-yield-line {{
                font-family: 'IBM Plex Sans Arabic', sans-serif !important;
                margin-top: 4px !important;
                font-size: 10.5pt !important;
                line-height: 1.46 !important;
                font-weight: 700 !important;
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}

            .high-yield-label {{
                color: var(--accent-gold) !important;
                font-weight: 800 !important;
            }}

            .high-yield-text {{
                color: #0f172a !important;
                font-weight: 700 !important;
            }}
        }}
    </style>
</head>
<body class="study-mode">

    <!-- Subtle Left Margin Rhythm Accent (Watermark) -->
    <div class="left-watermark-pulse" aria-hidden="true">
        <svg viewBox="0 0 100 800" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M50 0 V240 L40 260 L60 285 L32 315 L68 345 L50 365 V500 L42 518 L58 538 L50 555 V800" opacity="0.35" />
            <circle cx="50" cy="240" r="3" fill="currentColor" opacity="0.4"/>
            <circle cx="50" cy="500" r="3" fill="currentColor" opacity="0.4"/>
            <path d="M36 140 H64 M50 126 V154" stroke-width="2.5" opacity="0.35"/>
            <path d="M36 660 H64 M50 646 V674" stroke-width="2.5" opacity="0.35"/>
        </svg>
    </div>

    <div class="controls-header no-print">
        <div class="header-title-container">
            <h1>{html.escape(doc_title)}</h1>
        </div>
        <div class="header-actions-container">
            <div class="filter-wrapper">
                <label for="itemFilter" class="filter-label">{filter_label_text}</label>
                <select id="itemFilter" class="filter-select" onchange="filterByItem(this.value)">
{item_options_html}
                </select>
            </div>
            <div class="btn-group">
                {switch_btn_html}
                <button id="btnStudy" class="btn btn-active" onclick="setMode('study')">
                    وضع الدراسة
                </button>
                <button id="btnExam" class="btn" onclick="setMode('exam')">
                    وضع الاختبار
                </button>
                <button id="btnDownloadSelection" class="btn btn-download" onclick="downloadCurrentSelection()" title="تحميل التحديد الحالي كملف HTML مستقل">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-left: 3px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    <span id="downloadBtnText">{initial_btn_text}</span>
                </button>
                <button class="btn btn-print" onclick="window.print()">
                    حفظ كـ PDF / طباعة
                </button>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- FIRST PAGE: Single-column minimal Index -->
        <div class="index-page-container">
            <div class="subject-main-banner">
                <h1 class="subject-title">{html.escape(first_sub)}</h1>
                <p class="subject-subtitle">بنك الأسئلة الموحد والشامل ({subtitle_str})</p>
                <p class="stats-summary" id="statsSummary">{stats_summary_str}</p>
            </div>

            <div class="index-section-title">{index_section_title}</div>

            <div class="index-list">
"""
    
    for gm in group_meta:
        gm_year = gm.get('year', '')
        gm_title = gm.get('title_display', gm['name'])
        html_out += f"""
                <div class="index-row-wrapper" data-group-id="{gm['id']}">
                    <a href="#{gm['id']}" class="index-row" data-group-id="{gm['id']}" data-year="{gm_year}">
                        <span class="index-topic-name">{html.escape(gm['name'])}</span>
                        <span class="index-topic-meta">
                            <span>{gm['range']}</span>
                            <span class="index-count">{gm['count']} سؤال</span>
                        </span>
                    </a>
                    <button type="button" class="btn-index-download no-print" onclick="downloadGroupItem(event, '{gm['id']}', '{html.escape(gm_title)}')" title="تحميل {html.escape(gm_title)} كملف مستقل">⬇ تحميل</button>
                </div>"""

    html_out += """
            </div><!-- end index-list -->
        </div><!-- end index-page-container -->
"""

    # Render each section: Topic Header and Question #1 are wrapped in an anchor container to avoid orphans!
    for gm in group_meta:
        g_id = gm['id']
        g_title = gm['title_display']
        g_qs = gm['questions']
        gm_year = gm.get('year', '')

        first_q = g_qs[0]
        first_q_html = render_question_card(1, first_q, group_by, theme)

        html_out += f"""
        <div class="topic-container" data-year="{gm_year}" data-group-id="{g_id}">
            <div class="topic-header-anchor">
                <div class="topic-header" id="{g_id}">
                    <div class="topic-title-text">{html.escape(g_title)}</div>
                    <span class="topic-counter">{len(g_qs)} سؤال</span>
                </div>
                {first_q_html}
            </div>
"""

        # Render questions 2 to N
        for q_num, q in enumerate(g_qs[1:], start=2):
            html_out += render_question_card(q_num, q, group_by, theme)

        html_out += """
        </div><!-- end topic-container -->
"""

    html_out += f"""
    </div><!-- end container -->

    <script>
        let currentFilterId = 'all';
        const originalStatsText = "{stats_summary_str}";
        const originalDocTitle = "{html.escape(doc_title)}";
        const subjectName = "{html.escape(first_sub)}";
        const groupByMode = "{group_by}";

        function setMode(mode) {{
            const body = document.body;
            const btnStudy = document.getElementById('btnStudy');
            const btnExam = document.getElementById('btnExam');

            body.classList.remove('study-mode', 'exam-mode');
            btnStudy.classList.remove('btn-active');
            btnExam.classList.remove('btn-active');

            if (mode === 'study') {{
                body.classList.add('study-mode');
                btnStudy.classList.add('btn-active');
            }} else if (mode === 'exam') {{
                body.classList.add('exam-mode');
                btnExam.classList.add('btn-active');
            }}
        }}

        function filterByItem(filterValue) {{
            currentFilterId = filterValue;
            const downloadBtnText = document.getElementById('downloadBtnText');
            const statsSummary = document.getElementById('statsSummary');
            const indexRows = document.querySelectorAll('.index-row-wrapper');
            const topicContainers = document.querySelectorAll('.topic-container');

            if (filterValue === 'all') {{
                document.querySelectorAll('.filter-hidden').forEach(el => el.classList.remove('filter-hidden'));
                if (downloadBtnText) downloadBtnText.textContent = groupByMode === 'session' ? "تحميل الدورة المحددة (HTML)" : "تحميل التصنيف المحدد (HTML)";
                if (statsSummary) statsSummary.textContent = originalStatsText;
                document.title = originalDocTitle;
                return;
            }}

            if (filterValue.startsWith('year_')) {{
                const year = filterValue.replace('year_', '');
                document.title = "بنك الأسئلة - " + subjectName + " (دورات " + year + ")";
                if (downloadBtnText) downloadBtnText.textContent = "تحميل دورات " + year + " (HTML)";

                let visibleCount = 0;
                let visibleSections = 0;
                topicContainers.forEach(tc => {{
                    const tcYear = tc.getAttribute('data-year');
                    if (tcYear === year) {{
                        tc.classList.remove('filter-hidden');
                        visibleSections++;
                        const qCards = tc.querySelectorAll('.question-card');
                        visibleCount += qCards.length;
                    }} else {{
                        tc.classList.add('filter-hidden');
                    }}
                }});

                indexRows.forEach(irw => {{
                    const rowYear = irw.querySelector('.index-row')?.getAttribute('data-year');
                    if (rowYear === year) {{
                        irw.classList.remove('filter-hidden');
                    }} else {{
                        irw.classList.add('filter-hidden');
                    }}
                }});

                if (statsSummary) {{
                    statsSummary.textContent = subjectName + " • دورات سنة " + year + " (" + visibleCount + " سؤال في " + visibleSections + " دورات)";
                }}
                return;
            }}

            const targetTc = document.querySelector('.topic-container[data-group-id="' + filterValue + '"]');
            const itemTitle = targetTc ? (targetTc.querySelector('.topic-title-text')?.textContent?.trim() || "") : "";
            const qCount = targetTc ? (targetTc.querySelectorAll('.question-card')?.length || 0) : 0;

            document.title = "بنك الأسئلة - " + subjectName + " (" + itemTitle + ")";
            if (downloadBtnText) {{
                downloadBtnText.textContent = "تحميل " + itemTitle + " (HTML)";
            }}

            topicContainers.forEach(tc => {{
                if (tc.getAttribute('data-group-id') === filterValue) {{
                    tc.classList.remove('filter-hidden');
                }} else {{
                    tc.classList.add('filter-hidden');
                }}
            }});

            indexRows.forEach(irw => {{
                if (irw.getAttribute('data-group-id') === filterValue) {{
                    irw.classList.remove('filter-hidden');
                }} else {{
                    irw.classList.add('filter-hidden');
                }}
            }});

            if (statsSummary) {{
                statsSummary.textContent = subjectName + " • " + itemTitle + " (" + qCount + " سؤال)";
            }}
        }}

        function downloadGroupItem(event, groupId, title) {{
            if (event) {{
                event.preventDefault();
                event.stopPropagation();
            }}
            const targetTc = document.querySelector('.topic-container[data-group-id="' + groupId + '"]');
            if (targetTc) {{
                exportContentAsHtml(subjectName + " - " + title, [targetTc]);
            }}
        }}

        function downloadCurrentSelection() {{
            if (currentFilterId === 'all') {{
                const allContainers = Array.from(document.querySelectorAll('.topic-container'));
                exportContentAsHtml(subjectName + " - بنك الأسئلة الكامل", allContainers);
                return;
            }}

            if (currentFilterId.startsWith('year_')) {{
                const year = currentFilterId.replace('year_', '');
                const yearContainers = Array.from(document.querySelectorAll('.topic-container[data-year="' + year + '"]'));
                exportContentAsHtml(subjectName + " - دورات سنة " + year, yearContainers);
                return;
            }}

            const targetTc = document.querySelector('.topic-container[data-group-id="' + currentFilterId + '"]');
            const itemTitle = targetTc ? (targetTc.querySelector('.topic-title-text')?.textContent?.trim() || "قسم") : "قسم";
            if (targetTc) {{
                exportContentAsHtml(subjectName + " - " + itemTitle, [targetTc]);
            }}
        }}

        function exportContentAsHtml(title, containerElements) {{
            if (!containerElements || containerElements.length === 0) return;

            let totalQs = 0;
            let clonedContainersHtml = '';

            containerElements.forEach(tc => {{
                const clone = tc.cloneNode(true);
                clone.classList.remove('filter-hidden');
                clone.querySelectorAll('.filter-hidden').forEach(el => el.remove());
                const cards = clone.querySelectorAll('.question-card');
                totalQs += cards.length;
                clonedContainersHtml += clone.outerHTML + '\\n';
            }});

            const styleContent = document.querySelector('style') ? document.querySelector('style').innerHTML : '';
            const watermarkEl = document.querySelector('.left-watermark-pulse');
            const watermarkHtml = watermarkEl ? watermarkEl.outerHTML : '';

            const standaloneHtml = '<!DOCTYPE html>' +
                '<html lang="ar" dir="rtl">' +
                '<head>' +
                '<meta charset="UTF-8">' +
                '<meta name="viewport" content="width=device-width, initial-scale=1.0">' +
                '<title>' + title + '</title>' +
                '<link rel="preconnect" href="https://fonts.googleapis.com">' +
                '<link rel="preconnect" href="https://fonts.gstatic.com">' +
                '<link href="https://fonts.googleapis.com/css2?family=Alexandria:wght@400;500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700;800&family=Noto+Sans+Arabic:wght@400;500;600;700;800&display=swap" rel="stylesheet">' +
                '<style>' + styleContent + '</style>' +
                '</head>' +
                '<body class="study-mode">' +
                watermarkHtml +
                '<div class="controls-header no-print">' +
                '<div class="header-title-container"><h1>' + title + '</h1></div>' +
                '<div class="btn-group">' +
                '<button id="btnStudy" class="btn btn-active" onclick="setStudyMode()">وضع الدراسة (إظهار الشرح)</button>' +
                '<button id="btnExam" class="btn" onclick="setExamMode()">وضع الاختبار (إخفاء الشرح)</button>' +
                '<button class="btn btn-print" onclick="window.print()">حفظ كـ PDF / طباعة</button>' +
                '</div></div>' +
                '<div class="container">' +
                '<div class="index-page-container" style="page-break-after: always; margin-bottom: 24px;">' +
                '<div class="subject-main-banner">' +
                '<h1 class="subject-title">' + subjectName + '</h1>' +
                '<p class="subject-subtitle">' + title + '</p>' +
                '<p class="stats-summary">' + totalQs + ' سؤال</p>' +
                '</div></div>' +
                clonedContainersHtml +
                '</div>' +
                '<script>' +
                'function setStudyMode() {{ setMode("study"); }}' +
                'function setExamMode() {{ setMode("exam"); }}' +
                'function setMode(mode) {{' +
                '  const body = document.body;' +
                '  const btnStudy = document.getElementById("btnStudy");' +
                '  const btnExam = document.getElementById("btnExam");' +
                '  body.classList.remove("study-mode", "exam-mode");' +
                '  btnStudy.classList.remove("btn-active");' +
                '  btnExam.classList.remove("btn-active");' +
                '  if (mode === "study") {{ body.classList.add("study-mode"); btnStudy.classList.add("btn-active"); }}' +
                '  else if (mode === "exam") {{ body.classList.add("exam-mode"); btnExam.classList.add("btn-active"); }}' +
                '}}' +
                '<' + '/script>' +
                '</body></html>';

            const cleanFileName = title.replace(/[\\/\\\\:*?"<>|]+/g, '_').trim() + '.html';
            const blob = new Blob([standaloneHtml], {{ type: 'text/html;charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = cleanFileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(url), 1500);
        }}
    </script>
</body>
</html>
"""

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_out)

    return output_path

# -----------------------------------------------------------------------------
# Discovery & Processing Utilities
# -----------------------------------------------------------------------------
def get_final_json_files():
    """Scans for the 10 master JSON question banks in the final/ directory."""
    workspace_dir = Path(__file__).resolve().parent.parent
    final_dir = workspace_dir / "final"
    if not final_dir.exists():
        return []
    
    files = sorted(final_dir.glob("*/*_all.json"))
    if not files:
        files = sorted([p for p in final_dir.glob("*/*.json") if p.name != "manifest.json"])
    return files

def scan_workspace_files():
    """Scans for available question bank files (.json and .csv) in workspace."""
    base_dir = Path(__file__).resolve().parent
    workspace_dir = base_dir.parent

    found = []
    seen_stems = set()

    # 1. Check final/ folder first (highest priority)
    for p in get_final_json_files():
        if p.stem not in seen_stems:
            found.append(p)
            seen_stems.add(p.stem)

    # 2. Check pdf_maker/input/
    input_dir = base_dir / "input"
    if input_dir.exists():
        for p in input_dir.glob("*.json"):
            if p.stem not in seen_stems:
                found.append(p)
                seen_stems.add(p.stem)
        for p in input_dir.glob("*.csv"):
            if p.stem not in seen_stems:
                found.append(p)
                seen_stems.add(p.stem)

    # 3. Check all_* folders in workspace
    for sub_dir in sorted(workspace_dir.glob("all_*")):
        if sub_dir.is_dir():
            for p in sorted(sub_dir.glob("*.json")):
                if p.stem not in seen_stems:
                    found.append(p)
                    seen_stems.add(p.stem)
            for p in sorted(sub_dir.glob("*.csv")):
                if p.stem not in seen_stems:
                    found.append(p)
                    seen_stems.add(p.stem)

    return found

def export_individual_sessions(questions, output_dir, stem, custom_subject=None):
    """Generates standalone HTML files for each individual exam session into a 'sessions/' subdirectory."""
    if not questions:
        return []

    first_sub = custom_subject or questions[0].get('subject') or "المادة الطبية"
    sessions_dir = Path(output_dir) / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    sessions_dict = {}
    for q in questions:
        sess = (q.get('date') or "").strip() or "دورات غير محددة"
        sessions_dict.setdefault(sess, []).append(q)

    generated_files = []
    sorted_sess = sorted(sessions_dict.keys(), key=parse_date_score, reverse=True)
    for s_name in sorted_sess:
        s_qs = sessions_dict[s_name]
        clean_name = re.sub(r'[^\w\u0600-\u06FF]+', '_', s_name).strip('_')
        s_title = s_name if (s_name.startswith("دورة") or s_name == "دورات غير محددة") else f"دورة {s_name}"
        out_file = sessions_dir / f"{stem}_{clean_name}.html"
        generate_html_document(
            questions=s_qs,
            output_path=str(out_file),
            group_by='session',
            custom_title=f"بنك الأسئلة - {first_sub} ({s_title})",
            switch_link=None
        )
        generated_files.append(out_file)

    return generated_files

def export_individual_topics(questions, output_dir, stem, custom_subject=None):
    """Generates standalone HTML files for each individual topic/category into a 'topics/' subdirectory."""
    if not questions:
        return []

    first_sub = custom_subject or questions[0].get('subject') or "المادة الطبية"
    topics_dir = Path(output_dir) / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)

    topics_dict = {}
    for q in questions:
        top = (q.get('topic') or "").strip() or "الموضوع العام"
        topics_dict.setdefault(top, []).append(q)

    generated_files = []
    for t_name, t_qs in topics_dict.items():
        clean_name = re.sub(r'[^\w\u0600-\u06FF]+', '_', t_name).strip('_')
        out_file = topics_dir / f"{stem}_{clean_name}.html"
        generate_html_document(
            questions=t_qs,
            output_path=str(out_file),
            group_by='topic',
            custom_title=f"بنك الأسئلة - {first_sub} ({t_name})",
            switch_link=None
        )
        generated_files.append(out_file)

    return generated_files

def export_individual_years(questions, output_dir, stem, custom_subject=None):
    """Generates standalone HTML files for each exam year into a 'years/' subdirectory."""
    if not questions:
        return []

    first_sub = custom_subject or questions[0].get('subject') or "المادة الطبية"
    years_dir = Path(output_dir) / "years"
    years_dir.mkdir(parents=True, exist_ok=True)

    # Group questions by year
    year_map = {}
    for q in questions:
        y, _ = parse_date_score(q.get('date', ''))
        if y > 1900:
            year_map.setdefault(str(y), []).append(q)

    generated_files = []
    for y in sorted(year_map.keys(), reverse=True):
        y_qs = year_map[y]
        out_file = years_dir / f"{stem}_{y}_sessions.html"
        generate_html_document(
            questions=y_qs,
            output_path=str(out_file),
            group_by='session',
            custom_title=f"بنك الأسئلة - {first_sub} (دورات {y})",
            switch_link=None
        )
        generated_files.append(out_file)

    return generated_files

def process_single_file(file_path, output_dir=None, export_years=True):
    path = Path(file_path)
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "output"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem

    print(f"\n---> Processing: {path.name}")
    try:
        questions = load_and_normalize(path)
        if not questions:
            print(f"[!] No valid questions found in {path.name}")
            return None

        first_sub = questions[0].get('subject') or "المادة الطبية"

        # 1. النسخة المرتبة بحسب المواضيع (Topics)
        out_topics_name = f"{stem}_topics.html"
        out_topics_path = output_dir / out_topics_name
        encoded_sessions_href = urllib.parse.quote(f"{stem}_sessions.html")
        switch_to_sessions = {
            "href": encoded_sessions_href,
            "label": "الترتيب حسب الدورات"
        }
        generate_html_document(
            questions=questions,
            output_path=str(out_topics_path),
            group_by='topic',
            custom_title=f"بنك الأسئلة - {first_sub} (مرتب حسب المواضيع)",
            switch_link=switch_to_sessions
        )

        # 2. النسخة المرتبة بحسب الدورات الامتحانية (Sessions)
        out_sessions_name = f"{stem}_sessions.html"
        out_sessions_path = output_dir / out_sessions_name
        encoded_topics_href = urllib.parse.quote(f"{stem}_topics.html")
        switch_to_topics = {
            "href": encoded_topics_href,
            "label": "الترتيب حسب المواضيع"
        }
        generate_html_document(
            questions=questions,
            output_path=str(out_sessions_path),
            group_by='session',
            custom_title=f"بنك الأسئلة - {first_sub} (مرتب حسب الدورات)",
            switch_link=switch_to_topics
        )

        # 3. Create default {stem}.html (identical copy of topics view)
        out_default_path = output_dir / f"{stem}.html"
        shutil.copyfile(out_topics_path, out_default_path)

        # Also copy to parent subject folder if in final/ or working_on/
        if "final" in str(path.parent) or "working_on" in str(path.parent):
            try:
                shutil.copyfile(out_topics_path, path.parent / out_topics_name)
                shutil.copyfile(out_sessions_path, path.parent / out_sessions_name)
                shutil.copyfile(out_default_path, path.parent / f"{stem}.html")
            except Exception:
                pass

        # 4. Generate standalone per-session, per-topic, and per-year HTML files
        if export_years:
            session_files = export_individual_sessions(questions, output_dir, stem, first_sub)
            topic_files = export_individual_topics(questions, output_dir, stem, first_sub)
            year_files = export_individual_years(questions, output_dir, stem, first_sub)

            print(f"[✓] Generated {len(session_files)} session files, {len(topic_files)} topic files, {len(year_files)} year files.")

            # Copy packages to parent subject folder
            for target_parent in [path.parent] if ("final" in str(path.parent) or "working_on" in str(path.parent)) else []:
                for subfolder, file_list in [("sessions", session_files), ("topics", topic_files), ("years", year_files)]:
                    sub_dest = target_parent / subfolder
                    sub_dest.mkdir(parents=True, exist_ok=True)
                    valid_names = {sf.name for sf in file_list}
                    for old_f in sub_dest.glob(f"{stem}_*.html"):
                        if old_f.name not in valid_names:
                            try:
                                old_f.unlink()
                            except Exception:
                                pass
                    for sf in file_list:
                        try:
                            shutil.copyfile(sf, sub_dest / sf.name)
                        except Exception:
                            pass

        print(f"[✓] Successfully generated master views and packages for {path.name}")
        return out_default_path

    except Exception as e:
        print(f"[ERROR] Failed to process {path.name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_all_final(output_dir=None, progress_callback=None):
    """Batch-converts all 10 master JSON question banks in final/."""
    files = get_final_json_files()
    if not files:
        print("[!] No final question bank files found.")
        return []

    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "output"
    else:
        output_dir = Path(output_dir)

    print(f"\n=======================================================")
    print(f"   Batch Building ALL Final Question Banks ({len(files)} subjects)")
    print(f"=======================================================")

    results = []
    total = len(files)
    for idx, f in enumerate(files, start=1):
        if progress_callback:
            progress_callback(idx, total, f.name)
        res = process_single_file(f, output_dir)
        if res:
            results.append(res)

    print(f"\n[✓] Completed: {len(results)} of {total} subjects generated successfully.")
    return results

# -----------------------------------------------------------------------------
# GUI Launch Dialog (Batch final vs Manual Selection)
# -----------------------------------------------------------------------------
def launch_gui_dialog():
    """Modern Tkinter modal dialog offering Batch final vs Manual single file."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog

        root = tk.Tk()
        root.title("TealMED - بناء عروض HTML و PDF للأسئلة")
        root.geometry("560x390")
        root.resizable(False, False)
        root.configure(bg="#f8fafc")
        root.attributes('-topmost', True)

        # Center on screen
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = max(0, int((sw - 560) / 2))
        y = max(0, int((sh - 390) / 2))
        root.geometry(f"560x390+{x}+{y}")

        # Header Banner
        header = tk.Frame(root, bg="#0f172a", padx=20, pady=16)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="مولّد بنوك الأسئلة التفاعلية والـ PDF",
            font=("Segoe UI", 13, "bold"),
            fg="#ffffff",
            bg="#0f172a"
        ).pack(anchor=tk.W)

        tk.Label(
            header,
            text="توليد عروض مرتبة بحسب المواضيع وبحسب الدورات الامتحانية (مجهزة للطباعة)",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a"
        ).pack(anchor=tk.W, pady=(2, 0))

        content = tk.Frame(root, bg="#f8fafc", padx=24, pady=18)
        content.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            content,
            text="حدد آلية العمل المطلوبة:",
            font=("Segoe UI", 10, "bold"),
            fg="#1e293b",
            bg="#f8fafc"
        ).pack(anchor=tk.W, pady=(0, 12))

        status_var = tk.StringVar(value="جاهز للبدء...")
        progress_bar = ttk.Progressbar(content, orient=tk.HORIZONTAL, mode='determinate')

        def on_batch_final():
            btn_batch.config(state=tk.DISABLED)
            btn_manual.config(state=tk.DISABLED)
            progress_bar.pack(fill=tk.X, pady=(10, 4))
            progress_bar['maximum'] = 10
            progress_bar['value'] = 0

            def worker():
                def update_prog(curr, tot, name):
                    progress_bar['value'] = curr
                    status_var.set(f"جاري معالجة [{curr}/{tot}]: {name}")
                    root.update_idletasks()

                results = process_all_final(progress_callback=update_prog)
                status_var.set(f"✅ تم اكتمال بناء كافة المواد ({len(results)} مواد بنجاح!)")
                messagebox.showinfo(
                    "اكتمل البناء بنجاح",
                    f"تم توليد عروض المواضيع والدورات لكافة المواد ({len(results)} مواد) في مجلد output بنجاح!\n\nيمكنك الآن فتح الملفات وطباعتها كـ PDF مباشرة."
                )
                out_dir = Path(__file__).resolve().parent / "output"
                os.startfile(str(out_dir))
                root.destroy()

            import threading
            threading.Thread(target=worker, daemon=True).start()

        def on_manual_file():
            selected = filedialog.askopenfilename(
                title="اختر ملف بنك الأسئلة (.json أو .csv)",
                filetypes=[
                    ("ملفات بنوك الأسئلة", "*.json *.csv"),
                    ("ملفات JSON", "*.json"),
                    ("ملفات CSV", "*.csv")
                ]
            )
            if selected:
                status_var.set(f"جاري معالجة: {Path(selected).name}...")
                btn_batch.config(state=tk.DISABLED)
                btn_manual.config(state=tk.DISABLED)

                def worker():
                    res = process_single_file(selected)
                    if res:
                        status_var.set("✅ تم اكتمال البناء بنجاح!")
                        messagebox.showinfo("اكتمل البناء", f"تم بناء العروض بنجاح للملف:\n{Path(selected).name}")
                        os.startfile(str(res))
                    root.destroy()

                import threading
                threading.Thread(target=worker, daemon=True).start()

        # Option 1: Batch Process All Final Files
        final_files_count = len(get_final_json_files())
        card1 = tk.Frame(content, bg="#ffffff", highlightbackground="#cbd5e1", highlightthickness=1, padx=14, pady=10)
        card1.pack(fill=tk.X, pady=(0, 10))

        btn_batch = tk.Button(
            card1,
            text=f"🚀 بناء كافة ملفات مجلد final دفعة واحدة ({final_files_count} مواد كاملة)",
            font=("Segoe UI", 10, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            command=on_batch_final
        )
        btn_batch.pack(anchor=tk.W)

        tk.Label(
            card1,
            text="يقوم بتحويل كافة المواد الـ 10 (القلبية، الهضمية، التوليد، الأطفال...) دفعة واحدة وتوليد عروض المواضيع والدورات المحدثة.",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#ffffff",
            justify=tk.LEFT,
            wraplength=480
        ).pack(anchor=tk.W, pady=(4, 0))

        # Option 2: Manual Single File Selection
        card2 = tk.Frame(content, bg="#ffffff", highlightbackground="#cbd5e1", highlightthickness=1, padx=14, pady=10)
        card2.pack(fill=tk.X, pady=(0, 10))

        btn_manual = tk.Button(
            card2,
            text="📁 اختيار ملف مفرد يدوياً (.json أو .csv)",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2",
            command=on_manual_file
        )
        btn_manual.pack(anchor=tk.W)

        tk.Label(
            card2,
            text="اختيار وتوليد ملف واحد محدد يدوياً من جهازك أو من أي مجلد آخر.",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#ffffff",
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(3, 0))

        # Status footer
        status_lbl = tk.Label(
            content,
            textvariable=status_var,
            font=("Segoe UI", 8, "italic"),
            fg="#475569",
            bg="#f8fafc"
        )
        status_lbl.pack(anchor=tk.W, pady=(4, 0))

        root.mainloop()

    except Exception as e:
        print(f"[!] GUI Error: {e}")
        interactive_menu()

# -----------------------------------------------------------------------------
# CLI Interactive Menu
# -----------------------------------------------------------------------------
def interactive_menu():
    print("=" * 65)
    print(" TealMED PDF & HTML Question Bank Generator ")
    print("=" * 65)
    files = scan_workspace_files()

    print("\nAvailable Question Banks:")
    for idx, f in enumerate(files, start=1):
        rel = f.name
        try:
            rel = f.relative_to(Path(__file__).resolve().parent.parent)
        except Exception:
            pass
        print(f"  [{idx:2d}] {rel}")

    print("\nOptions:")
    print("  [ F] Process ALL 10 final subjects (final/*_all.json) [RECOMMENDED]")
    print("  [ A] Process ALL files found above")
    print("  [ G] Open Graphical Menu (Windows GUI)")
    print("  [ Q] Quit")

    choice = input("\nEnter your selection: ").strip()
    if choice.upper() == 'Q':
        return
    elif choice.upper() == 'F':
        process_all_final()
    elif choice.upper() == 'A':
        out_dir = Path(__file__).resolve().parent / "output"
        for f in files:
            process_single_file(f, out_dir)
    elif choice.upper() == 'G':
        launch_gui_dialog()
    elif choice.isdigit():
        num = int(choice)
        if 1 <= num <= len(files):
            out_dir = Path(__file__).resolve().parent / "output"
            process_single_file(files[num - 1], out_dir)
        else:
            print("[!] Invalid number.")
    else:
        print("[!] Invalid selection.")

def main():
    parser = argparse.ArgumentParser(description="TealMED PDF/HTML Question Bank Generator")
    parser.add_argument("file", nargs="?", help="Path to .json or .csv file")
    parser.add_argument("--gui", action="store_true", help="Open Graphical Launcher dialog")
    parser.add_argument("--final", action="store_true", help="Process all 10 subjects in final/")
    parser.add_argument("--all", action="store_true", help="Process all files in input folder")
    parser.add_argument("--out", "-o", help="Custom output directory")
    args = parser.parse_args()

    out_dir = Path(args.out) if args.out else (Path(__file__).resolve().parent / "output")

    if args.gui:
        launch_gui_dialog()
    elif args.final:
        process_all_final(out_dir)
    elif args.all:
        files = scan_workspace_files()
        for f in files:
            process_single_file(f, out_dir)
    elif args.file:
        process_single_file(args.file, out_dir)
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
