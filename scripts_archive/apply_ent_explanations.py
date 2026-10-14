"""
Master script to apply explanations.txt to all_ent/ent_all.json,
normalize punctuation, re-sort by user's topic order, re-index 1..194,
and export all formats to all_ent, final/ent, classified, and output/sorted_chunks.
"""

import os
import sys
import re
import json
import shutil
from pathlib import Path
import pandas as pd

# Topics in exact user specified order:
TARGET_TOPICS_ORDER = [
    "أمراض الأذن والسمعيات",
    "أمراض الأذن العصبية والدوار والعصب الوجهي",
    "أمراض الأنف والجيوب الأنفية",
    "أورام الأنف والبلعوم الأنفي والرعاف",
    "أمراض الفم والبلعوم واللوزتين",
    "أمراض وأورام الغدد اللعابية",
    "أمراض الحنجرة واضطرابات الصوت والأورام",
    "إسعافات مجرى الهواء وكتل العنق"
]

def normalize_stem_punct(stem):
    if not stem or not isinstance(stem, str):
        return ""
    s = stem.strip()
    if not s:
        return ""
    # Strip any trailing colons, arabic colons, question marks, dots, or whitespace
    s = re.sub(r'[\s:：؟?.]+$', '', s)
    return s + ':'

def normalize_option_punct(text):
    if not text or not isinstance(text, str):
        return ""
    s = text.strip()
    if not s:
        return ""
    # Strip trailing dots, colons, arabic colons, or whitespace
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
    if len(splits) != 194:
        raise ValueError(f"Expected 194 explanation headers, found {len(splits)}")

    parsed = {}
    for i in range(len(splits)):
        m = splits[i]
        q_num = int(m.group(1))
        start_pos = m.end()
        end_pos = splits[i+1].start() if i + 1 < len(splits) else len(text)
        block = text[start_pos:end_pos].strip()
        
        if block.endswith('---'):
            block = block[:-3].strip()
            
        obj_m = re.search(r'EDUCATIONAL OBJECTIVE:\s*(.*?)(?=(?:HIGH YIELD NOTE:|EXPLANATION:|$))', block, re.DOTALL)
        note_m = re.search(r'HIGH YIELD NOTE:\s*(.*?)(?=(?:EXPLANATION:|$))', block, re.DOTALL)
        exp_m = re.search(r'EXPLANATION:\s*(.*?)$', block, re.DOTALL)
        
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
            "Medical_Subject": q.get("subject_name", "") or "الأذنية",
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

def generate_markdown_prompt(questions):
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
        
        # Include explanation if available
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
    json_path = base_dir / "all_ent" / "ent_all.json"
    exp_path = base_dir / "explanations.txt"

    print("1. Loading base questions from all_ent/ent_all.json...")
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    print(f"   Loaded {len(questions)} questions.")

    print("2. Parsing explanations from explanations.txt...")
    exp_map = parse_explanations_file(exp_path)
    print(f"   Successfully parsed {len(exp_map)} explanations.")

    print("3. Applying explanations & punctuation normalization to each question...")
    for idx, q in enumerate(questions, start=1):
        exp_data = exp_map[idx]
        q['educational_objective'] = exp_data['educational_objective']
        q['high_yield_note'] = exp_data['high_yield_note']
        q['explanation'] = exp_data['explanation']

        # Punctuation normalization
        q['title'] = normalize_stem_punct(q['title'])
        for opt in q.get('options', []):
            opt['text'] = normalize_option_punct(opt.get('text', ''))

    print("   Explanations and punctuation applied.")

    # Double-check q_ent_012
    q12 = next(q for q in questions if q.get('original_id') == 'q_ent_047' or q['id'] == 'q_ent_012')
    print(f"   Check q_ent_012: Title={q12['title']}")
    print(f"   Check q_ent_012 options: {[opt['text'] for opt in q12['options']]}")
    print(f"   Check q_ent_012 objective: {q12['educational_objective'][:60]}...")

    print("\n4. Grouping by topic and re-ordering topics by user specification...")
    topics_dict = {t: [] for t in TARGET_TOPICS_ORDER}
    for q in questions:
        t = q.get('topic_name')
        if t not in topics_dict:
            raise ValueError(f"Unknown topic: '{t}' not in target topics order!")
        topics_dict[t].append(q)

    for t in TARGET_TOPICS_ORDER:
        print(f"   • {t}: {len(topics_dict[t])} questions")

    # Combine in exact requested topic order
    # Notice: questions inside each topic are ALREADY sorted chronologically
    sorted_questions = []
    for t in TARGET_TOPICS_ORDER:
        sorted_questions.extend(topics_dict[t])

    print(f"\n5. Re-indexing questions from 1 to {len(sorted_questions)}...")
    for new_idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{new_idx:03d}"
        q['id'] = f"q_ent_{num_str}"
        # Ensure subject_name is الأذنية
        q['subject_name'] = "الأذنية"

    print("   Re-indexing complete. First Q:", sorted_questions[0]['id'], sorted_questions[0]['topic_name'])
    print("   Last Q:", sorted_questions[-1]['id'], sorted_questions[-1]['topic_name'])

    # 6. Save all_ent files
    print("\n6. Saving master package in all_ent/...")
    all_ent_dir = base_dir / "all_ent"
    all_ent_dir.mkdir(parents=True, exist_ok=True)
    with open(all_ent_dir / "ent_all.json", "w", encoding="utf-8") as f:
        json.dump(sorted_questions, f, ensure_ascii=False, indent=2)

    df_all = questions_to_dataframe(sorted_questions)
    df_all.to_csv(all_ent_dir / "ent_all.csv", index=False, encoding="utf-8-sig")

    md_all = generate_markdown_prompt(sorted_questions)
    with open(all_ent_dir / "ent_all_ai.md", "w", encoding="utf-8") as f:
        f.write(md_all)

    # 7. Save per-topic files in all_ent/topics/
    all_ent_topics_dir = all_ent_dir / "topics"
    if all_ent_topics_dir.exists():
        for old_f in all_ent_topics_dir.glob("ent_*"):
            old_f.unlink()
    all_ent_topics_dir.mkdir(parents=True, exist_ok=True)

    for t_idx, t in enumerate(TARGET_TOPICS_ORDER, start=1):
        t_qs = [q for q in sorted_questions if q['topic_name'] == t]
        slug = sanitize_filename(t)
        t_base = f"ent_{t_idx:02d}_{slug}"
        with open(all_ent_topics_dir / f"{t_base}.json", "w", encoding="utf-8") as f:
            json.dump(t_qs, f, ensure_ascii=False, indent=2)
        df_t = questions_to_dataframe(t_qs)
        df_t.to_csv(all_ent_topics_dir / f"{t_base}.csv", index=False, encoding="utf-8-sig")

    # 8. Save final/ent/ files
    print("\n7. Saving final/ent/ master package...")
    final_ent_dir = base_dir / "final" / "ent"
    final_ent_dir.mkdir(parents=True, exist_ok=True)
    with open(final_ent_dir / "ent_all.json", "w", encoding="utf-8") as f:
        json.dump(sorted_questions, f, ensure_ascii=False, indent=2)
    df_all.to_csv(final_ent_dir / "ent_all.csv", index=False, encoding="utf-8-sig")
    with open(final_ent_dir / "ent_all_ai.md", "w", encoding="utf-8") as f:
        f.write(md_all)

    # 9. Update classified/ folder (clean old ent files first)
    print("\n8. Updating classified/ folder...")
    classified_dir = base_dir / "classified"
    for sub in ["json", "csv", "md"]:
        s_dir = classified_dir / sub
        s_dir.mkdir(parents=True, exist_ok=True)
        for old_f in s_dir.glob("ent_*"):
            old_f.unlink()

    for t_idx, t in enumerate(TARGET_TOPICS_ORDER, start=1):
        t_qs = [q for q in sorted_questions if q['topic_name'] == t]
        slug = sanitize_filename(t)
        base_name = f"ent_{t_idx:02d}_{slug}"
        
        with open(classified_dir / "json" / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(t_qs, f, ensure_ascii=False, indent=2)
        df_t = questions_to_dataframe(t_qs)
        df_t.to_csv(classified_dir / "csv" / f"{base_name}.csv", index=False, encoding="utf-8-sig")
        with open(classified_dir / "md" / f"{base_name}_ai.md", "w", encoding="utf-8") as f:
            f.write(generate_markdown_prompt(t_qs))

    # 10. Update output/sorted_chunks/ (17 chunks of 12 questions)
    print("\n9. Slicing into output/sorted_chunks/ (12 questions per chunk)...")
    chunks_dir = base_dir / "output" / "sorted_chunks"
    for sub in ["json", "csv", "md"]:
        s_dir = chunks_dir / sub
        s_dir.mkdir(parents=True, exist_ok=True)
        for old_f in s_dir.glob("ent_*"):
            old_f.unlink()

    chunk_size = 12
    for c_idx in range(0, len(sorted_questions), chunk_size):
        chunk_qs = sorted_questions[c_idx:c_idx + chunk_size]
        chunk_num = (c_idx // chunk_size) + 1
        base_name = f"ent_{chunk_num:02d}"

        with open(chunks_dir / "json" / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(chunk_qs, f, ensure_ascii=False, indent=2)
        df_chunk = questions_to_dataframe(chunk_qs)
        df_chunk.to_csv(chunks_dir / "csv" / f"{base_name}.csv", index=False, encoding="utf-8-sig")
        with open(chunks_dir / "md" / f"{base_name}_ai.md", "w", encoding="utf-8") as f:
            f.write(generate_markdown_prompt(chunk_qs))

    # Also update output/ENT.csv
    df_all.to_csv(base_dir / "output" / "ENT.csv", index=False, encoding="utf-8-sig")

    # 11. Update final/manifest.json
    print("\n10. Updating final/manifest.json...")
    manifest_path = base_dir / "final" / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    manifest["subjects"]["ent"] = {
        "subject_name": "الأذنية",
        "folder": "final/ent",
        "questions_count": len(sorted_questions),
        "files": {
            "csv": "ent_all.csv",
            "json": "ent_all.json",
            "ai_prompt": "ent_all_ai.md"
        },
        "topics": TARGET_TOPICS_ORDER
    }
    manifest["subjects_count"] = len(manifest["subjects"])
    manifest["total_questions"] = sum(s["questions_count"] for s in manifest["subjects"].values())

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"    Manifest updated: {manifest['subjects_count']} subjects, {manifest['total_questions']} total questions.")
    print("\nAll ENT files generated successfully!")

if __name__ == "__main__":
    main()
