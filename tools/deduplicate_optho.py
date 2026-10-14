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
FINAL_DIR = BASE_DIR / "final" / "optho"
WORKING_DIR = BASE_DIR / "working_on"
MANIFEST_PATH = BASE_DIR / "final" / "manifest.json"

def main():
    print("=== Deduplicating Optho (Single-Session Duplicates in Oct 19 & June 21) ===")

    # 1. Load current master JSON
    with open(FINAL_DIR / "optho_all.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} questions.")

    # 2. Identify and remove only the duplicate second copies in June 2021 and Oct 2019
    to_remove = set()
    for target in ['حزيران 2021', 'تشرين 2019']:
        seen_titles = {}
        for q in data:
            if q.get('exam_period') == target:
                norm_title = q['title'].strip().rstrip(':').strip()
                if norm_title in seen_titles:
                    to_remove.add(q['id'])
                else:
                    seen_titles[norm_title] = q['id']

    print(f"Identified {len(to_remove)} duplicate questions to remove within June 2021 and Oct 2019.")

    filtered_questions = [q for q in data if q['id'] not in to_remove]
    print(f"Remaining unique questions: {len(filtered_questions)}")
    assert len(filtered_questions) == 190, f"Expected 190, got {len(filtered_questions)}"

    # 3. Renumber sequentially from 001 to 190
    for idx, q in enumerate(filtered_questions, start=1):
        q['id'] = f"q_optho_{idx:03d}"

    # 4. Save updated JSON in working_on and final
    with open(WORKING_DIR / "optho_all.json", 'w', encoding='utf-8') as f:
        json.dump(filtered_questions, f, ensure_ascii=False, indent=2)
    with open(FINAL_DIR / "optho_all.json", 'w', encoding='utf-8') as f:
        json.dump(filtered_questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Saved optho_all.json (190 questions) in working_on and final/optho")

    # 5. Build CSV dataframe for 190 questions
    csv_rows = []
    for q in filtered_questions:
        # Determine correct answer text and wrong answers
        opts = q.get('options', [])
        cor_opt = next((o for o in opts if o.get('is_correct')), None)
        cor_text = cor_opt['text'] if cor_opt else ""
        wrong_texts = [o['text'] for o in opts if not o.get('is_correct')]

        row = {
            'Question_ID': q['id'],
            'Medical_Subject': q.get('subject_name', 'العينية'),
            'Exam_Date': q.get('exam_period', ''),
            'Chapter_or_Section': q.get('topic_name', ''),
            'Question_Text': q.get('title', ''),
            'Explanation': q.get('explanation', ''),
            'High_Yield_Note': q.get('high_yield_note', ''),
            'Correct_Answer': cor_text,
            'Wrong_Answer_1': wrong_texts[0] if len(wrong_texts) > 0 else None,
            'Wrong_Answer_2': wrong_texts[1] if len(wrong_texts) > 1 else None,
            'Wrong_Answer_3': wrong_texts[2] if len(wrong_texts) > 2 else None,
            'Wrong_Answer_4': wrong_texts[3] if len(wrong_texts) > 3 else None,
            'Wrong_Answer_5': wrong_texts[4] if len(wrong_texts) > 4 else None,
        }
        csv_rows.append(row)

    df = pd.DataFrame(csv_rows)
    df.to_csv(FINAL_DIR / "optho_all.csv", index=False, encoding='utf-8-sig')
    df.to_csv(WORKING_DIR / "optho_all.csv", index=False, encoding='utf-8-sig')
    df.to_csv(WORKING_DIR / "optho.csv", index=False, encoding='utf-8-sig')
    print(f"[✓] Saved optho_all.csv (190 rows) in working_on and final/optho")

    # 6. Generate AI Markdown files
    ai_md_lines = []
    temp_md_lines = []

    for idx, q in enumerate(filtered_questions, start=1):
        num_str = f"{idx:03d}"
        qid = q['id']
        topic = q['topic_name']
        title = q['title']
        cor_let = q.get('correct_option', '')

        # AI clean prompt
        ai_md_lines.append(f"#{num_str} [{qid}] ({topic})")
        ai_md_lines.append(f"السؤال: {title}")
        ai_md_lines.append(f"الجواب: {cor_let}")
        for opt in q.get('options', []):
            let = opt.get('letter', '')
            txt = opt.get('text', '')
            if opt.get('is_correct'):
                ai_md_lines.append(f"{let}) {txt} (الصحيح)")
            else:
                ai_md_lines.append(f"{let}) {txt}")
        ai_md_lines.append("---")
        ai_md_lines.append("")

        # AI temp (with explanations)
        temp_md_lines.append(f"#{num_str} [{qid}] ({topic})")
        temp_md_lines.append(f"السؤال: {title}")
        temp_md_lines.append(f"الجواب: {cor_let}")
        for opt in q.get('options', []):
            let = opt.get('letter', '')
            txt = opt.get('text', '')
            if opt.get('is_correct'):
                temp_md_lines.append(f"{let}) {txt} (الصحيح)")
            else:
                temp_md_lines.append(f"{let}) {txt}")
        if q.get('educational_objective'):
            temp_md_lines.append(f"الهدف التعليمي: {q['educational_objective']}")
        if q.get('high_yield_note'):
            temp_md_lines.append(f"ملاحظة عالية الأهمية: {q['high_yield_note']}")
        if q.get('explanation'):
            temp_md_lines.append(f"الشرح:\n{q['explanation']}")
        temp_md_lines.append("---")
        temp_md_lines.append("")

    for folder in [WORKING_DIR, FINAL_DIR]:
        with open(folder / "optho_all_ai.md", 'w', encoding='utf-8') as f:
            f.write("\n".join(ai_md_lines).strip() + "\n")
        with open(folder / "optho_all_ai_temp.md", 'w', encoding='utf-8') as f:
            f.write("\n".join(temp_md_lines).strip() + "\n")
    print("[✓] Regenerated optho_all_ai.md and optho_all_ai_temp.md in both folders")

    # 7. Update Sliced Chunks in working_on/json/ and working_on/csv/
    json_dir = WORKING_DIR / "json"
    csv_dir = WORKING_DIR / "csv"
    chunk_size = 12
    total_chunks = (len(filtered_questions) + chunk_size - 1) // chunk_size

    # Remove any old stale chunk files >= total_chunks + 1 (e.g. 17, 18)
    for stale_idx in range(total_chunks + 1, 30):
        stale_tag = f"{stale_idx:02d}"
        sj = json_dir / f"optho_{stale_tag}.json"
        sc = csv_dir / f"optho_{stale_tag}.csv"
        sm = WORKING_DIR / "md" / f"optho_{stale_tag}_ai.md"
        if sj.exists():
            sj.unlink()
        if sc.exists():
            sc.unlink()
        if sm.exists():
            sm.unlink()

    for c_idx in range(total_chunks):
        c_num = c_idx + 1
        tag = f"{c_num:02d}"
        c_json_path = json_dir / f"optho_{tag}.json"
        c_csv_path = csv_dir / f"optho_{tag}.csv"

        start_i = c_idx * chunk_size
        end_i = min(start_i + chunk_size, len(filtered_questions))

        chunk_q = filtered_questions[start_i:end_i]
        chunk_df = df.iloc[start_i:end_i]

        with open(c_json_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_q, f, ensure_ascii=False, indent=2)
        chunk_df.to_csv(c_csv_path, index=False, encoding='utf-8-sig')

    print(f"[✓] Synced all {total_chunks} chunk files in working_on/json and working_on/csv")

    # 8. Update manifest.json
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        ordered_topics = []
        for q in filtered_questions:
            t = q.get("topic_name")
            if t and t not in ordered_topics:
                ordered_topics.append(t)

        manifest["subjects"]["optho"] = {
            "subject_name": "العينية",
            "folder": "final/optho",
            "questions_count": len(filtered_questions),
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

        print(f"[✓] Updated manifest.json: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")

    print("=== Base Deduplication Completed Successfully ===")

if __name__ == "__main__":
    main()
