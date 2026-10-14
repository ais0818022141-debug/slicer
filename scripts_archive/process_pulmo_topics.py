"""
TealMED Pulmonology Topic Processor & Chronological Sorter
==========================================================
1. Reads questions from output/json/pulmo_01.json .. pulmo_15.json.
2. Applies topics from topics.txt.
3. Enforces punctuation normalization (: for question stem, . for options).
4. Groups questions by the 7 target topics in exact user-specified order:
   - أعراض الأمراض التنفسية
   - أخماج الجهاز التنفسي
   - الأمراض الرئوية الانسدادية
   - الأمراض الرئوية الخلالية
   - أمراض الأوعية الرئوية
   - أمراض الجنب
   - أورام الرئة والقصبات
5. Within each topic, sorts chronologically (newest exam session to oldest).
6. Re-indexes globally 1..172:
   - ID: q_pulmo_001 .. q_pulmo_172
   - Header: #01 .. #172
7. Exports to:
   - all_pulmo/ (pulmo_all.json, pulmo_all.csv, pulmo_all_ai.md, and all_pulmo/topics/)
   - classified/ (7 topic files in json/, csv/, md/)
   - output/sorted_chunks/ (15 chunks of 12 questions in json/, csv/, md/)
   - output/ (updates output/json/, output/csv/, output/md/ with sorted chunks)
   - output/أسئلة دورات الصدرية.csv (with Chapter_or_Section updated)
"""

import os
import sys
import re
import json
import shutil
from pathlib import Path
import pandas as pd
from topic_sorter import parse_exam_date

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
            "Explanation": q.get("explanation", "") or "",
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
        
        lines.append("---\n")

    return "\n".join(lines).strip()

def main():
    base_dir = Path(r"c:\Users\Toshiba\Desktop\slicer")
    topics_file = base_dir / "topics.txt"

    print("1. Parsing topics.txt...")
    with open(topics_file, 'r', encoding='utf-8') as f:
        topic_lines = [l.strip() for l in f.read().splitlines() if l.strip()]

    topic_map = {}
    for l in topic_lines:
        m = re.match(r'^#(\d+)\s+\[(q_pulmo_\d+)\]\s+(.+)$', l)
        if not m:
            raise ValueError(f"Unmatched line in topics.txt: {l}")
        num = int(m.group(1))
        qid = m.group(2)
        top = m.group(3).strip()
        topic_map[qid] = top

    print(f"   Parsed {len(topic_map)} topic mappings.")

    print("\n2. Loading questions from output/json/pulmo_01.json .. pulmo_15.json...")
    raw_questions = []
    for i in range(1, 16):
        p = base_dir / "output" / "json" / f"pulmo_{i:02d}.json"
        with open(p, 'r', encoding='utf-8') as f:
            raw_questions.extend(json.load(f))
    print(f"   Loaded {len(raw_questions)} questions.")

    print("\n3. Attaching topics, normalizing punctuation & subjects...")
    for q in raw_questions:
        qid = q['id']
        if qid not in topic_map:
            raise ValueError(f"Question ID '{qid}' not found in topics.txt!")
        q['topic_name'] = topic_map[qid]
        q['subject_name'] = "الصدرية"
        q['original_id'] = qid

        # Normalize punctuation
        q['title'] = normalize_stem_punct(q.get('title', ''))
        for opt in q.get('options', []):
            opt['text'] = normalize_option_punct(opt.get('text', ''))

    print("\n4. Grouping by topic and sorting chronologically within each topic...")
    topics_dict = {t: [] for t in TARGET_TOPICS_ORDER}
    for q in raw_questions:
        t = q['topic_name']
        if t not in topics_dict:
            raise ValueError(f"Unknown topic: '{t}'!")
        topics_dict[t].append(q)

    # Sort each topic chronologically (newest exam session to oldest)
    for t in TARGET_TOPICS_ORDER:
        topics_dict[t].sort(key=lambda q: parse_exam_date(q.get("exam_period")), reverse=True)
        count = len(topics_dict[t])
        first_date = topics_dict[t][0].get("exam_period") if count else ""
        last_date = topics_dict[t][-1].get("exam_period") if count else ""
        print(f"   • {t}: {count} questions ({first_date} -> {last_date})")

    # Combine questions in exact requested topic order
    sorted_questions = []
    for t in TARGET_TOPICS_ORDER:
        sorted_questions.extend(topics_dict[t])

    print(f"\n5. Re-indexing sequentially 1 to {len(sorted_questions)}...")
    for new_idx, q in enumerate(sorted_questions, start=1):
        num_str = f"{new_idx:03d}"
        q['id'] = f"q_pulmo_{num_str}"

    print(f"   Re-indexing complete: {sorted_questions[0]['id']} -> {sorted_questions[-1]['id']}")

    # 6. Save to all_pulmo/
    print("\n6. Saving master package in all_pulmo/...")
    all_pulmo_dir = base_dir / "all_pulmo"
    all_pulmo_dir.mkdir(parents=True, exist_ok=True)
    with open(all_pulmo_dir / "pulmo_all.json", "w", encoding="utf-8") as f:
        json.dump(sorted_questions, f, ensure_ascii=False, indent=2)

    df_all = questions_to_dataframe(sorted_questions)
    df_all.to_csv(all_pulmo_dir / "pulmo_all.csv", index=False, encoding="utf-8-sig")

    md_all = generate_markdown_prompt(sorted_questions)
    with open(all_pulmo_dir / "pulmo_all_ai.md", "w", encoding="utf-8") as f:
        f.write(md_all)

    # Save per-topic in all_pulmo/topics/
    all_pulmo_topics = all_pulmo_dir / "topics"
    all_pulmo_topics.mkdir(parents=True, exist_ok=True)
    for t_idx, t in enumerate(TARGET_TOPICS_ORDER, start=1):
        t_qs = [q for q in sorted_questions if q['topic_name'] == t]
        slug = sanitize_filename(t)
        base_name = f"pulmo_{t_idx:02d}_{slug}"
        with open(all_pulmo_topics / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(t_qs, f, ensure_ascii=False, indent=2)
        df_t = questions_to_dataframe(t_qs)
        df_t.to_csv(all_pulmo_topics / f"{base_name}.csv", index=False, encoding="utf-8-sig")

    # 7. Save to classified/
    print("\n7. Saving to classified/ (json/, csv/, md/)...")
    classified_dir = base_dir / "classified"
    for sub in ["json", "csv", "md"]:
        s_dir = classified_dir / sub
        s_dir.mkdir(parents=True, exist_ok=True)
        # remove old pulmo files if any
        for old_f in s_dir.glob("pulmo_*"):
            old_f.unlink()

    for t_idx, t in enumerate(TARGET_TOPICS_ORDER, start=1):
        t_qs = [q for q in sorted_questions if q['topic_name'] == t]
        slug = sanitize_filename(t)
        base_name = f"pulmo_{t_idx:02d}_{slug}"
        with open(classified_dir / "json" / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(t_qs, f, ensure_ascii=False, indent=2)
        df_t = questions_to_dataframe(t_qs)
        df_t.to_csv(classified_dir / "csv" / f"{base_name}.csv", index=False, encoding="utf-8-sig")
        with open(classified_dir / "md" / f"{base_name}_ai.md", "w", encoding="utf-8") as f:
            f.write(generate_markdown_prompt(t_qs))

    # 8. Slicing into chunks of 12 in output/sorted_chunks/
    print("\n8. Slicing into output/sorted_chunks/ (12 questions per chunk)...")
    chunks_dir = base_dir / "output" / "sorted_chunks"
    for sub in ["json", "csv", "md"]:
        s_dir = chunks_dir / sub
        s_dir.mkdir(parents=True, exist_ok=True)
        for old_f in s_dir.glob("pulmo_*"):
            old_f.unlink()

    chunk_size = 12
    for c_idx in range(0, len(sorted_questions), chunk_size):
        chunk_qs = sorted_questions[c_idx:c_idx + chunk_size]
        chunk_num = (c_idx // chunk_size) + 1
        base_name = f"pulmo_{chunk_num:02d}"

        with open(chunks_dir / "json" / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(chunk_qs, f, ensure_ascii=False, indent=2)
        df_chunk = questions_to_dataframe(chunk_qs)
        df_chunk.to_csv(chunks_dir / "csv" / f"{base_name}.csv", index=False, encoding="utf-8-sig")
        with open(chunks_dir / "md" / f"{base_name}_ai.md", "w", encoding="utf-8") as f:
            f.write(generate_markdown_prompt(chunk_qs))

    # 9. Also update output/json, output/csv, output/md directly with the newly sorted chunks
    print("\n9. Updating output/json, output/csv, output/md with new sorted chunks...")
    out_dir = base_dir / "output"
    for c_idx in range(0, len(sorted_questions), chunk_size):
        chunk_qs = sorted_questions[c_idx:c_idx + chunk_size]
        chunk_num = (c_idx // chunk_size) + 1
        base_name = f"pulmo_{chunk_num:02d}"

        with open(out_dir / "json" / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(chunk_qs, f, ensure_ascii=False, indent=2)
        df_chunk = questions_to_dataframe(chunk_qs)
        df_chunk.to_csv(out_dir / "csv" / f"{base_name}.csv", index=False, encoding="utf-8-sig")
        with open(out_dir / "md" / f"{base_name}_ai.md", "w", encoding="utf-8") as f:
            f.write(generate_markdown_prompt(chunk_qs))

    # 10. Update output/أسئلة دورات الصدرية.csv with sorted questions and topics
    print("\n10. Updating output/أسئلة دورات الصدرية.csv with topic classifications...")
    df_all.to_csv(out_dir / "أسئلة دورات الصدرية.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 65)
    print(" Pulmonology Topic Processing & Sorting Complete!")
    print("=" * 65)

if __name__ == "__main__":
    main()
