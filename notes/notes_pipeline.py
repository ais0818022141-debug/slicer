"""
TealMED Clinical Notes Pipeline
===============================
Interactive and CLI tool to batch-convert medical study notes (Markdown)
into platform-ready JSON and CSV files with 100% verbatim accuracy.

Usage:
  python notes_pipeline.py
  python notes_pipeline.py --file notes/notesEX.md
  python notes_pipeline.py --dir notes --subject "باطنة كلوية" --prefix nephro
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import List

# Add parent directory to path to ensure modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))
from notes_converter import (
    convert_markdown_file_to_notes,
    export_notes_to_json,
    export_notes_to_csv,
    detect_medical_subject
)


def select_files_gui(title="Select Markdown Notes", filetypes=None) -> List[str]:
    """Opens native Windows file picker to select one or more Markdown files."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        types = filetypes or [
            ("Markdown Notes", "*.md *.markdown *.txt"),
            ("All Files", "*.*")
        ]
        file_paths = filedialog.askopenfilenames(title=title, filetypes=types)
        root.destroy()
        return list(file_paths)
    except Exception as e:
        print(f"Could not open GUI file dialog: {e}")
        return []


def select_dir_gui(title="Select Notes Folder") -> str:
    """Opens native Windows folder picker."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        folder = filedialog.askdirectory(title=title)
        root.destroy()
        return folder
    except Exception as e:
        print(f"Could not open GUI folder dialog: {e}")
        return ""


def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="TealMED Clinical Notes Converter Pipeline")
    parser.add_argument("--file", "-f", nargs="*", help="Path to one or more Markdown notes files")
    parser.add_argument("--dir", "-d", type=str, help="Directory containing Markdown notes")
    parser.add_argument("--subject", "-s", type=str, help="Default subject name (e.g. باطنة كلوية)")
    parser.add_argument("--prefix", "-p", type=str, help="ID prefix (e.g. nephro, cardio)")
    parser.add_argument("--out", "-o", type=str, help="Output directory (default: 'notes/output')")
    parser.add_argument("--no-split", action="store_true", help="Do not split multi-part notes into separate items")
    parser.add_argument("--auto", "-y", action="store_true", help="Run non-interactively without prompts")
    args = parser.parse_args()

    print("\n" + "=" * 68)
    print(" 🩺 TealMED Clinical Notes Engine & Exporter (Verbatim Fidelity)")
    print("=" * 68)

    cur_dir = Path(__file__).resolve().parent

    # 1. Collect target files
    input_files: List[Path] = []
    if args.file:
        for f in args.file:
            p = Path(f)
            if p.is_file():
                input_files.append(p.resolve())
            elif p.is_dir():
                input_files.extend(sorted(p.glob("*.md")))
    elif args.dir:
        d = Path(args.dir)
        if d.is_dir():
            input_files.extend(sorted(d.glob("*.md")))

    if not input_files:
        print("\nSelect input mode:")
        print(" [1] Select one or more Markdown files (File Picker)")
        print(" [2] Scan entire folder for .md notes")
        choice = "1" if args.auto else input("Enter choice (1/2) [Default: 1]: ").strip() or "1"

        if choice == "2":
            folder = select_dir_gui("Select Notes Folder")
            if folder:
                input_files = sorted(Path(folder).glob("*.md"))
        else:
            files = select_files_gui("Select Markdown Notes (.md)")
            input_files = [Path(f).resolve() for f in files]

    # Filter out prompt/sample files if user selected folder
    ignored_stems = {"ai_question_prompt", "readme", "license", "package"}
    input_files = [
        f for f in input_files
        if f.is_file() and f.suffix.lower() in [".md", ".markdown", ".txt"]
        and f.stem.lower() not in ignored_stems
    ]

    if not input_files:
        print("\n[!] No valid Markdown files found or selected. Exiting.")
        if not args.auto:
            input("Press Enter to exit...")
        return

    print(f"\nFound {len(input_files)} file(s) to process:")
    for idx, f in enumerate(input_files, 1):
        print(f"  [{idx}] {f.name}")

    # 2. Output directory
    if args.out:
        out_dir = Path(args.out).resolve()
    else:
        out_dir = cur_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 3. Processing Notes
    all_notes = []
    split_parts = not args.no_split

    print("\nParsing notes with 100% verbatim logic...")
    for f in input_files:
        try:
            notes = convert_markdown_file_to_notes(
                file_path=f,
                default_subject=args.subject,
                id_prefix=args.prefix,
                split_parts=split_parts
            )
            print(f" ✔ Processed '{f.name}' -> Extracted {len(notes)} note(s)")
            all_notes.extend(notes)
        except Exception as e:
            print(f" [X] Error processing '{f.name}': {e}")

    if not all_notes:
        print("\n[!] No notes could be extracted. Exiting.")
        return

    # 4. Display Summary Table
    print("\n" + "-" * 68)
    print(f" Summary of Extracted Notes ({len(all_notes)} total):")
    print("-" * 68)
    for idx, n in enumerate(all_notes, 1):
        print(f" Note #{idx}:")
        print(f"   ID         : {n['id']}")
        print(f"   Title      : {n['title']}")
        print(f"   Subject    : {n['subject_name']} | Topic: {n['topic_name']}")
        print(f"   Difficulty : {n['difficulty']} | Free: {n['is_free']} | Official: {n['is_official']}")
        print(f"   Tags       : {', '.join(n['tags'])}")
        print(f"   Key Points : {len(n['key_points'])} extracted verbatim")
        print(f"   Content    : {len(n['content'])} chars (100% untouched)")
        print("-" * 68)

    # 5. Export Files
    json_path = out_dir / "notes.json"
    csv_path = out_dir / "notes.csv"
    csv_full_path = out_dir / "notes_full.csv"

    export_notes_to_json(all_notes, json_path)
    export_notes_to_csv(all_notes, csv_path, full_schema=False)
    export_notes_to_csv(all_notes, csv_full_path, full_schema=True)

    print("\n🎉 Export Completed Successfully!")
    print(f" 📂 Output Directory : {out_dir}")
    print(f" 📄 Platform JSON    : {json_path.name} ({json_path.stat().st_size:,} bytes)")
    print(f" 📊 Platform CSV     : {csv_path.name} ({csv_path.stat().st_size:,} bytes)")
    print(f" 📑 Full DB CSV      : {csv_full_path.name} ({csv_full_path.stat().st_size:,} bytes)")
    print("=" * 68)

    if not args.auto:
        input("\nPress Enter to finish...")


if __name__ == "__main__":
    main()
