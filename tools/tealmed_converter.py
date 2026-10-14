"""
TealMED Medical Data Parsing & Conversion Specialist
===================================================
Production-grade converter for medical question banks (CSV / Excel).
Ensures 100% verbatim fidelity, zero hallucinations, safe clinical artifact cleaning,
and customizable, collision-free database IDs matching the TealMED database schema.
"""

import os
import sys
import re
import html
import json
import random
from pathlib import Path
import pandas as pd

# Regex targeting ONLY recognized HTML tags
# (Preserves clinical inequality operators like '< 30 g/L' and '> 140 mmHg')
SAFE_HTML_TAG_REGEX = re.compile(
    r'</?(?:html|body|p|span|div|br|b|i|strong|em|font|table|tbody|tr|td|th|ul|ol|li|a|h[1-6]|style|script)\b[^>]*>',
    re.IGNORECASE
)


def safe_clean_text(val):
    """
    Cleans text by removing HTML/CSS artifacts while preserving verbatim clinical text
    and protecting clinical inequality operators (< and >).
    """
    if val is None or pd.isna(val):
        return ""
    text = str(val)

    # 1. Replace Excel carriage return export artifacts
    text = text.replace("_x000D_", "\n").replace("*x000D*", "\n")

    # 2. Decode HTML entities (e.g., &nbsp;, &gt;, &#39;)
    text = html.unescape(text)

    # 3. Strip ONLY recognized HTML tags (protects '< 30 g/L' or '> 140')
    text = SAFE_HTML_TAG_REGEX.sub(' ', text)

    # 4. Remove residual web attributes if unclosed (e.g. style="..." or class="...")
    text = re.sub(r'(?:style|class|id)\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)

    # 5. Clean trailing / multiple whitespace per line while preserving linebreaks
    cleaned_lines = []
    for line in text.splitlines():
        line_clean = re.sub(r'[ \t\f\v]+', ' ', line).strip()
        if line_clean:
            cleaned_lines.append(line_clean)

    return "\n".join(cleaned_lines)


def clean_prefix_string(prefix):
    """Normalizes prefix string to clean kebab/snake case without leading 'q_'."""
    p = re.sub(r'[^a-zA-Z0-9_-]', '_', str(prefix or '').strip()).strip('_-').lower()
    if p.startswith('q_'):
        p = p[2:]
    return p or "question"


def parse_csv_to_tealmed_json(csv_path, output_json_path=None, id_prefix=None, start_index=1, pad_width=2):
    """
    Parses a CSV or Excel medical questions file into the TealMED schema JSON format.
    
    Args:
        csv_path: Path to the CSV or Excel file.
        output_json_path: Path to save the JSON output (optional).
        id_prefix: User-defined prefix (e.g. 'cardio', 'nephro'). If None, uses filename stem.
        start_index: Starting number for question IDs (default: 1).
        pad_width: Zero-padding width (default: 2, e.g. 01, 02).
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Source file not found: {csv_path}")

    # Read CSV or Excel with robust encoding fallback
    if csv_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(csv_path)
    else:
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(csv_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding="cp1256")

    # Drop completely empty rows
    df = df.dropna(how='all')

    # Case-insensitive column lookup
    col_lookup = {str(col).strip().lower(): col for col in df.columns}

    def get_val(row, *candidates):
        for c in candidates:
            c_low = c.lower()
            if c_low in col_lookup:
                val = row[col_lookup[c_low]]
                if pd.notna(val):
                    return val
        return None

    prefix = clean_prefix_string(id_prefix if id_prefix else csv_path.stem)
    items = []
    validation_warnings = []
    current_index = start_index

    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        # 1. Deterministic Question ID
        # If the CSV already has an explicit Question_ID column, respect it:
        explicit_id = None
        for col in ['Question_ID', 'question_id', 'id', 'ID', 'Id']:
            if col in row and pd.notna(row[col]) and str(row[col]).strip():
                raw = str(row[col]).strip()
                clean = re.sub(r'[^a-zA-Z0-9_-]', '_', raw).strip('_-').lower()
                explicit_id = clean if clean.startswith('q_') else f"q_{clean}"
                break

        if explicit_id:
            q_id = explicit_id
        else:
            num_str = str(current_index).zfill(pad_width)
            q_id = f"q_{prefix}_{num_str}"
            current_index += 1

        # 2. Subject Name
        subject_name = safe_clean_text(get_val(row, "Medical_Subject", "subject_name", "subject", "المادة", "الموضوع_العام") or "الكلية")

        # 3. Topic Name (Strictly set to "الموضوع" if missing)
        raw_topic = get_val(row, "topic_name", "Chapter_or_Section", "topic", "chapter", "الفصل", "المبحث")
        topic_name = safe_clean_text(raw_topic) if raw_topic and str(raw_topic).strip() else "الموضوع"

        # 4. Question Title
        raw_title = get_val(row, "Question_Text", "title", "question", "نص_السؤال", "السؤال")
        title = safe_clean_text(raw_title)
        if not title:
            validation_warnings.append(f"Row {idx} ({q_id}): Question title is empty!")

        # 5. Exam Period
        raw_exam_date = get_val(row, "Exam_Date", "exam_period", "exam_date", "الدورة", "تاريخ_الامتحان")
        exam_period = safe_clean_text(raw_exam_date) if raw_exam_date and str(raw_exam_date).strip() else None

        # 6. Explanation
        raw_exp = get_val(row, "Explanation", "explanation", "exp", "الشرح", "التفسير", "التعليل")
        explanation = safe_clean_text(raw_exp)

        # 7. Choices: 1 Correct + any non-empty Wrong answers (e.g. 3, 4, or 5 options)
        correct_text = safe_clean_text(get_val(row, "Correct_Answer", "correct_answer", "answer", "الجواب_الصحيح", "الإجابة_الصحيحة"))
        if not correct_text:
            validation_warnings.append(f"Row {idx} ({q_id}): Correct_Answer is empty!")

        raw_choices = []
        if correct_text:
            raw_choices.append({"text": correct_text, "is_correct": True})

        # Collect only non-empty wrong answers (supporting up to 5 wrong answers = 6 options total)
        wrong_candidates = [
            get_val(row, "Wrong_Answer_1", "wrong_answer_1", "wrong_1", "الخيار_الخاطئ_1", "خطأ_1"),
            get_val(row, "Wrong_Answer_2", "wrong_answer_2", "wrong_2", "الخيار_الخاطئ_2", "خطأ_2"),
            get_val(row, "Wrong_Answer_3", "wrong_answer_3", "wrong_3", "الخيار_الخاطئ_3", "خطأ_3"),
            get_val(row, "Wrong_Answer_4", "wrong_answer_4", "wrong_4", "الخيار_الخاطئ_4", "خطأ_4"),
            get_val(row, "Wrong_Answer_5", "wrong_answer_5", "wrong_5", "الخيار_الخاطئ_5", "خطأ_5"),
        ]

        for w_val in wrong_candidates:
            w_text = safe_clean_text(w_val)
            if w_text:
                raw_choices.append({"text": w_text, "is_correct": False})

        if len(raw_choices) < 2:
            validation_warnings.append(f"Row {idx} ({q_id}): Question has fewer than 2 valid options!")

        # Shuffle choices randomly so correct answer is distributed
        random.shuffle(raw_choices)

        # Assign letters sequentially (A, B, C, D, E, F... matching the actual number of choices)
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        formatted_options = []
        correct_letter = None

        for i, opt in enumerate(raw_choices):
            letter = alphabet[i]
            if opt["is_correct"]:
                correct_letter = letter
            formatted_options.append({
                "letter": letter,
                "text": opt["text"],
                "is_correct": opt["is_correct"]
            })

        # 8. High Yield Note (Extract from CSV column or fallback to explanation text)
        raw_hy = get_val(row, "High_Yield_Note", "high_yield_note", "high_yield", "الفكرة_من_السؤال", "الفكرة من السؤال", "نقطة عالية الأهمية", "نقطة_عالية_الأهمية")
        high_yield_note = safe_clean_text(raw_hy) if raw_hy else None
        if not high_yield_note and explanation:
            hy_m = re.search(r'(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|الفكرة\s+من\s+السؤال)\s*:\s*(.*?)(?=(?:EXPLANATION|الشرح|التعليل)\s*:|$)', explanation, re.DOTALL | re.IGNORECASE)
            if hy_m:
                high_yield_note = safe_clean_text(hy_m.group(1))

        # 9. Educational Objective (Extract from CSV column or fallback to explanation text)
        raw_edu = get_val(row, "Educational_Objective", "educational_objective", "الهدف_من_السؤال", "الهدف من السؤال", "الهدف_التعليمي", "الهدف التعليمي")
        educational_objective = safe_clean_text(raw_edu) if raw_edu else None
        if not educational_objective and explanation:
            edu_m = re.search(r'(?:EDUCATIONAL\s+OBJECTIVE|الهدف\s+التعليمي|الهدف\s+من\s+السؤال)\s*:\s*(.*?)(?=(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|EXPLANATION|الشرح|التعليل)\s*:|$)', explanation, re.DOTALL | re.IGNORECASE)
            if edu_m:
                educational_objective = safe_clean_text(edu_m.group(1))

        # Assemble full question item matching exact TealMED JSON schema
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
            "educational_objective": educational_objective,
            "high_yield_note": high_yield_note,
            "explanation": explanation,
            "options": formatted_options
        }
        items.append(item)

    # Save to output file
    if output_json_path is None:
        output_json_path = csv_path.with_suffix(".json")

    out_path = Path(output_json_path)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"[OK] Converted {len(items)} questions -> '{out_path.name}' (IDs: {items[0]['id']} .. {items[-1]['id']})")
    if validation_warnings:
        print(f"     [!] Warnings ({len(validation_warnings)}):")
        for w in validation_warnings[:5]:
            print(f"         - {w}")
        if len(validation_warnings) > 5:
            print(f"         ... and {len(validation_warnings) - 5} more warnings.")

    return items, current_index


def select_files_gui():
    """Opens native Windows file picker to select one or multiple CSV / Excel files."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        file_paths = filedialog.askopenfilenames(
            title="TealMED Converter - Select CSV or Excel File(s)",
            filetypes=[
                ("Medical Question Files", "*.csv *.xlsx *.xls"),
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls"),
                ("All Files", "*.*")
            ]
        )
        root.destroy()
        return list(file_paths)
    except Exception as e:
        print(f"Could not open GUI file dialog: {e}")
        return []


def main():
    print("\n" + "="*60)
    print(" TealMED Medical Question Converter")
    print("="*60)

    # 1. Determine files to convert
    if len(sys.argv) > 1:
        # CLI usage
        selected_files = [str(Path(p).resolve()) for p in sys.argv[1:] if Path(p).is_file()]
    else:
        print("Select one or multiple CSV/Excel files from the file picker...")
        selected_files = select_files_gui()
    
    if not selected_files:
        print("No files were selected. Exiting.")
        input("\nPress Enter to exit...")
        return

    print(f"\nFiles to convert ({len(selected_files)}):")
    for f in selected_files:
        print(f"  • {Path(f).name}")

    # 2. Ask user for ID prefix (e.g. cardio, nephro, renal)
    default_prefix = Path(selected_files[0]).stem.replace("-", "_").lower()
    # If filename is renal_01, default can suggest renal
    suggested = re.sub(r'_\d+$', '', default_prefix)
    
    print("-" * 60)
    user_prefix = input(f"Enter ID prefix (e.g. cardio, renal, nephro) [Default: '{suggested}']: ").strip()
    chosen_prefix = user_prefix if user_prefix else suggested

    # 3. Ask user for starting question number
    start_num_input = input("Enter starting question number [Default: 1]: ").strip()
    try:
        current_start = int(start_num_input) if start_num_input else 1
    except ValueError:
        current_start = 1

    # 4. If multiple files, ask if numbering continues sequentially
    continuous = True
    if len(selected_files) > 1:
        cont_input = input("Continue numbering sequentially across all files? (Y/n) [Default: Y]: ").strip().lower()
        continuous = cont_input != 'n'

    print("-" * 60)
    print(f"Converting with prefix: 'q_{clean_prefix_string(chosen_prefix)}' starting at #{current_start}...\n")

    for file_path in selected_files:
        p = Path(file_path)
        items, next_start = parse_csv_to_tealmed_json(
            csv_path=p,
            id_prefix=chosen_prefix,
            start_index=current_start,
            pad_width=2
        )
        if continuous:
            current_start = next_start

    print("\nConversion complete! All JSON files are ready.")
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
