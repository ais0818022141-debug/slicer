"""
TealMED Unified Fast Slicer Pipeline
====================================
1. Splits raw medical question bank (Excel / CSV) into custom chunks (default: 12 rows).
2. Directly converts each chunk into production-grade TealMED JSON (.json).
3. Directly generates token-optimized AI Markdown prompt (_ai.md).
4. Maintains continuous sequential question IDs (q_prefix_01..NN) and headers (#01..#NN).
5. Output contains strictly: .csv, .json, and _ai.md (no useless _ai.json).
"""

import os
import sys
import re
import argparse
from pathlib import Path
import pandas as pd

# Add current directory to path to import converter & preparer helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tealmed_converter import parse_csv_to_tealmed_json, clean_prefix_string
from ai_preparer import generate_markdown_prompt


def select_file_gui():
    """Opens native Windows file picker to select an Excel or CSV file."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        file_path = filedialog.askopenfilename(
            title="TealMED Slicer - Select an Excel or CSV file",
            filetypes=[
                ("Excel and CSV Files", "*.xlsx *.xls *.csv"),
                ("Excel Files", "*.xlsx *.xls"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ]
        )
        root.destroy()
        return file_path
    except Exception as e:
        print(f"Could not open GUI file dialog: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(description="TealMED Unified Fast Slicer Pipeline")
    parser.add_argument("--file", "-f", type=str, help="Path to Excel or CSV file")
    parser.add_argument("--prefix", "-p", type=str, help="Subject prefix name (e.g. rheuma, hema)")
    parser.add_argument("--rows", "-r", type=int, default=12, help="Rows per file chunk (default: 12)")
    parser.add_argument("--out", "-o", type=str, help="Output directory (default: 'output')")
    parser.add_argument("--auto", "-y", action="store_true", help="Run non-interactively")
    args = parser.parse_args()

    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print("\n" + "=" * 65)
    print(" TealMED Unified Fast Slicer Pipeline")
    print(" (Splits CSV/Excel + Converts to TealMED JSON + Generates AI Prompts)")
    print("=" * 65)

    cur_dir = Path(__file__).resolve().parent

    # 1. Select Input File
    input_path = args.file
    if not input_path:
        print("Select an Excel or CSV file from the file picker...")
        input_path = select_file_gui()

    if not input_path or not Path(input_path).exists():
        print("[!] No valid file selected. Exiting.")
        if not args.auto:
            input("\nPress Enter to exit...")
        return

    input_file = Path(input_path).resolve()
    file_stem = input_file.stem
    print(f"\nSource file: '{input_file.name}'")

    # 2. Subject Prefix Name
    suggested_prefix = file_stem
    # If generic name like Book1 or Book2, suggest clean name if possible
    if re.match(r'^book\d+$', file_stem.lower()):
        suggested_prefix = "subject"

    if args.prefix:
        chosen_prefix = args.prefix
    elif args.auto:
        chosen_prefix = suggested_prefix
    else:
        p_in = input(f"Enter output prefix name (e.g. rheuma, hema, renal) [Default: '{suggested_prefix}']: ").strip()
        chosen_prefix = p_in if p_in else suggested_prefix

    clean_prefix = clean_prefix_string(chosen_prefix)

    # 3. Rows per Chunk
    rows_per_file = args.rows
    if not args.auto:
        r_in = input(f"Enter number of rows per file chunk [Default: {rows_per_file}]: ").strip()
        if r_in:
            try:
                val = int(r_in)
                if val > 0:
                    rows_per_file = val
            except ValueError:
                pass

    # 4. Output Directory and Subdirectories
    if args.out:
        output_dir = Path(args.out)
    else:
        output_dir = cur_dir / "output"

    csv_dir = output_dir / "csv"
    json_dir = output_dir / "json"
    md_dir = output_dir / "md"

    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: '{output_dir.resolve()}'")
    print(f"  - csv/  (CSV chunk files)")
    print(f"  - json/ (TealMED database JSON files)")
    print(f"  - md/   (AI prompt Markdown files)")

    # 5. Read the Excel or CSV file
    print("\nReading data file, please wait...")
    if input_file.suffix.lower() == '.csv':
        df = None
        for enc in ["utf-8-sig", "utf-8", "cp1256"]:
            try:
                df = pd.read_csv(input_file, encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        if df is None:
            print("[!] Could not decode CSV file.")
            return
    else:
        df = pd.read_excel(input_file)

    # Clean completely empty rows
    df = df.dropna(how='all')
    total_rows = len(df)
    total_files = (total_rows + rows_per_file - 1) // rows_per_file
    pad_width = max(2, len(str(total_files)))
    q_pad_width = max(2, len(str(total_rows)))

    print(f"Total valid question rows: {total_rows}")
    print(f"Splitting into {total_files} chunk(s) of ~{rows_per_file} questions each...\n")

    # 6. Process chunks: CSV, JSON, and AI Markdown
    current_q_start = 1

    for part_idx, start_row in enumerate(range(0, total_rows, rows_per_file), start=1):
        chunk_df = df.iloc[start_row : start_row + rows_per_file].copy()
        file_num_str = str(part_idx).zfill(pad_width)
        base_stem = f"{clean_prefix}_{file_num_str}"

        csv_path = csv_dir / f"{base_stem}.csv"
        json_path = json_dir / f"{base_stem}.json"
        md_path = md_dir / f"{base_stem}_ai.md"

        # 1. Export chunk CSV into csv/
        chunk_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # 2. Export TealMED JSON with continuous numbering into json/
        items, next_q_start = parse_csv_to_tealmed_json(
            csv_path=csv_path,
            output_json_path=json_path,
            id_prefix=clean_prefix,
            start_index=current_q_start,
            pad_width=q_pad_width
        )

        # 3. Export AI Markdown prompt into md/
        md_content = generate_markdown_prompt(items)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        first_id = items[0]["id"]
        last_id = items[-1]["id"]
        print(f"  [{file_num_str}/{total_files}] '{base_stem}': {len(items)} questions ({first_id} -> {last_id})")
        print(f"         CSV: 'csv/{csv_path.name}' | JSON: 'json/{json_path.name}' | AI Prompt: 'md/{md_path.name}'")

        current_q_start = next_q_start

    print("\n" + "=" * 65)
    print(f"Success! All {total_files} chunk(s) sliced and converted in:")
    print(f"{output_dir.resolve()}")
    print("Organized into subfolders: csv/, json/, and md/ (no _ai.json).")
    print("=" * 65)

    if not args.auto:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()