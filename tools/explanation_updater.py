"""
TealMED Clinical Explanations Batch Updater (Production-Grade)
=============================================================
Parses structured clinical explanations from text files:
- EDUCATIONAL OBJECTIVE
- HIGH YIELD NOTE
- EXPLANATION (strictly excluding any extra sections like CLINICAL ERROR FLAG)

And automatically updates:
- 'educational_objective'
- 'high_yield_note'
- 'explanation'
inside TealMED JSON database files (.json) and CSV files (.csv).

Supports ordered multi-file batches (e.g. 12 questions per file)
ensuring file 1 gets questions 1-12, file 2 gets 13-24, etc.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
import pandas as pd


def parse_explanations_text(text):
    """
    Parses structured explanation blocks from text.
    Extracts strictly:
      1. EDUCATIONAL OBJECTIVE
      2. HIGH YIELD NOTE
      3. EXPLANATION
    Any subsequent extra metadata (e.g. CLINICAL ERROR FLAG) is cleanly excluded.
    """
    mapping = {}
    # Split blocks by delimiter '---' or new question header '#...'
    raw_blocks = re.split(r'\n(?=\s*(?:#|###)\s*[0-9a-zA-Z_\[\]]+|\n\s*---\s*\n)', text)

    for b in raw_blocks:
        b = b.strip('- \t\r\n')
        if not b:
            continue

        # Extract question ID / number tokens from header lines (e.g. #01, #1, [q_renal_01], #01 [q_renal_01])
        header_part = "\n".join(b.splitlines()[:3])
        found_tokens = re.findall(r'\[([a-zA-Z0-9_-]+)\]|#([a-zA-Z0-9_-]+)', header_part)
        raw_ids = set()
        for tok_tuple in found_tokens:
            for tok in tok_tuple:
                if tok:
                    raw_ids.add(tok.lower().strip())

        if not raw_ids:
            id_m = re.search(r'(?:#|###)\s*\[?([a-zA-Z0-9_-]+)\]?', b)
            if id_m:
                raw_ids.add(id_m.group(1).lower().strip())

        if not raw_ids:
            continue

        # 1. Educational Objective
        obj_m = re.search(
            r'(?:EDUCATIONAL\s+OBJECTIVE|الهدف\s+التعليمي)\s*:\s*(.*?)(?=(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية|EXPLANATION|الشرح|التعليل)\s*:|$)',
            b, re.DOTALL | re.IGNORECASE
        )

        # 2. High Yield Note
        note_m = re.search(
            r'(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|نقطة\s+عالية\s+الأهمية)\s*:\s*(.*?)(?=(?:EXPLANATION|الشرح|التعليل)\s*:|$)',
            b, re.DOTALL | re.IGNORECASE
        )

        # 3. Explanation (stops at CLINICAL ERROR FLAG, any trailing flag header, or '---')
        exp_m = re.search(
            r'(?:EXPLANATION|الشرح|التعليل\s+السريري|التعليل)\s*:\s*(.*?)(?=(?:\n\s*CLINICAL\s+ERROR\s+FLAG|\n\s*[A-Z\s_]{3,}\s*:|\n\s*---|\Z))',
            b, re.DOTALL | re.IGNORECASE
        )

        obj = obj_m.group(1).strip() if obj_m else None
        note = note_m.group(1).strip() if note_m else None
        exp = exp_m.group(1).strip() if exp_m else None

        # Fallback cleaning in case flag was included
        if exp:
            exp = re.split(r'\n\s*CLINICAL\s+ERROR\s+FLAG', exp, flags=re.IGNORECASE)[0].strip()

        entry = {
            "educational_objective": obj,
            "high_yield_note": note,
            "explanation": exp
        }

        # Map all identified tokens
        for raw_id in raw_ids:
            mapping[raw_id] = entry
            if raw_id.isdigit():
                num = int(raw_id)
                mapping[num] = entry
                mapping[str(num)] = entry
                mapping[f"{num:02d}"] = entry
                mapping[f"{num:03d}"] = entry
            else:
                num_m = re.search(r'_(\d+)$', raw_id)
                if num_m:
                    num = int(num_m.group(1))
                    mapping[num] = entry
                    mapping[str(num)] = entry
                    mapping[f"{num:02d}"] = entry
                    mapping[f"{num:03d}"] = entry

    return mapping


def load_explanations_file(file_path):
    """Loads and parses explanations text file with encoding fallback."""
    p = Path(file_path)
    if not p.exists():
        return {}

    for enc in ["utf-8-sig", "utf-8", "cp1256"]:
        try:
            with open(p, "r", encoding=enc) as f:
                content = f.read()
            return parse_explanations_text(content)
        except UnicodeDecodeError:
            continue
    return {}


def resolve_explanation(q_id, local_idx, offset, exp_map):
    """
    Resolves the explanation entry for a question:
    1. Direct question ID match (e.g. 'q_rheuma_13')
    2. Global ID numeric suffix (e.g. 'q_rheuma_13' -> 13)
    3. File chunk offset + local question index (e.g. 12 + 1 = 13)
    4. Fallback to local index
    """
    if not exp_map:
        return None

    # Check direct ID match if provided
    if q_id:
        clean_id = str(q_id).strip().lower()
        if clean_id in exp_map:
            return exp_map[clean_id]

        # Extract numeric suffix from ID (e.g. q_rheuma_13 -> 13)
        num_m = re.search(r'_(\d+)$', clean_id)
        if num_m:
            id_num = int(num_m.group(1))
            if id_num in exp_map:
                return exp_map[id_num]

    # Expected global number if offset was specified
    expected_global = offset + local_idx if offset > 0 else local_idx
    if expected_global in exp_map:
        return exp_map[expected_global]

    # Fallback to local_idx
    if local_idx in exp_map:
        return exp_map[local_idx]

    return None


def update_json_file(file_path, exp_map, offset=0):
    """Updates educational_objective, high_yield_note, and explanation in JSON."""
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
        entry = resolve_explanation(q_id, idx, offset, exp_map)

        if entry:
            if entry["educational_objective"]:
                q["educational_objective"] = entry["educational_objective"]
            if entry["high_yield_note"]:
                q["high_yield_note"] = entry["high_yield_note"]
            if entry["explanation"]:
                q["explanation"] = entry["explanation"]
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
        range_info = f" (Questions #{min_q}-#{max_q})" if min_q != max_q else f" (Question #{min_q})"
    else:
        range_info = ""
    print(f"  [OK] {file_path.name}: Updated {updated}/{len(data)} explanations{range_info}.")
    return updated


def update_csv_file(file_path, exp_map, offset=0):
    """Updates Explanation column (and objectives/notes if columns exist) in CSV file."""
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

    # Locate Explanation and High_Yield_Note columns
    exp_col = None
    for c in df.columns:
        if c.lower() in ["explanation", "exp", "الشرح", "التفسير", "التعليل"]:
            exp_col = c
            break

    if not exp_col:
        exp_col = "Explanation"
        df[exp_col] = ""

    df[exp_col] = df[exp_col].astype(object)

    hy_col = None
    for c in df.columns:
        if c.lower() in ["high_yield_note", "high_yield", "الفكرة_من_السؤال", "الفكرة من السؤال", "نقطة عالية الأهمية", "نقطة_عالية_الأهمية"]:
            hy_col = c
            break

    if not hy_col:
        # Insert High_Yield_Note column right after Explanation column
        try:
            exp_loc = df.columns.get_loc(exp_col) + 1
            df.insert(exp_loc, "High_Yield_Note", "")
        except Exception:
            df["High_Yield_Note"] = ""
        hy_col = "High_Yield_Note"

    df[hy_col] = df[hy_col].astype(object)

    edu_col = None
    for c in df.columns:
        if c.lower() in ["educational_objective", "educational", "الهدف_من_السؤال", "الهدف من السؤال", "الهدف_التعليمي", "الهدف التعليمي"]:
            edu_col = c
            break

    if not edu_col:
        # Insert Educational_Objective column right after High_Yield_Note column
        try:
            hy_loc = df.columns.get_loc(hy_col) + 1
            df.insert(hy_loc, "Educational_Objective", "")
        except Exception:
            df["Educational_Objective"] = ""
        edu_col = "Educational_Objective"

    df[edu_col] = df[edu_col].astype(object)

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
        entry = resolve_explanation(q_id, local_idx, offset, exp_map)

        if entry:
            applied = False
            if entry.get("explanation"):
                df.at[idx, exp_col] = entry["explanation"]
                applied = True
            if entry.get("high_yield_note"):
                df.at[idx, hy_col] = entry["high_yield_note"]
                applied = True
            if entry.get("educational_objective"):
                df.at[idx, edu_col] = entry["educational_objective"]
                applied = True

            if applied:
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
        range_info = f" (Questions #{min_q}-#{max_q})" if min_q != max_q else f" (Question #{min_q})"
    else:
        range_info = ""
    print(f"  [OK] {file_path.name}: Updated {updated}/{len(df)} CSV explanations{range_info}.")
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

        types = filetypes or [("TealMED Files", "*.json *.csv"), ("JSON Files", "*.json"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
        file_paths = filedialog.askopenfilenames(title=title, filetypes=types)
        root.destroy()
        return list(file_paths)
    except Exception as e:
        print(f"Could not open GUI file dialog: {e}")
        return []


def run_batch_update(exp_map, target_files, questions_per_file=12):
    """
    Applies explanations across all target files.
    Works seamlessly on:
    1. Topic-classified files with variable question counts (matches strictly by question ID/number).
    2. Sliced chunk files with local numbering (uses chunk offset).
    """
    sorted_files = sorted([Path(f) for f in target_files], key=lambda p: natural_sort_key(p.name))
    print(f"\nProcessing {len(sorted_files)} file(s)...")

    total_updated = 0
    for p in sorted_files:
        ext = p.suffix.lower()
        if ext not in [".json", ".csv"]:
            continue

        # Check if this is an unsorted chunk file (e.g. hema_02.json) with local IDs 1..12
        chunk_num = 0
        chunk_m = re.match(r'^[a-zA-Z0-9_\u0600-\u06FF]+?_(\d+)\.(json|csv)$', p.name)
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
            total_updated += update_json_file(p, exp_map, offset=offset)
        elif ext == ".csv":
            total_updated += update_csv_file(p, exp_map, offset=offset)

    return total_updated


def main():
    parser = argparse.ArgumentParser(description="TealMED Clinical Explanations Batch Updater")
    parser.add_argument("--explanations", "-e", type=str, help="Path to explanations.txt file")
    parser.add_argument("--dir", "-d", type=str, help="Directory containing target files")
    parser.add_argument("--rows", "-r", type=int, default=12, help="Questions per file chunk (default: 12)")
    parser.add_argument("--auto", "-y", action="store_true", help="Run non-interactively")
    args = parser.parse_args()

    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print("\n" + "=" * 65)
    print(" TealMED Clinical Explanations Batch Updater (Production-Grade)")
    print("=" * 65)

    cur_dir = Path(__file__).resolve().parent
    default_exp_file = cur_dir / "explanations.txt"

    # 1. Load explanations mapping
    exp_map = {}
    if args.explanations:
        exp_map = load_explanations_file(args.explanations)
    elif default_exp_file.exists():
        print(f"Found default explanations file: '{default_exp_file.name}'")
        if args.auto:
            exp_map = load_explanations_file(default_exp_file)
        else:
            use_default = input("Load explanations from 'explanations.txt'? (Y/n) [Default: Y]: ").strip().lower()
            if use_default != 'n':
                exp_map = load_explanations_file(default_exp_file)

    if not exp_map:
        print("Select your explanations text file (.txt)...")
        picked = select_files_gui("Select Explanations Text File", [("Text Files", "*.txt"), ("All Files", "*.*")])
        if picked:
            exp_map = load_explanations_file(picked[0])

    if not exp_map:
        print("[!] No explanations loaded. Exiting.")
        if not args.auto:
            input("\nPress Enter to exit...")
        return

    numeric_keys = [k for k in exp_map.keys() if isinstance(k, int)]
    total_questions = max(numeric_keys) if numeric_keys else len(exp_map)
    print(f"Successfully loaded explanations for {total_questions} questions.")

    # 2. Target files selection
    target_files = []

    if args.dir:
        p_dir = Path(args.dir)
        if p_dir.exists():
            target_files = [str(f) for f in p_dir.glob("*") if f.suffix.lower() in [".json", ".csv"] and "_ai." not in f.name.lower()]
    else:
        # Detect candidate folders with classified (both JSON & CSV) as default option 1
        available = []
        classified_dir = cur_dir / "classified"
        if classified_dir.exists():
            class_files = [f for f in classified_dir.rglob("*") if f.suffix.lower() in [".json", ".csv"] and "_ai." not in f.name.lower()]
            if class_files:
                available.append(("classified (All JSON & CSV files)", classified_dir, class_files))

        sub_candidates = [
            ("classified/json", cur_dir / "classified" / "json"),
            ("classified/csv", cur_dir / "classified" / "csv"),
            ("output (All JSON & CSV files)", cur_dir / "output"),
            ("output/json", cur_dir / "output" / "json"),
            ("output/csv", cur_dir / "output" / "csv")
        ]
        for label, c_dir in sub_candidates:
            if c_dir.exists():
                is_all = "All" in label
                files = [f for f in (c_dir.rglob("*") if is_all else c_dir.glob("*")) if f.suffix.lower() in [".json", ".csv"] and "_ai." not in f.name.lower()]
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
        print("\nSelect JSON or CSV file(s) to update...")
        target_files = select_files_gui("Select Target Files", [
            ("Supported Files", "*.json *.csv"),
            ("JSON Files", "*.json"),
            ("CSV Files", "*.csv"),
            ("All Files", "*.*")
        ])

    if not target_files:
        print("No target files selected. Exiting.")
        if not args.auto:
            input("\nPress Enter to exit...")
        return

    # 3. Apply batch updates
    run_batch_update(exp_map, target_files, questions_per_file=args.rows)

    print("\n" + "=" * 65)
    print("Success! Clinical explanations, objectives, and high-yield notes updated!")
    print("=" * 65)
    if not args.auto:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
