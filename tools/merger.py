"""
TealMED File Merger Tool
========================
Combines multiple JSON or CSV files into a single unified file in exact sequential order.
- Prompts first for file type (JSON or CSV).
- Detects classified and output folders, or allows manual file selection.
- Merges questions in exact natural chronological/numerical order.
- Exports unified .json or .csv with clean utf-8 encoding.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
import pandas as pd


def natural_sort_key(s):
    """Natural sort key so file_2 comes before file_10."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]


def select_files_gui(title="Select Files to Combine", filetypes=None):
    """Opens native Windows file picker to select multiple files."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        types = filetypes or [("All Files", "*.*")]
        file_paths = filedialog.askopenfilenames(title=title, filetypes=types)
        root.destroy()
        return list(file_paths)
    except Exception as e:
        print(f"Could not open GUI file dialog: {e}")
        return []


def merge_json_files(file_paths, output_path):
    """
    Merges multiple JSON question lists into a single JSON array in exact order.
    """
    sorted_paths = sorted([Path(f) for f in file_paths], key=lambda p: natural_sort_key(p.name))
    combined_questions = []

    print(f"\nMerging {len(sorted_paths)} JSON files in order:")
    for idx, p in enumerate(sorted_paths, start=1):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                q_range = ""
                if data:
                    first_id = data[0].get("id", "N/A")
                    last_id = data[-1].get("id", "N/A")
                    q_range = f"({first_id} -> {last_id})"
                print(f"  {idx}. '{p.name}' - {len(data)} questions {q_range}")
                combined_questions.extend(data)
            else:
                print(f"  [!] Skipping {p.name}: does not contain a JSON array.")
        except Exception as e:
            print(f"  [!] Error reading {p.name}: {e}")

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(combined_questions, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Successfully merged {len(combined_questions)} questions into:")
    print(f"     '{out_p.resolve()}'")
    return len(combined_questions)


def merge_csv_files(file_paths, output_path):
    """
    Merges multiple CSV files into a single unified CSV in exact order.
    """
    sorted_paths = sorted([Path(f) for f in file_paths], key=lambda p: natural_sort_key(p.name))
    dfs = []

    print(f"\nMerging {len(sorted_paths)} CSV files in order:")
    for idx, p in enumerate(sorted_paths, start=1):
        df = None
        for enc in ["utf-8-sig", "utf-8", "cp1256"]:
            try:
                df = pd.read_csv(p, encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        if df is not None:
            q_col = next((c for c in df.columns if c.lower() in ["question_id", "id", "q_id"]), None)
            q_range = ""
            if q_col and len(df) > 0:
                q_range = f"({df.at[0, q_col]} -> {df.at[len(df)-1, q_col]})"
            print(f"  {idx}. '{p.name}' - {len(df)} rows {q_range}")
            dfs.append(df)
        else:
            print(f"  [!] Error reading CSV {p.name}")

    if not dfs:
        print("[!] No CSV data to merge.")
        return 0

    combined_df = pd.concat(dfs, ignore_index=True)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    combined_df.to_csv(out_p, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Successfully merged {len(combined_df)} rows into:")
    print(f"     '{out_p.resolve()}'")
    return len(combined_df)


def detect_prefix_from_files(files):
    """Extracts a common prefix from a list of files."""
    if not files:
        return "merged"
    first_name = Path(files[0]).stem
    # Match prefix like rheuma_01 or rheuma_01_topic
    m = re.match(r'^([a-zA-Z0-9_\u0600-\u06FF]+?)_\d+', first_name)
    if m:
        return m.group(1)
    parts = first_name.split("_")
    return parts[0] if parts else "merged"


def main():
    parser = argparse.ArgumentParser(description="TealMED File Merger Tool")
    parser.add_argument("--type", "-t", choices=["json", "csv"], help="File type to merge: 'json' or 'csv'")
    parser.add_argument("--dir", "-d", type=str, help="Directory containing files to merge")
    parser.add_argument("--out", "-o", type=str, help="Output file path")
    parser.add_argument("--auto", "-y", action="store_true", help="Run non-interactively")
    args = parser.parse_args()

    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print("\n" + "=" * 65)
    print(" TealMED File Merger Tool")
    print(" (Combines Multiple JSON or CSV Files in Exact Order)")
    print("=" * 65)

    cur_dir = Path(__file__).resolve().parent

    # 1. Ask for File Type
    file_type = args.type
    if not file_type:
        print("\nSelect the file format to combine:")
        print("  1. JSON (.json) [Default]")
        print("  2. CSV  (.csv)")
        if args.auto:
            file_type = "json"
        else:
            t_choice = input("\nEnter choice (1 or 2) [Default: 1]: ").strip()
            file_type = "csv" if t_choice == "2" else "json"

    ext = f".{file_type.lower()}"
    print(f"\nSelected format: {ext.upper()}")

    # 2. Select Files / Folder
    target_files = []
    if args.dir:
        p_dir = Path(args.dir)
        if p_dir.exists():
            target_files = [str(f) for f in p_dir.glob(f"*{ext}") if "_ai." not in f.name.lower()]
    else:
        # Detect relevant candidate folders
        candidates = [
            (f"classified/{file_type}", cur_dir / "classified" / file_type),
            (f"output/{file_type}", cur_dir / "output" / file_type),
            ("classified", cur_dir / "classified"),
            ("output", cur_dir / "output")
        ]

        available = []
        for label, c_dir in candidates:
            if c_dir.exists():
                files = [f for f in c_dir.glob(f"*{ext}") if "_ai." not in f.name.lower()]
                if files:
                    available.append((label, c_dir, files))

        if available:
            print(f"\nDetected directories with {ext.upper()} files:")
            for idx, (label, c_dir, files) in enumerate(available, start=1):
                print(f"  {idx}. '{label}' ({len(files)} {ext} files)")
            print(f"  {len(available) + 1}. Select files manually via file picker / folder path")

            if args.auto:
                target_files = [str(f) for f in available[0][2]]
                print(f"\nAuto-selected: '{available[0][0]}'")
            else:
                choice = input(f"\nEnter choice [Default: 1 ('{available[0][0]}')]: ").strip()
                if not choice or choice == "1":
                    target_files = [str(f) for f in available[0][2]]
                elif choice.isdigit() and 1 <= int(choice) <= len(available):
                    target_files = [str(f) for f in available[int(choice) - 1][2]]

    if not target_files and not args.auto:
        filter_name = f"{ext.upper()} Files"
        print(f"\nOpening file picker to select {ext.upper()} files...")
        target_files = select_files_gui(
            title=f"Select {ext.upper()} Files to Combine",
            filetypes=[(filter_name, f"*{ext}"), ("All Files", "*.*")]
        )
        if not target_files:
            manual_input = input(f"Or enter folder/file path containing {ext} files (or press Enter to exit): ").strip('"\' ')
            if manual_input:
                m_path = Path(manual_input)
                if m_path.is_dir():
                    target_files = [str(f) for f in m_path.glob(f"*{ext}") if "_ai." not in f.name.lower()]
                elif m_path.is_file():
                    target_files = [str(m_path)]

    if not target_files:
        print(f"[!] No {ext} files found to combine. Exiting.")
        if not args.auto:
            input("\nPress Enter to exit...")
        return

    # 3. Output File Name & Destination
    detected_prefix = detect_prefix_from_files(target_files)
    default_folder = "merged"
    default_out_name = f"{detected_prefix}_all{ext}"

    if args.out:
        final_output_path = Path(args.out)
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_folder = default_folder
        if not args.auto:
            folder_input = input(f"\nEnter destination folder name [Default: '{default_folder}']: ").strip()
            if folder_input:
                out_folder = folder_input

        target_dir = cur_dir / out_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        if args.auto:
            final_output_path = target_dir / default_out_name
        else:
            out_name_input = input(f"Enter output filename [Default: '{default_out_name}']: ").strip()
            chosen_name = out_name_input if out_name_input else default_out_name
            if not chosen_name.lower().endswith(ext):
                chosen_name += ext
            final_output_path = target_dir / chosen_name

    # 4. Perform Merge
    if ext == ".json":
        merge_json_files(target_files, final_output_path)
    else:
        merge_csv_files(target_files, final_output_path)

    print("\n" + "=" * 65)
    print("Success! Merged file is ready.")
    print("=" * 65)

    if not args.auto:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
