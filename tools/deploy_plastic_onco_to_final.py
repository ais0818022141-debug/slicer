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
TARGET_DIR = FINAL_DIR / "plastic_onco"
MANIFEST_PATH = FINAL_DIR / "manifest.json"

def main():
    print("=== Deploying Plastic Surgery & Oncology to final/plastic_onco/ ===")

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Master files to deploy
    files_to_copy = [
        "plastic_onco_all.csv",
        "plastic_onco_all.json",
        "plastic_onco_all_ai.md",
        "plastic_onco_all_ai_temp.md",
        "plastic_onco_all.html",
        "plastic_onco_all_topics.html",
        "plastic_onco_all_sessions.html",
        "explanations.txt"
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

    # Copy generated folders: sessions, topics, years
    for folder in ["sessions", "topics", "years"]:
        src_folder = WORKING_DIR / folder
        dst_folder = TARGET_DIR / folder
        if src_folder.exists():
            if dst_folder.exists():
                shutil.rmtree(dst_folder)
            shutil.copytree(src_folder, dst_folder)
            item_count = len(list(dst_folder.glob("*.html")))
            print(f"[✓] Copied folder: {folder}/ ({item_count} HTML files)")

    # Update manifest.json
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        with open(TARGET_DIR / "plastic_onco_all.json", 'r', encoding='utf-8') as f:
            q_data = json.load(f)

        ordered_topics = []
        for q in q_data:
            t = q.get("topic_name")
            if t and t not in ordered_topics:
                ordered_topics.append(t)

        manifest.setdefault("subjects", {})
        manifest["subjects"]["plastic_onco"] = {
            "subject_name": "الجراحة التجميلية والأورام",
            "folder": "final/plastic_onco",
            "questions_count": len(q_data),
            "files": {
                "csv": "plastic_onco_all.csv",
                "json": "plastic_onco_all.json",
                "ai_prompt": "plastic_onco_all_ai.md"
            },
            "topics": ordered_topics
        }

        manifest["subjects_count"] = len(manifest["subjects"])
        manifest["total_questions"] = sum(s.get("questions_count", 0) for s in manifest["subjects"].values())

        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] Updated manifest.json: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")

    print("\n=== Final Deployment of Plastic Surgery & Oncology Completed Successfully ===")

if __name__ == "__main__":
    main()
