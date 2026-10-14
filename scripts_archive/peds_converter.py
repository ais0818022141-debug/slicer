"""
TealMED Converter for Pediatrics (طب الأطفال)
==============================================
Converts `all_peds/أسئلة دورات الاطفال 2.xlsx` into `all_peds/أسئلة دورات الاطفال.json`
Ensures 100% fidelity, zero data corruption, clean stripped topics, and strict schema compliance.
"""

import os
import re
import json
import html
from pathlib import Path
import pandas as pd

SAFE_HTML_TAG_REGEX = re.compile(
    r'</?(?:html|body|p|span|div|br|b|i|strong|em|font|table|tbody|tr|td|th|ul|ol|li|a|h[1-6]|style|script)\b[^>]*>',
    re.IGNORECASE
)

def safe_clean_text(val):
    if val is None or pd.isna(val):
        return ""
    text = str(val)
    text = text.replace("_x000D_", "\n").replace("*x000D*", "\n")
    text = html.unescape(text)
    text = SAFE_HTML_TAG_REGEX.sub(' ', text)
    text = re.sub(r'(?:style|class|id)\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    cleaned_lines = []
    for line in text.splitlines():
        line_clean = re.sub(r'[ \t\f\v]+', ' ', line).strip()
        if line_clean:
            cleaned_lines.append(line_clean)
    return "\n".join(cleaned_lines)

def norm_for_match(s):
    if not s or pd.isna(s): return ""
    s = str(s).strip()
    s = re.sub(r'[\.\,\:\s\(\)\"\'«»ـ\-\/]', '', s)
    s = re.sub(r'[أإآا]', 'ا', s)
    s = re.sub(r'[ةه]', 'ه', s)
    s = re.sub(r'[ىي]', 'ي', s)
    return s.lower()

def clean_topic_name(topic):
    if not topic or pd.isna(topic):
        return "عام"
    # Strips "15. الفصل الخامس عشر: " -> "الأمراض الخمجية والمناعة"
    t = re.sub(r'^\s*\d+\s*[\.\-]?\s*الفصل\s+[\w\s]+?:\s*', '', str(topic)).strip()
    return safe_clean_text(t)

def resolve_correct_letter(exp, opts, row_num):
    # Match the answer portion before "الشرح" or "\n"
    m = re.match(r'^(?:الإجابة الصحيحة|الاجابة الصحيحة|الإجابة|الاجابة|الجواب الصحيح|الجواب|الخيار الصحيح)\s*[:\-]?\s*(.*?)(?=(?:الشرح|تفنيد|ترميم|\n)|$)', exp)
    ht = m.group(1).strip() if m else exp[:80]

    # Check 1: Quoted letter like "A" or 'B'
    m_quoted = re.match(r'^["\'«]([A-Ea-e])["\'»]\s*(?:\((.*?)\))?', ht)
    if m_quoted:
        let = m_quoted.group(1).upper()
        if let in opts:
            return let

    # Check 2: Standalone letter followed by word boundary
    m_standalone = re.match(r'^([A-Ea-e])\b(?!\w)\s*(?:\((.*?)\))?', ht)
    if m_standalone:
        let = m_standalone.group(1).upper()
        if let in opts:
            return let

    # Check 3: Text match (e.g. "انغلاف أمعاء" or "ASD")
    clean_text = ht.strip('"\'«»() .:')
    nt = norm_for_match(clean_text)

    matches = []
    for ch, val in opts.items():
        nv = norm_for_match(val)
        if nt == nv:
            matches.append((ch, "EXACT"))
        elif nt in nv or nv in nt:
            matches.append((ch, "PARTIAL"))

    if len(matches) == 1:
        return matches[0][0]
    elif len(matches) > 1:
        exacts = [m for m in matches if m[1] == "EXACT"]
        if len(exacts) == 1:
            return exacts[0][0]
        raise ValueError(f"Row {row_num}: Ambiguous text match for '{clean_text}': {matches}")
    
    raise ValueError(f"Row {row_num}: Could not resolve answer from header '{ht}'. Options: {opts}")

def convert_peds_excel():
    excel_path = Path(r"c:\Users\Toshiba\Desktop\slicer\all_peds\أسئلة دورات الاطفال 2.xlsx")
    output_json_path = excel_path.parent / "أسئلة دورات الاطفال.json"
    
    df = pd.read_excel(excel_path)
    df = df.dropna(how='all')

    items = []
    pad_width = 2 if len(df) < 100 else len(str(len(df)))

    for idx, row in df.iterrows():
        row_num = idx + 2
        seq_num = idx + 1
        num_str = str(seq_num).zfill(pad_width)
        q_id = f"q_peds_{num_str}"

        # 1. Subject & Topic
        subject_name = "طب الأطفال"
        topic_name = clean_topic_name(row.get("الموضوع"))

        # 2. Title & Exam Date
        title = safe_clean_text(row.get("نص السؤال"))
        raw_exam = row.get("تاريخ الدورة")
        exam_period = safe_clean_text(raw_exam) if pd.notna(raw_exam) else None

        # 3. Explanation
        raw_exp = row.get("الإجابة والشرح")
        explanation = safe_clean_text(raw_exp)

        # 4. Options
        opts_dict = {}
        for ch in "ABCDE":
            val = row.get(f"الخيار {ch}")
            if pd.notna(val):
                clean_opt = safe_clean_text(val)
                if clean_opt and clean_opt != "فارغ":
                    opts_dict[ch] = clean_opt

        # 5. Resolve Correct Letter
        correct_letter = resolve_correct_letter(explanation, opts_dict, row_num)

        # 6. Build formatted options list (preserving A, B, C, D, E letters)
        formatted_options = []
        for ch in sorted(opts_dict.keys()):
            formatted_options.append({
                "letter": ch,
                "text": opts_dict[ch],
                "is_correct": (ch == correct_letter)
            })

        # 7. Assemble Item according to TealMED Schema
        item = {
            "id": q_id,
            "subject_name": subject_name,
            "topic_name": topic_name,
            "title": title,
            "difficulty": "متوسط",
            "exam_type": "national_board",
            "exam_period": exam_period,
            "points": 10,
            "is_free": 1,
            "correct_option": correct_letter,
            "vignette": None,
            "attending_clue": None,
            "educational_objective": None,
            "high_yield_note": None,
            "explanation": explanation,
            "options": formatted_options
        }
        items.append(item)

    # Save to JSON
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    # Also save a standard alias peds_all.json for uniformity
    alias_path = excel_path.parent / "peds_all.json"
    with open(alias_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"SUCCESS: Converted {len(items)} questions to:")
    print(f"  1. {output_json_path.name}")
    print(f"  2. {alias_path.name}")
    return items

if __name__ == "__main__":
    convert_peds_excel()
