"""
Master Script: Apply Pulmonology Explanations and Build Master Packages
======================================================================
1. Loads all_pulmo/pulmo_all.json (172 questions, sorted by 7 topics).
2. Parses explanations.txt (172 explanation blocks).
3. Injects educational_objective, high_yield_note, and explanation into questions.
4. Normalizes punctuation (: for question stem, . for options).
5. Exports:
   - all_pulmo/ (pulmo_all.json, pulmo_all.csv, pulmo_all_ai.md, and all_pulmo/topics/)
   - final/pulmo/ (pulmo_all.json, pulmo_all.csv, pulmo_all_ai.md)
   - classified/ (json/, csv/, md/ for each of the 7 topics)
   - output/sorted_chunks/ (15 chunks of 12 questions in json/, csv/, md/)
   - output/أسئلة دورات الصدرية.csv
6. Updates final/manifest.json to add 'pulmo'.
"""

import os
import sys
import re
import json
import shutil
from pathlib import Path
import pandas as pd

TARGET_TOPICS_ORDER = [
    "أعراض الأمراض التنفسية",
    "أخماج الجهاز التنفسي",
    "الأمراض الرئوية الانسدادية",
    "الأمراض الرئوية الخلالية",
    "أمراض الأوعية الرئوية",
    "أمراض الجنب",
    "أورام الرئة والقصبات"
]

def normalize_stem_punct(stem):
    if not stem or not isinstance(stem, str):
        return ""
    s = stem.strip()
    if not s:
        return ""
    s = re.sub(r'[\s:：؟?.]+$', '', s)
    return s + ':'

def normalize_option_punct(text):
    if not text or not isinstance(text, str):
        return ""
    s = text.strip()
    if not s:
        return ""
    s = re.sub(r'[\s.:：]+$', '', s)
    return s + '.'

def sanitize_filename(name):
    if not name:
        return "بدون_موضوع"
    clean = re.sub(r'[ \t]+', '_', str(name).strip())
    clean = re.sub(r'[\\/:*?"<>|]', '', clean)
    clean = clean.strip('._')
    return clean or "موضوع"

def parse_explanations_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    pattern = r'(?m)^#(\d+)\s*$'
    splits = list(re.finditer(pattern, text))
    if len(splits) != 172:
        raise ValueError(f"Expected 172 explanation headers, found {len(splits)}")

    parsed = {}
    for i in range(len(splits)):
        m = splits[i]
        q_num = int(m.group(1))
        start_pos = m.end()
        end_pos = splits[i+1].start() if i + 1 < len(splits) else len(text)
        block = text[start_pos:end_pos].strip()
        
        if block.endswith('---'):
            block = block[:-3].strip()
            
        obj_m = re.search(r'EDUCATIONAL\s*[\u064b-\u065f\u0670\u0640]*\s*OBJECTIVE:\s*(.*?)(?=(?:HIGH\s*[\u064b-\u065f\u0670\u0640]*\s*YIELD\s*[\u064b-\u065f\u0670\u0640]*\s*NOTE:|EXPLANATION:|$))', block, re.DOTALL | re.IGNORECASE)
        note_m = re.search(r'HIGH\s*[\u064b-\u065f\u0670\u0640]*\s*YIELD\s*[\u064b-\u065f\u0670\u0640]*\s*NOTE:\s*(.*?)(?=(?:EXPLANATION:|$))', block, re.DOTALL | re.IGNORECASE)
        exp_m = re.search(r'EXPLANATION:\s*(.*?)$', block, re.DOTALL | re.IGNORECASE)
        
        obj = obj_m.group(1).strip() if obj_m else ""
        note = note_m.group(1).strip() if note_m else ""
        exp = exp_m.group(1).strip() if exp_m else ""
        
        if not obj or not note or not exp:
            raise ValueError(f"Block #{q_num} missing fields: obj={bool(obj)}, note={bool(note)}, exp={bool(exp)}")

        parsed[q_num] = {
            'educational_objective': obj,
            'high_yield_note': note,
            'explanation': exp
        }
    return parsed

def questions_to_dataframe(questions):
    rows = []
    for q in questions:
        options = q.get("options", [])
        corr_letter = q.get("correct_option", "")

        correct_text = ""
        wrong_texts = []
        for opt in options:
            if opt.get("is_correct") or (corr_letter and opt.get("letter") == corr_letter):
                correct_text = opt.get("text", "")
            else:
                wrong_texts.append(opt.get("text", ""))

        row = {
            "Question_ID": q.get("id", ""),
            "Medical_Subject": q.get("subject_name", "") or "الصدرية",
            "Exam_Date": q.get("exam_period", ""),
            "Chapter_or_Section": q.get("topic_name", ""),
            "Question_Text": q.get("title", ""),
            "Explanation": q.get("explanation", ""),
            "High_Yield_Note": q.get("high_yield_note", "") or "",
            "Correct_Answer": correct_text
        }
        for i in range(1, 6):
            row[f"Wrong_Answer_{i}"] = wrong_texts[i - 1] if i - 1 < len(wrong_texts) else ""

        rows.append(row)

    return pd.DataFrame(rows)

def generate_markdown_prompt(questions, include_explanation=True):
    lines = []
    for q in questions:
        q_id = q.get("id") or ""
        topic = q.get("topic_name") or "الموضوع"
        title = q.get("title") or ""
        correct_opt = q.get("correct_option", "")
        options = q.get("options", [])

        num_m = re.search(r'_(\d+)$', str(q_id))
        num_str = f"#{num_m.group(1)}" if num_m else f"#{q_id}"

        lines.append(f"{num_str} [{q_id}] ({topic})")
        lines.append(f"السؤال: {title}")
        lines.append(f"الجواب: {correct_opt}")
        for opt in options:
            let = opt.get("letter", "")
            txt = opt.get("text", "")
            is_corr = (let == correct_opt) or opt.get("is_correct", False)
            mark = " (الصحيح)" if is_corr else ""
            lines.append(f"{let}) {txt}{mark}")
        
        if include_explanation:
            exp = q.get("explanation", "")
            hy = q.get("high_yield_note", "")
            obj = q.get("educational_objective", "")
            if obj or hy or exp:
                lines.append(f"\nالشرح السريري:")
                if obj:
                    lines.append(f"الهدف التعليمي: {obj}")
                if hy:
                    lines.append(f"ملاحظة عالية الأهمية: {hy}")
                if exp:
                    lines.append(f"التوضيح: {exp}")
        lines.append("---\n")

    return "\n".join(lines).strip()

def main():
    base_dir = Path(r"c:\Users\Toshiba\Desktop\slicer")
    json_path = base_dir / "all_pulmo" / "pulmo_all.json"
    exp_path = base_dir / "explanations.txt"

    print("1. Loading questions from all_pulmo/pulmo_all.json...")
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    print(f"   Loaded {len(questions)} questions.")

    print("\n2. Parsing explanations from explanations.txt...")
    exp_map = parse_explanations_file(exp_path)
    print(f"   Parsed {len(exp_map)} explanation blocks successfully.")

    print("\n3. Attaching explanations and normalizing punctuation...")
    for idx, q in enumerate(questions, start=1):
        exp = exp_map[idx]
        q['educational_objective'] = exp['educational_objective']
        q['high_yield_note'] = exp['high_yield_note']
        q['explanation'] = exp['explanation']
        q['subject_name'] = "الصدرية"

        q['title'] = normalize_stem_punct(q['title'])
        for opt in q.get('options', []):
            opt['text'] = normalize_option_punct(opt.get('text', ''))

    print("   All explanations attached and punctuation normalized.")

    # 4. Save to all_pulmo/
    print("\n4. Saving master package in all_pulmo/...")
    all_pulmo_dir = base_dir / "all_pulmo"
    all_pulmo_dir.mkdir(parents=True, exist_ok=True)
    with open(all_pulmo_dir / "pulmo_all.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    df_all = questions_to_dataframe(questions)
    df_all.to_csv(all_pulmo_dir / "pulmo_all.csv", index=False, encoding="utf-8-sig")

    md_all = generate_markdown_prompt(questions, include_explanation=True)
    with open(all_pulmo_dir / "pulmo_all_ai.md", "w", encoding="utf-8") as f:
        f.write(md_all)

    # Save per-topic in all_pulmo/topics/
    all_pulmo_topics = all_pulmo_dir / "topics"
    if all_pulmo_topics.exists():
        for f_old in all_pulmo_topics.glob("pulmo_*"):
            f_old.unlink()
    all_pulmo_topics.mkdir(parents=True, exist_ok=True)

    for t_idx, t in enumerate(TARGET_TOPICS_ORDER, start=1):
        t_qs = [q for q in questions if q['topic_name'] == t]
        slug = sanitize_filename(t)
        base_name = f"pulmo_{t_idx:02d}_{slug}"
        with open(all_pulmo_topics / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(t_qs, f, ensure_ascii=False, indent=2)
        df_t = questions_to_dataframe(t_qs)
        df_t.to_csv(all_pulmo_topics / f"{base_name}.csv", index=False, encoding="utf-8-sig")

    # 5. Save to final/pulmo/
    print("\n5. Saving master package in final/pulmo/...")
    final_pulmo_dir = base_dir / "final" / "pulmo"
    final_pulmo_dir.mkdir(parents=True, exist_ok=True)
    with open(final_pulmo_dir / "pulmo_all.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    df_all.to_csv(final_pulmo_dir / "pulmo_all.csv", index=False, encoding="utf-8-sig")
    with open(final_pulmo_dir / "pulmo_all_ai.md", "w", encoding="utf-8") as f:
        f.write(md_all)

    # 6. Save to classified/ (json/, csv/, md/)
    print("\n6. Updating classified/ folder...")
    classified_dir = base_dir / "classified"
    for sub in ["json", "csv", "md"]:
        s_dir = classified_dir / sub
        s_dir.mkdir(parents=True, exist_ok=True)
        for f_old in s_dir.glob("pulmo_*"):
            f_old.unlink()

    for t_idx, t in enumerate(TARGET_TOPICS_ORDER, start=1):
        t_qs = [q for q in questions if q['topic_name'] == t]
        slug = sanitize_filename(t)
        base_name = f"pulmo_{t_idx:02d}_{slug}"
        with open(classified_dir / "json" / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(t_qs, f, ensure_ascii=False, indent=2)
        df_t = questions_to_dataframe(t_qs)
        df_t.to_csv(classified_dir / "csv" / f"{base_name}.csv", index=False, encoding="utf-8-sig")
        with open(classified_dir / "md" / f"{base_name}_ai.md", "w", encoding="utf-8") as f:
            f.write(generate_markdown_prompt(t_qs, include_explanation=True))

    # 7. Slicing into output/sorted_chunks/ (12 questions per chunk)
    print("\n7. Slicing into output/sorted_chunks/ (12 questions per chunk)...")
    chunks_dir = base_dir / "output" / "sorted_chunks"
    for sub in ["json", "csv", "md"]:
        s_dir = chunks_dir / sub
        s_dir.mkdir(parents=True, exist_ok=True)
        for f_old in s_dir.glob("pulmo_*"):
            f_old.unlink()

    chunk_size = 12
    for c_idx in range(0, len(questions), chunk_size):
        chunk_qs = questions[c_idx:c_idx + chunk_size]
        chunk_num = (c_idx // chunk_size) + 1
        base_name = f"pulmo_{chunk_num:02d}"

        with open(chunks_dir / "json" / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(chunk_qs, f, ensure_ascii=False, indent=2)
        df_chunk = questions_to_dataframe(chunk_qs)
        df_chunk.to_csv(chunks_dir / "csv" / f"{base_name}.csv", index=False, encoding="utf-8-sig")
        # In sorted_chunks/md: keep question prompt clean without explanations as user requested
        with open(chunks_dir / "md" / f"{base_name}_ai.md", "w", encoding="utf-8") as f:
            f.write(generate_markdown_prompt(chunk_qs, include_explanation=False))

    # Also update output/أسئلة دورات الصدرية.csv
    df_all.to_csv(base_dir / "output" / "أسئلة دورات الصدرية.csv", index=False, encoding="utf-8-sig")

    # 8. Update final/manifest.json
    print("\n8. Updating final/manifest.json...")
    manifest_path = base_dir / "final" / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    manifest["subjects"]["pulmo"] = {
        "subject_name": "الصدرية",
        "folder": "final/pulmo",
        "questions_count": len(questions),
        "files": {
            "csv": "pulmo_all.csv",
            "json": "pulmo_all.json",
            "ai_prompt": "pulmo_all_ai.md"
        },
        "topics": TARGET_TOPICS_ORDER
    }
    manifest["subjects_count"] = len(manifest["subjects"])
    manifest["total_questions"] = sum(s["questions_count"] for s in manifest["subjects"].values())

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"   Manifest updated: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")
    print("\nAll Pulmonology packages built successfully!")

if __name__ == "__main__":
    main()
