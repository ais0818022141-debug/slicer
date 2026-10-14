import os
import sys
import json
import shutil
from pathlib import Path

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
WORKING_DIR = BASE_DIR / "working_on"
FINAL_DIR = BASE_DIR / "final"
TARGET_DIR = FINAL_DIR / "optho"
MANIFEST_PATH = FINAL_DIR / "manifest.json"

def main():
    print("=== Deploying Consolidated Ophthalmology to final/optho/ ===")

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Master files to deploy (strictly consolidated files only, no chunks)
    files_to_copy = [
        "optho_all.csv",
        "optho_all.json",
        "optho_all_ai.md",
        "optho_all_ai_temp.md",
        "optho_all.html",
        "optho_all_topics.html",
        "optho_all_sessions.html",
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

        # Load topics in order of appearance from the deployed json
        with open(TARGET_DIR / "optho_all.json", 'r', encoding='utf-8') as f:
            q_data = json.load(f)

        ordered_topics = []
        for q in q_data:
            t = q.get("topic_name")
            if t and t not in ordered_topics:
                ordered_topics.append(t)

        manifest.setdefault("subjects", {})
        manifest["subjects"]["optho"] = {
            "subject_name": "العينية",
            "folder": "final/optho",
            "questions_count": len(q_data),
            "files": {
                "csv": "optho_all.csv",
                "json": "optho_all.json",
                "ai_prompt": "optho_all_ai.md"
            },
            "topics": ordered_topics
        }

        manifest["subjects_count"] = len(manifest["subjects"])
        manifest["total_questions"] = sum(s.get("questions_count", 0) for s in manifest["subjects"].values())

        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] Updated manifest.json: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")

    print("\n=== Final Deployment of Ophthalmology Completed Successfully ===")

if __name__ == "__main__":
    main()
