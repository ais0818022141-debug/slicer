import os
import sys
import json
import shutil
import pandas as pd
from pathlib import Path

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
WORKING_DIR = BASE_DIR / "working_on"
FINAL_DIR = BASE_DIR / "final"
TARGET_DIR = FINAL_DIR / "general_surgery"
MANIFEST_PATH = FINAL_DIR / "manifest.json"

def main():
    print("=== Deploying Consolidated General Surgery to final/general_surgery/ ===")

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Master files to deploy (strictly consolidated files only, no chunks)
    files_to_copy = [
        "general_surgery_all.csv",
        "general_surgery_all.json",
        "general_surgery_all_ai.md",
        "general_surgery_all_ai_temp.md",
        "general_surgery_all.html",
        "general_surgery_all_topics.html",
        "general_surgery_all_sessions.html",
    ]

    for fname in files_to_copy:
        src = WORKING_DIR / fname
        dst = TARGET_DIR / fname
        if src.exists():
            shutil.copyfile(src, dst)
            size_kb = dst.stat().st_size / 1024
            print(f"[✓] Copied: {fname} ({size_kb:.1f} KB)")
        else:
            print(f"[!] Warning: Missing source file: {fname}")

    # Update manifest.json
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Load topics from the deployed json
        with open(TARGET_DIR / "general_surgery_all.json", 'r', encoding='utf-8') as f:
            q_data = json.load(f)

        distinct_topics = sorted(list(set(q.get("topic_name", "") for q in q_data if q.get("topic_name"))))

        manifest.setdefault("subjects", {})
        manifest["subjects"]["general_surgery"] = {
            "subject_name": "الجراحة العامة",
            "folder": "final/general_surgery",
            "questions_count": len(q_data),
            "files": {
                "csv": "general_surgery_all.csv",
                "json": "general_surgery_all.json",
                "ai_prompt": "general_surgery_all_ai.md"
            },
            "topics": distinct_topics
        }

        manifest["subjects_count"] = len(manifest["subjects"])
        manifest["total_questions"] = sum(s.get("questions_count", 0) for s in manifest["subjects"].values())

        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] Updated manifest.json: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")

    print("\n=== Final Deployment Completed Successfully ===")

if __name__ == "__main__":
    main()
