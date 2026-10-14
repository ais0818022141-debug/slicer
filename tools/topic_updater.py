"""
TealMED Topic Updater Tool (Production-Grade)
============================================
Reads topic mappings from text files (in the user's standard format)
and automatically updates topics in:
- TealMED database JSON files (.json)
- Compact AI JSON files (_ai.json)
- Markdown prompt files (_ai.md / .md)
- Medical questions CSV files (.csv)

Supports ordered multi-file batches (e.g. 12 questions per file)
ensuring that file 1 receives topics 1-12, file 2 receives 13-24, etc.,
and companion files for each part stay perfectly synchronized.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
import pandas as pd


def clean_topic_string(raw_text):
    """Cleans asterisks, markdown tags, and parenthetical notes from topic text."""
    if not raw_text:
        return ""
    text = str(raw_text).strip()
    # Remove notes like *(ملاحظة)* or (ملاحظة)
    text = re.sub(r'\*\(.*?\)\*', '', text).strip()
    text = re.sub(r'\(.*?\)$', '', text).strip()
    # Strip all markdown asterisks and underscores
    text = text.replace('*', '').replace('_', '')
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text


def parse_topics_from_text(text):
    """
    Parses topic mappings from text supporting formats such as:
    #01 [q_ent_001] أمراض الحنجرة واضطرابات الصوت والأورام
    1. **[q_renal_01]**: التهابات المسالك وأمراض البروستات
    [q_renal_01]: اسم الموضوع
    q_renal_01: اسم الموضوع
    1. اسم الموضوع
    1. **اسم الموضوع**
    """
    mapping = {}
    lines = text.splitlines()

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        # Ignore markdown section headers like '## Topics' or '# Comments' that do NOT contain a number or q_ ID
        if re.match(r'^#{1,6}\s+[a-zA-Z\u0600-\u06FF]', line) and not re.search(r'\[?q_[a-zA-Z0-9_-]+\]?', line):
            continue

        # Pattern 0: User's format: #01 [q_ent_001] Topic or #01 [q_ent_001]: Topic
        m_hash_id = re.match(r'^#?(\d+)\s*\[(q_[a-zA-Z0-9_-]+)\]\s*[:\-]?\s*(.+)$', line)
        if m_hash_id:
            num = int(m_hash_id.group(1))
            q_id = m_hash_id.group(2).strip().lower()
            clean_topic = clean_topic_string(m_hash_id.group(3))
            if clean_topic:
                mapping[q_id] = clean_topic
                mapping[num] = clean_topic
                mapping[str(num)] = clean_topic
            continue

        # Pattern 1: ID-based (e.g. 1. **[q_renal_01]**: Topic or [q_renal_01]: Topic)
        m_id = re.search(r'\[?(q_[a-zA-Z0-9_-]+)\]?\s*\*{0,2}\s*[:\-]?\s*(.+)$', line)
        if m_id:
            q_id = m_id.group(1).strip().lower()
            clean_topic = clean_topic_string(m_id.group(2))
            if clean_topic:
                mapping[q_id] = clean_topic

                num_m = re.search(r'_(\d+)$', q_id)
                if num_m:
                    num_val = int(num_m.group(1))
                    mapping[num_val] = clean_topic
                    mapping[str(num_val)] = clean_topic
            continue

        # Pattern 2: Number-based (e.g. #01 Topic or 1. Topic or 1: Topic or 1) Topic)
        m_num = re.match(r'^#?(\d+)[\.\:\-\)\s]\s*(.+)$', line)
        if m_num:
            num = int(m_num.group(1))
            clean_topic = clean_topic_string(m_num.group(2))
            if clean_topic:
                mapping[num] = clean_topic
                mapping[str(num)] = clean_topic
            continue

        # Pattern 3: Fallback unnumbered line
        cleaned = clean_topic_string(line)
        if cleaned and idx not in mapping:
            mapping[idx] = cleaned
            mapping[str(idx)] = cleaned

    return mapping


def load_topics_file(file_path):
    """Loads and parses a topics text file."""
    p = Path(file_path)
    if not p.exists():
        return {}

    for enc in ["utf-8-sig", "utf-8", "cp1256"]:
        try:
            with open(p, "r", encoding=enc) as f:
                content = f.read()
            return parse_topics_from_text(content)
        except UnicodeDecodeError:
            continue
    return {}


def resolve_topic(q_id, local_idx, offset, topic_map):
    """
    Resolves the exact topic for a question based on:
    1. Direct question ID string (e.g. 'q_rheuma_03')
    2. Global ID numeric suffix (e.g. 'q_rheuma_03' -> 3)
    3. File chunk offset + local question index (e.g. 12 + 1 = 13)
    4. Fallback to local index
    """
    if not topic_map:
        return None

    # Check direct ID match if provided
    if q_id:
        clean_id = str(q_id).strip().lower()
        if clean_id in topic_map:
            return topic_map[clean_id]

        num_m = re.search(r'_(\d+)$', clean_id)
        if num_m:
            id_num = int(num_m.group(1))
            if id_num in topic_map:
                return topic_map[id_num]

    expected_global = offset + local_idx if offset > 0 else local_idx
    if expected_global in topic_map:
        return topic_map[expected_global]

    if local_idx in topic_map:
        return topic_map[local_idx]

    return None


def update_json_file(file_path, topic_map, offset=0):
    """Updates topic_name / topic inside a JSON file."""
    file_path = Path(file_path)
    if not file_path.exists():
        return 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Could not read JSON {file_path.name}: {e}")
        return 0

    if not isinstance(data, list):
        return 0

    updated = 0
    matched_q_nums = []

    for idx, q in enumerate(data, start=1):
        q_id = str(q.get("id", "")).strip().lower()
        new_topic = resolve_topic(q_id, idx, offset, topic_map)

        if new_topic:
            if "topic_name" in q:
                q["topic_name"] = new_topic
            if "topic" in q:
                q["topic"] = new_topic
            if "topic_name" not in q and "topic" not in q:
                q["topic_name"] = new_topic
            updated += 1

            num_m = re.search(r'_(\d+)$', q_id)
            if num_m:
                matched_q_nums.append(int(num_m.group(1)))
            else:
                matched_q_nums.append(offset + idx)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if matched_q_nums:
        min_q = min(matched_q_nums)
        max_q = max(matched_q_nums)
        range_info = f" (Topics #{min_q}-#{max_q})" if min_q != max_q else f" (Topic #{min_q})"
    else:
        range_info = ""
    print(f"  [OK] {file_path.name}: Updated {updated}/{len(data)} topics{range_info}.")
    return updated


def update_markdown_file(file_path, topic_map, offset=0):
    """
    Updates topic tags in a Markdown file.
    Supports formats:
      #01 [q_endo_01] (الموضوع)
      #97 [q_endo_97] (الموضوع)
      #01 (الموضوع)
      ### [q_endo_01] (الموضوع)
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[!] Could not read MD {file_path.name}: {e}")
        return 0

    header_pattern = re.compile(r'^(#{0,3}\s*#?\d*\s*\[([^\]]+)\]\s*)\((.*?)\)(.*)$')
    num_only_pattern = re.compile(r'^(#{0,3}\s*#?(\d+)\s*)\((.*?)\)(.*)$')

    updated = 0
    matched_q_nums = []
    local_idx = 0
    new_lines = []

    for line in lines:
        m = header_pattern.match(line)
        if m:
            local_idx += 1
            prefix = m.group(1)
            q_id = m.group(2).strip().lower()
            suffix = m.group(4)

            new_topic = resolve_topic(q_id, local_idx, offset, topic_map)
            if new_topic:
                new_lines.append(f"{prefix}({new_topic}){suffix}\n")
                updated += 1
                num_m = re.search(r'_(\d+)$', q_id)
                if num_m:
                    matched_q_nums.append(int(num_m.group(1)))
                else:
                    matched_q_nums.append(offset + local_idx)
                continue
        else:
            m2 = num_only_pattern.match(line)
            if m2:
                local_idx += 1
                prefix = m2.group(1)
                q_num_str = m2.group(2)
                suffix = m2.group(4)

                new_topic = resolve_topic(q_num_str, local_idx, offset, topic_map)
                if new_topic:
                    new_lines.append(f"{prefix}({new_topic}){suffix}\n")
                    updated += 1
                    matched_q_nums.append(int(q_num_str))
                    continue

        new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    if matched_q_nums:
        min_q = min(matched_q_nums)
        max_q = max(matched_q_nums)
        range_info = f" (Topics #{min_q}-#{max_q})" if min_q != max_q else f" (Topic #{min_q})"
    else:
        range_info = ""
    print(f"  [OK] {file_path.name}: Updated {updated} topic headers{range_info}.")
    return updated


def update_csv_file(file_path, topic_map, offset=0):
    """Updates Chapter_or_Section topic column in CSV file."""
    file_path = Path(file_path)
    if not file_path.exists():
        return 0

    df = None
    for enc in ["utf-8-sig", "utf-8", "cp1256"]:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    if df is None:
        print(f"[!] Could not read CSV {file_path.name}")
        return 0

    # Determine topic column name
    topic_col = None
    for candidate in ["Chapter_or_Section", "topic_name", "topic", "chapter"]:
        for c in df.columns:
            if c.lower() == candidate.lower():
                topic_col = c
                break
        if topic_col:
            break

    if not topic_col:
        topic_col = "Chapter_or_Section"
        df.insert(2 if len(df.columns) >= 2 else len(df.columns), topic_col, "")
    df[topic_col] = df[topic_col].astype(object)

    id_col = None
    for c in df.columns:
        if c.lower() in ["question_id", "id", "q_id"]:
            id_col = c
            break

    updated = 0
    matched_q_nums = []

    for idx in range(len(df)):
        local_idx = idx + 1
        q_id = str(df.at[idx, id_col]).strip() if id_col and pd.notna(df.at[idx, id_col]) else None
        new_topic = resolve_topic(q_id, local_idx, offset, topic_map)

        if new_topic:
            df.at[idx, topic_col] = new_topic
            updated += 1

            num_m = re.search(r'_(\d+)$', str(q_id)) if q_id else None
            if num_m:
                matched_q_nums.append(int(num_m.group(1)))
            else:
                matched_q_nums.append(offset + local_idx)

    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    if matched_q_nums:
        min_q = min(matched_q_nums)
        max_q = max(matched_q_nums)
        range_info = f" (Topics #{min_q}-#{max_q})" if min_q != max_q else f" (Topic #{min_q})"
    else:
        range_info = ""
    print(f"  [OK] {file_path.name}: Updated {updated}/{len(df)} rows{range_info}.")
    return updated


def natural_sort_key(s):
    """Natural sort key helper so 'file_2' comes before 'file_10'."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]


def select_files_gui(title="Select File(s)", filetypes=None):
    """Opens native Windows file picker."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        types = filetypes or [("Supported Files", "*.json *.md *.csv"), ("All Files", "*.*")]
        file_paths = filedialog.askopenfilenames(title=title, filetypes=types)
        root.destroy()
        return list(file_paths)
    except Exception as e:
        print(f"Could not open GUI file dialog: {e}")
        return []


def run_batch_update(topic_map, target_files, questions_per_file=12):
    """
    Applies topics across all target files.
    Works seamlessly on topic files (variable count) and sliced chunk files.
    """
    sorted_files = sorted([Path(f) for f in target_files], key=lambda p: natural_sort_key(p.name))
    print(f"\nProcessing {len(sorted_files)} file(s)...")

    total_updated = 0
    for p in sorted_files:
        ext = p.suffix.lower()
        if ext not in [".json", ".md", ".csv"]:
            continue

        chunk_num = 0
        chunk_m = re.match(r'^[a-zA-Z0-9_\u0600-\u06FF]+?_(\d+)(_ai)?\.(json|md|csv)$', p.name)
        if chunk_m:
            chunk_num = int(chunk_m.group(1))

        offset = 0
        if chunk_num > 1 and questions_per_file > 0:
            has_local_id = False
            if ext == ".json":
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        j_data = json.load(f)
                    if isinstance(j_data, list) and j_data:
                        first_id = str(j_data[0].get("id", ""))
                        num_m = re.search(r'_(\d+)$', first_id)
                        if num_m and int(num_m.group(1)) == 1:
                            has_local_id = True
                except Exception:
                    pass
            elif ext == ".csv":
                try:
                    df = pd.read_csv(p, nrows=2)
                    id_col = next((c for c in df.columns if c.lower() in ["question_id", "id", "q_id"]), None)
                    if id_col:
                        val = str(df.at[0, id_col])
                        num_m = re.search(r'_(\d+)$', val)
                        if num_m and int(num_m.group(1)) == 1:
                            has_local_id = True
                    else:
                        has_local_id = True
                except Exception:
                    pass

            if has_local_id:
                offset = (chunk_num - 1) * questions_per_file

        if ext == ".json":
            total_updated += update_json_file(p, topic_map, offset=offset)
        elif ext == ".md":
            total_updated += update_markdown_file(p, topic_map, offset=offset)
        elif ext == ".csv":
            total_updated += update_csv_file(p, topic_map, offset=offset)

    return total_updated


def main():
    parser = argparse.ArgumentParser(description="TealMED Topic Batch Updater")
    parser.add_argument("--topics", "-t", type=str, help="Path to topics.txt file")
    parser.add_argument("--dir", "-d", type=str, help="Directory containing target files")
    parser.add_argument("--rows", "-r", type=int, default=12, help="Questions per file chunk (default: 12)")
    parser.add_argument("--auto", "-y", action="store_true", help="Run non-interactively")
    args = parser.parse_args()

    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print("\n" + "=" * 60)
    print(" TealMED Topic Batch Updater (Production-Grade)")
    print("=" * 60)

    cur_dir = Path(__file__).resolve().parent
    default_topics_file = cur_dir / "topics.txt"

    # 1. Load Topic Mappings
    topic_map = {}
    if args.topics:
        topic_map = load_topics_file(args.topics)
    elif default_topics_file.exists():
        print(f"Found default topics file: '{default_topics_file.name}'")
        if args.auto:
            topic_map = load_topics_file(default_topics_file)
        else:
            use_default = input("Load topics from 'topics.txt'? (Y/n) [Default: Y]: ").strip().lower()
            if use_default != 'n':
                topic_map = load_topics_file(default_topics_file)

    if not topic_map:
        print("Please select your topics text file (.txt)...")
        picked_topic_files = select_files_gui("Select Topics Text File", [("Text Files", "*.txt"), ("All Files", "*.*")])
        if picked_topic_files:
            topic_map = load_topics_file(picked_topic_files[0])

    if not topic_map:
        print("[!] No topics mapping found. Exiting.")
        if not args.auto:
            input("\nPress Enter to exit...")
        return

    unique_topics = set(topic_map.values())
    numeric_keys = [k for k in topic_map.keys() if isinstance(k, int)]
    total_questions_mapped = max(numeric_keys) if numeric_keys else len(topic_map)
    print(f"Successfully loaded {len(topic_map)} mappings covering {total_questions_mapped} questions ({len(unique_topics)} unique topics).")

    # 2. Target files selection
    target_files = []

    if args.dir:
        p_dir = Path(args.dir)
        if p_dir.exists():
            target_files = [str(f) for f in p_dir.glob("*") if f.suffix.lower() in [".json", ".md", ".csv"] and "_ai.json" not in f.name.lower()]
    else:
        # Detect candidate folders with classified (All JSON, CSV & MD) as default option 1
        available = []
        classified_dir = cur_dir / "classified"
        if classified_dir.exists():
            class_files = [f for f in classified_dir.rglob("*") if f.suffix.lower() in [".json", ".md", ".csv"] and "_ai.json" not in f.name.lower()]
            if class_files:
                available.append(("classified (All JSON, CSV & MD files)", classified_dir, class_files))

        sub_candidates = [
            ("classified/json", cur_dir / "classified" / "json"),
            ("classified/csv", cur_dir / "classified" / "csv"),
            ("classified/md", cur_dir / "classified" / "md"),
            ("output (All JSON, CSV & MD files)", cur_dir / "output"),
            ("output/json", cur_dir / "output" / "json"),
            ("output/csv", cur_dir / "output" / "csv"),
            ("output/md", cur_dir / "output" / "md")
        ]
        for label, c_dir in sub_candidates:
            if c_dir.exists():
                is_all = "All" in label
                files = [f for f in (c_dir.rglob("*") if is_all else c_dir.glob("*")) if f.suffix.lower() in [".json", ".md", ".csv"] and "_ai.json" not in f.name.lower()]
                if files:
                    available.append((label, c_dir, files))

        if available:
            print("\nDetected target directories:")
            for idx, (rel, path, files) in enumerate(available, start=1):
                exts = ", ".join(sorted(set(f.suffix for f in files)))
                print(f"  {idx}. '{rel}' ({len(files)} files: {exts})")
            print(f"  {len(available) + 1}. Select file(s) manually via file picker")

            if args.auto:
                target_files = [str(f) for f in available[0][2]]
                print(f"\nAuto-selected: '{available[0][0]}'")
            else:
                choice = input(f"\nEnter choice [Default: 1 ('{available[0][0]}')]: ").strip()
                if not choice or choice == "1":
                    target_files = [str(f) for f in available[0][2]]
                elif choice.isdigit() and 1 <= int(choice) <= len(available):
                    target_files = [str(f) for f in available[int(choice) - 1][2]]

    if not target_files:
        print("\nSelect JSON, Markdown, or CSV file(s) to update...")
        target_files = select_files_gui("Select Files to Update Topics", [
            ("Supported Files", "*.json *.md *.csv"),
            ("JSON Files", "*.json"),
            ("Markdown Files", "*.md"),
            ("CSV Files", "*.csv"),
            ("All Files", "*.*")
        ])

    if not target_files:
        print("No target files selected. Exiting.")
        if not args.auto:
            input("\nPress Enter to exit...")
        return

    # 3. Run update
    run_batch_update(topic_map, target_files, questions_per_file=args.rows)

    print("\n" + "=" * 60)
    print("Success! All target files have been updated with their exact topics.")
    print("=" * 60)
    if not args.auto:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
