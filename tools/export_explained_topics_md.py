#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TealMED Explained Topics Markdown Exporter
==========================================
Generates unified Markdown question banks with clinical explanations:
1. Combined Master File: '<subject>_all_explained.md' containing all questions with
   options, correct answers, and clinical explanations (Educational Objective,
   High Yield Note, Explanation).
2. Per-Topic Files: Splits questions by topic into '<subject>_all_<topic>.md' files,
   each placed inside a dedicated 'topics_md/' subfolder.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from collections import OrderedDict

# Enforce UTF-8 for Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent


def sanitize_filename(name: str) -> str:
    """Sanitizes topic name for use in Windows filenames while preserving Arabic characters."""
    if not name:
        return "بدون_موضوع"
    # Replace non-word and non-Arabic characters with underscores
    clean = re.sub(r'[^\w\u0600-\u06FF]+', '_', str(name).strip())
    clean = clean.strip('._')
    return clean or "موضوع"


def format_single_question_markdown(q: dict, idx: int, padding: int = 2) -> str:
    """
    Formats a single question and its clinical explanations into the standardized
    TealMED Markdown format matching '<subject>_all_ai.md' with explanations appended.
    """
    q_id = q.get("id") or f"q_{idx:02d}"
    topic = q.get("topic_name") or q.get("topic") or "الموضوع"
    title = (q.get("title") or q.get("Question_Text") or "").strip()
    correct_opt = (q.get("correct_option") or "").strip().upper()
    options = q.get("options", [])

    # Extract sequential number if available in q_id (e.g. q_cardio_01 -> 01)
    num_m = re.search(r'_(\d+)$', str(q_id))
    if num_m:
        num_val = int(num_m.group(1))
        num_str = f"#{num_val:0{padding}d}"
    else:
        num_str = f"#{idx:0{padding}d}"

    lines = []
    lines.append(f"{num_str} [{q_id}] ({topic})")
    lines.append(f"السؤال: {title}")
    lines.append(f"الجواب: {correct_opt}")

    for opt in options:
        let = (opt.get("letter") or "").strip().upper()
        txt = (opt.get("text") or "").strip()
        is_corr = (let == correct_opt) or opt.get("is_correct", False)
        mark = " (الصحيح)" if is_corr else ""
        lines.append(f"{let}) {txt}{mark}")

    # Clinical Explanation Sections
    obj = (q.get("educational_objective") or "").strip()
    note = (q.get("high_yield_note") or "").strip()
    exp = (q.get("explanation") or "").strip()

    if obj or note or exp:
        lines.append("")
        if obj:
            lines.append("EDUCATIONAL OBJECTIVE:")
            lines.append(obj)
            lines.append("")
        if note:
            lines.append("HIGH YIELD NOTE:")
            lines.append(note)
            lines.append("")
        if exp:
            lines.append("EXPLANATION:")
            lines.append(exp)

    lines.append("---")
    return "\n".join(lines)


def export_subject_explained_topics(
    subject_dir: Path,
    subfolder_name: str = "topics_md",
    verbose: bool = True
) -> dict:
    """
    Processes a single subject folder inside final/:
    1. Loads '<subject>_all.json'
    2. Writes '<subject>_all_explained.md' in 'topics_md/'
    3. Groups questions by topic and writes '<subject>_all_<topic>.md'
    """
    subject_dir = Path(subject_dir).resolve()
    if not subject_dir.is_dir():
        raise FileNotFoundError(f"Subject directory not found: {subject_dir}")

    # Find the master json file (e.g. cardio_all.json)
    json_candidates = list(subject_dir.glob("*_all.json"))
    if not json_candidates:
        # Fallback to any .json file with subject prefix
        json_candidates = [f for f in subject_dir.glob("*.json") if not f.name.endswith("_ai.json")]

    if not json_candidates:
        raise FileNotFoundError(f"No valid JSON question bank found in {subject_dir}")

    json_file = json_candidates[0]
    stem = json_file.stem  # e.g. cardio_all

    with open(json_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if not isinstance(questions, list):
        raise ValueError(f"Expected JSON array in {json_file.name}, got {type(questions)}")

    total_q = len(questions)
    padding = 3 if total_q >= 100 else 2

    # Prepare output directory: final/<subject>/topics_md/
    out_dir = subject_dir / subfolder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Combined Master File: <stem>_explained.md
    master_lines = []
    topics_map = OrderedDict()

    for idx, q in enumerate(questions, start=1):
        q_md = format_single_question_markdown(q, idx=idx, padding=padding)
        master_lines.append(q_md)
        master_lines.append("")  # Empty line between blocks

        top_name = (q.get("topic_name") or q.get("topic") or "بدون_موضوع").strip()
        topics_map.setdefault(top_name, []).append((idx, q))

    master_content = "\n".join(master_lines).strip() + "\n"
    master_file = out_dir / f"{stem}_explained.md"
    with open(master_file, "w", encoding="utf-8") as f:
        f.write(master_content)

    # 2. Generate per-topic Markdown files
    topic_files_created = []
    questions_in_topics_count = 0

    for topic_name, q_list in topics_map.items():
        clean_topic = sanitize_filename(topic_name)
        topic_file = out_dir / f"{stem}_{clean_topic}.md"

        topic_lines = []
        for idx, q in q_list:
            q_md = format_single_question_markdown(q, idx=idx, padding=padding)
            topic_lines.append(q_md)
            topic_lines.append("")

        topic_content = "\n".join(topic_lines).strip() + "\n"
        with open(topic_file, "w", encoding="utf-8") as f:
            f.write(topic_content)

        topic_files_created.append(topic_file)
        questions_in_topics_count += len(q_list)

    # Clean up stale per-topic md files
    valid_names = {f.name for f in topic_files_created}
    valid_names.add(master_file.name)
    for old_file in out_dir.glob(f"{stem}_*.md"):
        if old_file.name not in valid_names:
            try:
                old_file.unlink()
            except Exception:
                pass

    stats = {
        "subject": subject_dir.name,
        "total_questions": total_q,
        "topics_count": len(topics_map),
        "topic_files_count": len(topic_files_created),
        "master_file": str(master_file),
        "output_dir": str(out_dir),
        "integrity_verified": (total_q == questions_in_topics_count)
    }

    if verbose:
        print(f"[OK] {subject_dir.name:20}: {total_q} questions -> Master file + {len(topic_files_created)} topic files in {subfolder_name}/")

    return stats


def export_all_final_subjects(
    final_dir: Path = None,
    subfolder_name: str = "topics_md",
    target_subject: str = None,
    verbose: bool = True
):
    """
    Scans the final/ directory and exports explained topics for all subjects
    or for a single requested subject.
    """
    if final_dir is None:
        final_dir = BASE_DIR / "final"
    final_dir = Path(final_dir).resolve()

    if not final_dir.is_dir():
        print(f"[!] final directory not found: {final_dir}")
        return []

    if target_subject:
        subj_path = final_dir / target_subject
        if not subj_path.is_dir():
            print(f"[!] Subject '{target_subject}' not found in {final_dir}")
            return []
        subject_dirs = [subj_path]
    else:
        subject_dirs = sorted([d for d in final_dir.iterdir() if d.is_dir()])

    print(f"=== TealMED Explained Topics Markdown Exporter ===")
    print(f"Target: {'All Subjects (' + str(len(subject_dirs)) + ')' if not target_subject else target_subject}")
    print(f"Subfolder: {subfolder_name}/")
    print("-" * 65)

    results = []
    total_all_q = 0
    total_all_topics = 0

    for s_dir in subject_dirs:
        try:
            res = export_subject_explained_topics(s_dir, subfolder_name=subfolder_name, verbose=verbose)
            results.append(res)
            total_all_q += res["total_questions"]
            total_all_topics += res["topic_files_count"]
        except Exception as e:
            print(f"[!] Error processing {s_dir.name}: {e}")

    print("-" * 65)
    print(f"Completed: {len(results)} subjects processed.")
    print(f"Total Questions: {total_all_q} | Total Topic Markdown Files: {total_all_topics}")
    print(f"All files exported into '<subject>/{subfolder_name}/'")
    return results


def launch_gui():
    """Simple Tkinter GUI wrapper for the exporter."""
    import tkinter as tk
    from tkinter import ttk, messagebox

    root = tk.Tk()
    root.title("TealMED Explained Topics Exporter")
    root.geometry("620x450")
    root.configure(bg="#F8FAFC")

    # Header Frame
    header_frame = tk.Frame(root, bg="#1E293B", padx=20, pady=16)
    header_frame.pack(fill="x")

    tk.Label(
        header_frame,
        text="TealMED Explained Topics Markdown Exporter",
        font=("Segoe UI", 13, "bold"),
        fg="#FFFFFF",
        bg="#1E293B"
    ).pack(anchor="w")

    tk.Label(
        header_frame,
        text="Exports all questions + clinical explanations, partitioned by topic into topics_md/",
        font=("Segoe UI", 9),
        fg="#94A3B8",
        bg="#1E293B"
    ).pack(anchor="w")

    # Content Frame
    content = tk.Frame(root, bg="#F8FAFC", padx=20, pady=20)
    content.pack(fill="both", expand=True)

    final_path = BASE_DIR / "final"
    subjects = []
    if final_path.is_dir():
        subjects = sorted([d.name for d in final_path.iterdir() if d.is_dir()])

    # Subject Selection
    tk.Label(content, text="Select Target:", font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155").pack(anchor="w")
    target_var = tk.StringVar(value="-- ALL 23 SUBJECTS --")
    options = ["-- ALL 23 SUBJECTS --"] + subjects
    combo = ttk.Combobox(content, textvariable=target_var, values=options, state="readonly", width=35, font=("Segoe UI", 10))
    combo.pack(anchor="w", pady=(4, 15))

    # Log text box
    log_box = tk.Text(content, wrap="word", height=10, font=("Consolas", 9), bg="#FFFFFF", fg="#1E293B", relief="solid", bd=1)
    log_box.pack(fill="both", expand=True, pady=(0, 15))

    def run_process():
        sel = target_var.get()
        target = None if sel == "-- ALL 23 SUBJECTS --" else sel
        log_box.delete("1.0", tk.END)
        log_box.insert(tk.END, f"Starting export for: {sel}...\n\n")
        root.update()

        try:
            res = export_all_final_subjects(target_subject=target, verbose=False)
            for r in res:
                log_box.insert(tk.END, f"[OK] {r['subject']}: {r['total_questions']} questions, {r['topic_files_count']} topic files\n")
            log_box.insert(tk.END, "\nSuccessfully finished!\n")
            messagebox.showinfo("Export Successful", "All explained topics Markdown files have been exported successfully!")
        except Exception as err:
            log_box.insert(tk.END, f"\n[ERROR] {err}\n")
            messagebox.showerror("Error", str(err))

    btn_frame = tk.Frame(content, bg="#F8FAFC")
    btn_frame.pack(fill="x")

    run_btn = tk.Button(
        btn_frame,
        text="Start Export",
        font=("Segoe UI", 10, "bold"),
        bg="#2563EB",
        fg="#FFFFFF",
        activebackground="#1D4ED8",
        activeforeground="#FFFFFF",
        relief="flat",
        padx=18,
        pady=8,
        cursor="hand2",
        command=run_process
    )
    run_btn.pack(side="left")

    close_btn = tk.Button(
        btn_frame,
        text="Close",
        font=("Segoe UI", 10),
        bg="#E2E8F0",
        fg="#334155",
        relief="flat",
        padx=14,
        pady=8,
        cursor="hand2",
        command=root.destroy
    )
    close_btn.pack(side="right")

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="TealMED Explained Topics Markdown Exporter")
    parser.add_argument("--subject", type=str, default=None, help="Specific subject folder (e.g. cardio). If omitted, processes all.")
    parser.add_argument("--subfolder", type=str, default="topics_md", help="Subfolder name inside each subject (default: topics_md)")
    parser.add_argument("--gui", action="store_true", help="Launch interactive graphical window")

    args = parser.parse_args()

    if args.gui:
        launch_gui()
    else:
        export_all_final_subjects(subfolder_name=args.subfolder, target_subject=args.subject)


if __name__ == "__main__":
    main()
