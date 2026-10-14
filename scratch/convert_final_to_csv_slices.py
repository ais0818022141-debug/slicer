#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Converts final/ topics and sessions folders to CSV files instead of HTML.
Removes years/ folders completely.
Deletes all .html files in final/ folders.
Keeps topics_md/ intact.
"""

import os
import sys
import re
import csv
import shutil
from pathlib import Path

def sanitize_filename(name: str) -> str:
    if not name:
        return "غير_محدد"
    clean = re.sub(r'[^\w\u0600-\u06FF]+', '_', str(name).strip())
    clean = clean.strip('._')
    return clean or "عام"

def process_subject(subject_dir: Path):
    stem = f"{subject_dir.name}_all"
    main_csv = subject_dir / f"{stem}.csv"
    if not main_csv.exists():
        print(f"[!] Main CSV not found: {main_csv}")
        return None

    # Load main CSV rows
    rows = []
    fieldnames = []
    for enc in ["utf-8-sig", "utf-8", "cp1256"]:
        try:
            with open(main_csv, "r", encoding=enc) as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames)
                rows = list(reader)
                break
        except Exception:
            continue

    if not rows or not fieldnames:
        print(f"[!] Failed to read {main_csv}")
        return None

    fieldnames = [c.lstrip("\ufeff") for c in fieldnames]
    cleaned_rows = []
    for r in rows:
        cleaned_rows.append({(k.lstrip("\ufeff") if isinstance(k, str) else k): (v if v is not None else "") for k, v in r.items()})
    rows = cleaned_rows

    # 1. Remove years/ folder
    years_dir = subject_dir / "years"
    if years_dir.exists():
        shutil.rmtree(years_dir)

    # 2. Remove all .html files in root of subject folder
    root_htmls = list(subject_dir.glob("*.html"))
    for h in root_htmls:
        try:
            h.unlink()
        except Exception:
            pass

    # 3. Process topics/ folder
    topics_dir = subject_dir / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)
    # Remove all .html files in topics/
    for h in topics_dir.glob("*.html"):
        try:
            h.unlink()
        except Exception:
            pass

    # Group rows by Chapter_or_Section
    topics_dict = {}
    for r in rows:
        top = (r.get("Chapter_or_Section") or "عام").strip() or "عام"
        topics_dict.setdefault(top, []).append(r)

    created_topics = []
    for top_name, top_rows in topics_dict.items():
        clean_top = sanitize_filename(top_name)
        out_csv = topics_dir / f"{stem}_{clean_top}.csv"
        with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(top_rows)
        created_topics.append(out_csv.name)

    # 4. Process sessions/ folder
    sessions_dir = subject_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    # Remove all .html files in sessions/
    for h in sessions_dir.glob("*.html"):
        try:
            h.unlink()
        except Exception:
            pass

    # Group rows by Exam_Date
    sessions_dict = {}
    for r in rows:
        sess = (r.get("Exam_Date") or "غير_محدد").strip() or "غير_محدد"
        sessions_dict.setdefault(sess, []).append(r)

    created_sessions = []
    for sess_name, sess_rows in sessions_dict.items():
        clean_sess = sanitize_filename(sess_name)
        out_csv = sessions_dir / f"{stem}_{clean_sess}.csv"
        with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sess_rows)
        created_sessions.append(out_csv.name)

    return {
        "subject": subject_dir.name,
        "total_qs": len(rows),
        "topics_count": len(created_topics),
        "sessions_count": len(created_sessions),
        "deleted_years": not years_dir.exists(),
        "root_htmls_deleted": len(root_htmls)
    }

def main():
    final_dir = Path("final")
    results = []
    for p in sorted(final_dir.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        res = process_subject(p)
        if res:
            results.append(res)

    print(f"\n{'Subject':<20} | {'Total Qs':<8} | {'Topics CSVs':<12} | {'Sessions CSVs':<14} | {'Years Removed'}")
    print("-" * 75)
    for r in results:
        print(f"{r['subject']:<20} | {r['total_qs']:<8} | {r['topics_count']:<12} | {r['sessions_count']:<14} | {'Yes' if r['deleted_years'] else 'No'}")
    print("-" * 75)
    total_t = sum(r['topics_count'] for r in results)
    total_s = sum(r['sessions_count'] for r in results)
    print(f"Total Subjects: {len(results)}")
    print(f"Total Topics CSVs Created: {total_t}")
    print(f"Total Sessions CSVs Created: {total_s}")

if __name__ == "__main__":
    main()
