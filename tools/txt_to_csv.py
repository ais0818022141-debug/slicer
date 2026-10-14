"""
TealMED Text to CSV Converter
=============================
Converts MCQ questions written in markdown/text format (e.g. mcq.txt)
into a CSV format fully compatible with slicer.py.
"""

import re
import csv
import argparse
from pathlib import Path


def parse_mcq_text(text: str):
    """
    Parses a markdown/text string containing one or more questions formatted like:
    ### Question
    * **subject_name:** ...
    * **topic_name:** ...
    * **title:** ...
    * **exam_type:** ...
    * **exam_period:** ...
    * **correct_option:** A
    
    **Options:**
    * A) ...
    * B) ...
    * C) ...
    * D) ...
    * E) ...
    """
    # Split questions by '### Question' or '### question'
    raw_blocks = re.split(r'(?m)^###\s+Question\b', text, flags=re.IGNORECASE)
    questions = []

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        # Extract key-value metadata pairs
        # Format: * **key:** value OR **key:** value OR key: value
        metadata = {}
        for line in block.splitlines():
            line_clean = line.strip()
            # Match * **key:** value or **key:** value
            m = re.match(r'^(?:\*\s*)?\*\*([a-zA-Z0-9_]+)\s*:\*\*\s*(.*)$', line_clean)
            if m:
                k = m.group(1).lower().strip()
                v = m.group(2).strip()
                metadata[k] = v

        # Extract Options
        # Options are usually preceded by **Options:**
        # Matches: * A) text, * A. text, A) text, up to F)
        options_dict = {}
        option_pattern = re.compile(r'^(?:\*\s*)?([A-Fa-f])[\)\.\-:]\s*(.+)$')
        
        in_options_section = False
        for line in block.splitlines():
            line_clean = line.strip()
            if re.match(r'^\*\*Options:\*\*', line_clean, re.IGNORECASE) or line_clean.lower() == 'options:':
                in_options_section = True
                continue
            
            opt_match = option_pattern.match(line_clean)
            if opt_match:
                letter = opt_match.group(1).upper()
                opt_text = opt_match.group(2).strip()
                options_dict[letter] = opt_text

        # Validate minimum required fields
        title = metadata.get("title", "")
        if not title:
            continue

        correct_letter = metadata.get("correct_option", "").strip().upper()
        if not correct_letter:
            correct_letter = "A"

        subject = metadata.get("subject_name", "")
        topic = metadata.get("topic_name", "")
        exam_period = metadata.get("exam_period", "")
        explanation = metadata.get("explanation", "")
        high_yield = metadata.get("high_yield_note", "") or metadata.get("الفكرة_من_السؤال", "") or metadata.get("الفكرة من السؤال", "") or metadata.get("نقطة_عالية_الأهمية", "")
        if not high_yield and explanation:
            hy_m = re.search(r'(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|الفكرة\s+من\s+السؤال)\s*:\s*(.*?)(?=(?:EXPLANATION|الشرح|التعليل)\s*:|$)', explanation, re.DOTALL | re.IGNORECASE)
            if hy_m:
                high_yield = hy_m.group(1).strip()

        educational_obj = metadata.get("educational_objective", "") or metadata.get("الهدف_من_السؤال", "") or metadata.get("الهدف من السؤال", "") or metadata.get("الهدف_التعليمي", "") or metadata.get("الهدف التعليمي", "")
        if not educational_obj and explanation:
            edu_m = re.search(r'(?:EDUCATIONAL\s+OBJECTIVE|الهدف\s+التعليمي|الهدف\s+من\s+السؤال)\s*:\s*(.*?)(?=(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|EXPLANATION|الشرح|التعليل)\s*:|$)', explanation, re.DOTALL | re.IGNORECASE)
            if edu_m:
                educational_obj = edu_m.group(1).strip()

        correct_answer = options_dict.get(correct_letter, "")
        wrong_answers = [text for letter, text in sorted(options_dict.items()) if letter != correct_letter]

        row = {
            "Medical_Subject": subject,
            "Exam_Date": exam_period,
            "Chapter_or_Section": topic,
            "Question_Text": title,
            "Explanation": explanation,
            "High_Yield_Note": high_yield,
            "Educational_Objective": educational_obj,
            "Correct_Answer": correct_answer,
            "Wrong_Answer_1": wrong_answers[0] if len(wrong_answers) > 0 else "",
            "Wrong_Answer_2": wrong_answers[1] if len(wrong_answers) > 1 else "",
            "Wrong_Answer_3": wrong_answers[2] if len(wrong_answers) > 2 else "",
            "Wrong_Answer_4": wrong_answers[3] if len(wrong_answers) > 3 else "",
            "Wrong_Answer_5": wrong_answers[4] if len(wrong_answers) > 4 else "",
        }
        questions.append(row)

    return questions


def convert_txt_to_csv(txt_path: Path, output_csv: Path = None):
    txt_path = Path(txt_path)
    if not txt_path.exists():
        raise FileNotFoundError(f"File not found: {txt_path}")

    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    questions = parse_mcq_text(content)
    if not questions:
        print("[!] No questions could be parsed from the file.")
        return None

    if output_csv is None:
        output_csv = txt_path.with_suffix(".csv")

    has_w5 = any(q.get("Wrong_Answer_5") for q in questions)
    fieldnames = [
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
        "Wrong_Answer_4"
    ]
    if has_w5:
        fieldnames.append("Wrong_Answer_5")

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(questions)

    print(f"[OK] Successfully converted {len(questions)} question(s) to '{output_csv.name}'")
    return output_csv


def main():
    parser = argparse.ArgumentParser(description="Convert mcq.txt to slicer-compatible CSV")
    parser.add_argument("--file", "-f", default="mcq.txt", help="Input text file path (default: mcq.txt)")
    parser.add_argument("--out", "-o", default=None, help="Output CSV file path")
    args = parser.parse_args()

    convert_txt_to_csv(Path(args.file), Path(args.out) if args.out else None)


if __name__ == "__main__":
    main()
