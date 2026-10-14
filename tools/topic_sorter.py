"""
TealMED Topic Grouper & Chronological Sorter Tool
=================================================
1. Merges all chunked questions for a subject prefix (e.g. 'hema_*.json').
2. Groups questions by Topic ('topic_name').
3. Sorts questions within each topic chronologically by Exam Date ('exam_period'),
   from newest session (e.g. May 2026) down to oldest.
4. Exports per-topic in a new directory ('classified/'):
   - Full TealMED database JSON (.json)
   - Full CSV with choices & metadata (.csv)
   - Concise AI Markdown prompt (_ai.md) ready for AI explanation generation.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict
import pandas as pd


# Syrian and Arab Medical Board exam month normalization map
MONTH_MAP = {
    'كانون الثاني': 1,
    'شباط': 2,
    'اذار': 3,
    'نيسان': 4,
    'ايار': 5,
    'حزيران': 6,
    'تموز': 7,
    'اب': 8,
    'ايلول': 9,
    'تشرين الاول': 10,
    'تشرين الثاني': 11,
    'كانون الاول': 12,
    # Short / common variations
    'تشرين': 10,
    'كانون': 12,
    'ربيع': 4,
    'صيف': 7,
    'خريف': 10,
    'شتاء': 1
}


def parse_exam_date(text):
    """
    Parses Arabic exam period string (e.g. 'أيار 2026', 'تشـــرين 2020', 'آذار 2023').
    Returns tuple (year, month) for chronological sorting (newest first).
    """
    if not text:
        return (0, 0)
    raw = str(text)
    # Remove tatweel (ـ) and normalize hamzas (أ, إ, آ -> ا)
    norm = raw.replace('ـ', '')
    norm = re.sub(r'[أإآ]', 'ا', norm)

    # Extract 4-digit year (19xx or 20xx)
    y_match = re.search(r'(20\d\d|19\d\d)', norm)
    year = int(y_match.group(1)) if y_match else 0

    # Extract month
    month = 0
    # Match longest phrase first (e.g. 'تشرين الاول' before 'تشرين')
    for name, m_val in sorted(MONTH_MAP.items(), key=lambda x: -len(x[0])):
        if name in norm:
            month = m_val
            break

    return (year, month)


def sanitize_filename(name):
    """Sanitizes topic name for use in Windows filenames."""
    if not name:
        return "بدون_موضوع"
    # Replace spaces with underscores
    clean = re.sub(r'[ \t]+', '_', str(name).strip())
    # Remove invalid Windows filename characters
    clean = re.sub(r'[\\/:*?"<>|]', '', clean)
    clean = clean.strip('._')
    return clean or "موضوع"


def generate_markdown_prompt(questions):
    """
    Generates ultra-token-efficient, clean plain-text prompt format
    with consecutive global question numbers (#01, #02...) ready for AI.
    """
    lines = []
    for q in questions:
        q_id = q.get("id") or ""
        topic = q.get("topic_name") or q.get("topic") or "الموضوع"
        title = q.get("title") or q.get("Question_Text") or ""
        correct_opt = q.get("correct_option", "")
        options = q.get("options", [])

        # Extract continuous global number from q_id (e.g. q_rheuma_07 -> #07)
        num_m = re.search(r'_(\d+)$', str(q_id))
        num_str = f"#{num_m.group(1)}" if num_m else f"#{q_id}"

        lines.append(f"{num_str} [{q_id}] ({topic})")
        lines.append(f"السؤال: {title}")
        lines.append(f"الجواب: {correct_opt}")
        for opt in options:
            let = opt.get("letter", "")
            txt = opt.get("text", "")
            is_corr = (let == correct_opt) or opt.get("is_correct", False)
            mark = " (الصحيح)" if is_corr else ""
            lines.append(f"{let}) {txt}{mark}")
        lines.append("---\n")

    return "\n".join(lines).strip()


def questions_to_dataframe(questions):
    """
    Converts questions list back into a DataFrame matching the TealMED CSV schema,
    including Question_ID for unambiguous matching.
    """
    rows = []
    for q in questions:
        options = q.get("options", [])
        corr_letter = q.get("correct_option", "")

        correct_text = ""
        wrong_texts = []
        for opt in options:
            if opt.get("is_correct") or (corr_letter and opt.get("letter") == corr_letter):
                correct_text = opt.get("text", "")
            else:
                wrong_texts.append(opt.get("text", ""))

        row = {
            "Question_ID": q.get("id", ""),
            "Medical_Subject": q.get("subject_name", ""),
            "Exam_Date": q.get("exam_period", ""),
            "Chapter_or_Section": q.get("topic_name", ""),
            "Question_Text": q.get("title", ""),
            "Explanation": q.get("explanation", ""),
            "High_Yield_Note": q.get("high_yield_note", "") or "",
            "Educational_Objective": q.get("educational_objective", "") or "",
            "Correct_Answer": correct_text
        }
        for i in range(1, 6):
            row[f"Wrong_Answer_{i}"] = wrong_texts[i - 1] if i - 1 < len(wrong_texts) else ""

        rows.append(row)

    return pd.DataFrame(rows)


def natural_sort_key(s):
    """Natural sort key so file_2 comes before file_10."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]


def detect_available_prefixes(directory):
    """
    Detects available prefixes in the directory or its json/ subdirectory.
    Returns dict: {prefix: [list of json files]}
    """
    p = Path(directory)
    prefixes = defaultdict(list)

    search_dirs = [p]
    if (p / "json").exists():
        search_dirs.append(p / "json")

    for s_dir in search_dirs:
        for f in s_dir.glob("*.json"):
            # Ignore compact AI files
            if "_ai." in f.name.lower():
                continue
            # Check pattern: {prefix}_{number}.json
            m = re.match(r'^([a-zA-Z0-9_\u0600-\u06FF]+?)_(\d+)\.json$', f.name)
            if m:
                prefix = m.group(1)
                prefixes[prefix].append(f)

    # Sort files inside each prefix
    for pref in prefixes:
        prefixes[pref].sort(key=lambda x: natural_sort_key(x.name))

    return dict(prefixes)


def select_files_gui(title="Select JSON File(s)"):
    """Opens native Windows file picker."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        file_paths = filedialog.askopenfilenames(
            title=title,
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        root.destroy()
        return list(file_paths)
    except Exception as e:
        print(f"Could not open GUI file dialog: {e}")
        return []


def run_topic_grouping_and_sorting(source_files, prefix, output_dir):
    """
    Merges questions from source_files, groups by topic, sorts chronologically,
    assigns globally continuous sequential numbers (#01..#NN) across all topics,
    and exports JSON, CSV, and AI Markdown files into dedicated subfolders (json/, csv/, md/).
    """
    output_dir = Path(output_dir)
    json_dir = output_dir / "json"
    csv_dir = output_dir / "csv"
    md_dir = output_dir / "md"

    json_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n1. Reading questions from {len(source_files)} source file(s)...")
    all_questions = []

    for fp in source_files:
        p = Path(fp)
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for q in data:
                    all_questions.append(q)
            print(f"  • Read {len(data)} questions from {p.name}")
        except Exception as e:
            print(f"  [!] Error reading {p.name}: {e}")

    total_q = len(all_questions)
    print(f"\nTotal merged questions: {total_q}")

    # Check and auto-apply topics.txt if available
    cur_dir = Path(__file__).resolve().parent
    topics_file = cur_dir / "topics.txt"
    if topics_file.exists():
        try:
            from topic_updater import load_topics_file, resolve_topic
            topic_map = load_topics_file(topics_file)
            if topic_map:
                applied_topics = 0
                for idx, q in enumerate(all_questions, start=1):
                    t = resolve_topic(q.get("id"), idx, 0, topic_map)
                    if t:
                        q["topic_name"] = t
                        applied_topics += 1
                if applied_topics > 0:
                    print(f"  • Auto-applied {applied_topics} topic mapping(s) from 'topics.txt'")
        except Exception as e:
            pass

    # 2. Group by topic
    topics_dict = defaultdict(list)
    for q in all_questions:
        t_name = str(q.get("topic_name") or q.get("topic") or "الموضوع").strip()
        topics_dict[t_name].append(q)

    print(f"Identified {len(topics_dict)} distinct topic(s):")
    for t_name, q_list in topics_dict.items():
        print(f"  • {t_name}: {len(q_list)} questions")

    # 3. Sort each topic's questions chronologically (newest exam session first)
    # and assign continuous global question numbers (1 to total_q) across topics
    print(f"\n2. Sorting chronologically (newest first) & assigning continuous global numbering...")

    pad_w = max(2, len(str(total_q)))
    pad_topics = max(2, len(str(len(topics_dict))))
    global_q_idx = 1
    exported_topics = []

    for topic_idx, (t_name, q_list) in enumerate(topics_dict.items(), start=1):
        # Sort by (year, month) descending
        q_list.sort(key=lambda q: parse_exam_date(q.get("exam_period")), reverse=True)

        topic_slug = sanitize_filename(t_name)
        start_topic_q = global_q_idx

        reindexed_questions = []
        for q in q_list:
            q_copy = dict(q)
            q_copy["original_id"] = q.get("id")
            num_str = str(global_q_idx).zfill(pad_w)
            q_copy["id"] = f"q_{prefix}_{num_str}"
            q_copy["topic_name"] = t_name
            reindexed_questions.append(q_copy)
            global_q_idx += 1

        end_topic_q = global_q_idx - 1

        # Target file names with sequential topic index (e.g. rheuma_01_TopicName)
        topic_num_str = str(topic_idx).zfill(pad_topics)
        base_name = f"{prefix}_{topic_num_str}_{topic_slug}"
        json_path = json_dir / f"{base_name}.json"
        csv_path = csv_dir / f"{base_name}.csv"
        md_path = md_dir / f"{base_name}_ai.md"

        # 1. Export JSON into json/
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(reindexed_questions, f, ensure_ascii=False, indent=2)

        # 2. Export CSV into csv/ (with Question_ID column)
        df = questions_to_dataframe(reindexed_questions)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # 3. Export AI Markdown prompt into md/
        md_content = generate_markdown_prompt(reindexed_questions)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        earliest_date = reindexed_questions[-1].get("exam_period") or "N/A"
        latest_date = reindexed_questions[0].get("exam_period") or "N/A"
        date_span = f"{latest_date} -> {earliest_date}" if latest_date != earliest_date else latest_date

        print(f"\n[OK] Topic #{topic_idx}: '{t_name}' ({len(reindexed_questions)} questions, Q#{start_topic_q}-#{end_topic_q}, {date_span})")
        print(f"     -> JSON: 'json/{json_path.name}'")
        print(f"     -> CSV:  'csv/{csv_path.name}'")
        print(f"     -> AI Prompt: 'md/{md_path.name}'")

        exported_topics.append({
            "topic": t_name,
            "count": len(reindexed_questions),
            "range": f"#{start_topic_q}-#{end_topic_q}",
            "files": [str(json_path), str(csv_path), str(md_path)]
        })

    return exported_topics


def main():
    parser = argparse.ArgumentParser(description="TealMED Topic Grouper & Chronological Sorter")
    parser.add_argument("--dir", "-d", type=str, help="Directory containing source chunk JSON files")
    parser.add_argument("--prefix", "-p", type=str, help="Subject prefix (e.g. 'hema', 'endo')")
    parser.add_argument("--out", "-o", type=str, help="Output directory for topic-grouped files")
    parser.add_argument("--auto", "-y", action="store_true", help="Run non-interactively")
    args = parser.parse_args()

    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print("\n" + "=" * 65)
    print(" TealMED Topic Grouper & Chronological Sorter Tool")
    print("=" * 65)

    cur_dir = Path(__file__).resolve().parent
    source_dir = Path(args.dir) if args.dir else (cur_dir / "output")

    if not source_dir.exists():
        print(f"[!] Source directory not found: {source_dir}")
        return

    # 1. Detect prefixes
    detected = detect_available_prefixes(source_dir)
    chosen_prefix = None
    target_files = []

    if args.prefix:
        chosen_prefix = args.prefix
        if chosen_prefix in detected:
            target_files = detected[chosen_prefix]
        else:
            search_paths = list(source_dir.glob(f"{chosen_prefix}_*.json"))
            if (source_dir / "json").exists():
                search_paths.extend((source_dir / "json").glob(f"{chosen_prefix}_*.json"))
            target_files = sorted(search_paths, key=natural_sort_key)
            target_files = [f for f in target_files if "_ai." not in f.name.lower()]
    elif detected:
        print(f"\nDetected subject prefixes in '{source_dir.name}':")
        prefix_list = list(detected.keys())
        for idx, pref in enumerate(prefix_list, start=1):
            print(f"  {idx}. '{pref}' ({len(detected[pref])} chunk files)")

        if args.auto or len(prefix_list) == 1:
            chosen_prefix = prefix_list[0]
            target_files = detected[chosen_prefix]
            print(f"\nAuto-selected prefix: '{chosen_prefix}'")
        else:
            choice_in = input(f"\nEnter number or name of prefix [Default: 1 ('{prefix_list[0]}')]: ").strip()
            if choice_in.isdigit() and 1 <= int(choice_in) <= len(prefix_list):
                chosen_prefix = prefix_list[int(choice_in) - 1]
            elif choice_in in detected:
                chosen_prefix = choice_in
            else:
                chosen_prefix = prefix_list[0]
            target_files = detected[chosen_prefix]

    if not target_files and not args.auto:
        print("\nSelect the JSON chunk files manually...")
        target_files = select_files_gui("Select Chunk JSON Files")
        if target_files:
            m = re.match(r'^([a-zA-Z0-9_\u0600-\u06FF]+?)_', Path(target_files[0]).name)
            chosen_prefix = m.group(1) if m else "subject"

    if not target_files:
        print("[!] No source files found. Exiting.")
        if not args.auto:
            input("\nPress Enter to exit...")
        return

    # 2. Destination output directory
    output_dir = Path(args.out) if args.out else (cur_dir / "classified")

    print(f"\nTarget prefix: '{chosen_prefix}' ({len(target_files)} chunk files)")
    print(f"Output directory: '{output_dir.resolve()}'")

    if not args.auto:
        ans = input("\nProceed with grouping and chronological sorting? (Y/n) [Default: Y]: ").strip().lower()
        if ans == 'n':
            print("Operation cancelled.")
            return

    # 3. Run processing
    exported = run_topic_grouping_and_sorting(target_files, chosen_prefix, output_dir)

    print("\n" + "=" * 65)
    print(f"Success! {len(exported)} topic(s) created in:")
    print(f"{output_dir.resolve()}")
    print("=" * 65)

    if not args.auto:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
