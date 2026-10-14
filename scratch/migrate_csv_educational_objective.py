#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import csv
import json
import shutil
import datetime
from pathlib import Path

def create_backup(p: Path):
    backup_dir = p.parent / ".backup"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{p.stem}_{ts}{p.suffix}"
    shutil.copyfile(p, backup_path)
    return backup_path

def norm_stem(s):
    if not s:
        return ""
    return "".join(str(s).split()).strip()

def run_migration():
    base_dir = Path(".")
    final_dir = base_dir / "final"
    
    report = []
    total_migrated_files = 0
    total_populated_objectives = 0
    total_empty_objectives = 0
    
    for subject_dir in sorted(final_dir.iterdir()):
        if not subject_dir.is_dir() or subject_dir.name.startswith("."):
            continue
            
        json_path = subject_dir / f"{subject_dir.name}_all.json"
        if not json_path.exists():
            print(f"[!] No JSON file found for subject: {subject_dir.name}")
            continue
            
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            
        by_id = {}
        by_stem = {}
        for q in json_data:
            qid = q.get("id")
            if qid:
                by_id[qid] = q
            st = norm_stem(q.get("title") or q.get("vignette") or "")
            if st:
                by_stem[st] = q
                
        # Find all CSV files in this subject folder (excluding .backup)
        csv_files = [p for p in subject_dir.glob("*.csv") if not p.name.startswith(".")]
        
        for csv_path in csv_files:
            create_backup(csv_path)
            
            # Read CSV
            rows = None
            fieldnames = None
            for enc in ["utf-8-sig", "utf-8", "cp1256"]:
                try:
                    with open(csv_path, "r", encoding=enc) as f:
                        reader = csv.DictReader(f)
                        fieldnames = list(reader.fieldnames)
                        rows = list(reader)
                        break
                except Exception:
                    continue
                    
            if rows is None or not fieldnames:
                print(f"[!] Failed to read CSV: {csv_path}")
                continue
                
            fieldnames = [c.lstrip("\ufeff") for c in fieldnames]
            cleaned_rows = []
            for r in rows:
                cleaned_rows.append({(k.lstrip("\ufeff") if isinstance(k, str) else k): (v if v is not None else "") for k, v in r.items()})
            rows = cleaned_rows
            
            # Target column name
            col_target = "Educational_Objective"
            
            # Determine column positions
            # Remove any existing educational objective column to ensure placement right after High_Yield_Note
            old_edu_cols = [c for c in fieldnames if c.strip().lower() in ["educational_objective", "educational", "الهدف_من_السؤال", "الهدف من السؤال", "الهدف_التعليمي", "الهدف التعليمي"]]
            for old_col in old_edu_cols:
                fieldnames.remove(old_col)
                
            # Find High_Yield_Note
            hy_idx = next((i for i, c in enumerate(fieldnames) if c.strip().lower() in ["high_yield_note", "الفكرة_من_السؤال", "الفكرة من السؤال", "نقطة_عالية_الأهمية", "نقطة عالية الأهمية"]), -1)
            if hy_idx != -1:
                fieldnames.insert(hy_idx + 1, col_target)
            else:
                exp_idx = next((i for i, c in enumerate(fieldnames) if c.strip().lower() in ["explanation", "التعليل", "الشرح"]), -1)
                if exp_idx != -1:
                    fieldnames.insert(exp_idx + 1, col_target)
                else:
                    cor_idx = next((i for i, c in enumerate(fieldnames) if c.strip().lower() in ["correct_answer", "الجواب_الصحيح", "الإجابة_الصحيحة"]), -1)
                    if cor_idx != -1:
                        fieldnames.insert(cor_idx, col_target)
                    else:
                        fieldnames.append(col_target)
                        
            # Populate Educational_Objective
            file_pop = 0
            file_empty = 0
            
            for r in rows:
                qid = (r.get("Question_ID") or r.get("id") or "").strip()
                stem = norm_stem(r.get("Question_Text") or r.get("title") or "")
                
                matched_q = by_id.get(qid)
                if not matched_q and stem:
                    matched_q = by_stem.get(stem)
                    
                edu_val = ""
                if matched_q:
                    raw_edu = matched_q.get("educational_objective")
                    if raw_edu and str(raw_edu).strip():
                        edu_val = str(raw_edu).strip()
                        
                r[col_target] = edu_val
                if edu_val:
                    file_pop += 1
                else:
                    file_empty += 1
                    
            # Write updated CSV
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
                
            total_migrated_files += 1
            total_populated_objectives += file_pop
            total_empty_objectives += file_empty
            
            report.append({
                "subject": subject_dir.name,
                "file": csv_path.name,
                "rows": len(rows),
                "populated": file_pop,
                "empty": file_empty,
                "position": fieldnames.index(col_target)
            })
            
    print(f"\n==================================================================")
    print(f" MIGRATION SUMMARY")
    print(f"==================================================================")
    print(f"{'Subject':<18} | {'File':<25} | {'Rows':<6} | {'With Edu':<10} | {'Empty':<6} | {'Col Pos'}")
    print("-" * 75)
    for rep in report:
        print(f"{rep['subject']:<18} | {rep['file']:<25} | {rep['rows']:<6} | {rep['populated']:<10} | {rep['empty']:<6} | Index {rep['position']}")
    print("-" * 75)
    print(f"Total CSV Files Migrated: {total_migrated_files}")
    print(f"Total Populated Educational Objectives: {total_populated_objectives}")
    print(f"Total Empty Educational Objectives: {total_empty_objectives}")

if __name__ == "__main__":
    run_migration()
