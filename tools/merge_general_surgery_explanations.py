import os
import sys
import re
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
EXP_FILE = WORKING_DIR / "Explanations.txt"
JSON_MASTER = WORKING_DIR / "general_surgery_all.json"
CSV_MASTER = WORKING_DIR / "general_surgery_all.csv"

def parse_explanations(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    lines = text.splitlines()
    blocks = {}
    current_num = None
    current_lines = []

    for line in lines:
        m = re.match(r'^\s*#(\d+)\s*$', line)
        if m:
            if current_num is not None:
                blocks[current_num] = "\n".join(current_lines).strip()
            current_num = int(m.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    if current_num is not None:
        blocks[current_num] = "\n".join(current_lines).strip()

    parsed_data = {}
    for qnum, block_text in blocks.items():
        obj_m = re.search(r'EDUCATIONAL\s+OBJECTIVE\s*:\s*(.*?)(?=\nHIGH\s+YIELD\s+NOTE\s*:|\nEXPLANATION\s*:|\n---|\Z)', block_text, re.DOTALL | re.IGNORECASE)
        hyn_m = re.search(r'HIGH\s+YIELD\s+NOTE\s*:\s*(.*?)(?=\nEXPLANATION\s*:|\n---|\Z)', block_text, re.DOTALL | re.IGNORECASE)
        exp_m = re.search(r'EXPLANATION\s*:\s*(.*?)(?=\n---|\Z)', block_text, re.DOTALL | re.IGNORECASE)

        obj = obj_m.group(1).strip() if obj_m else ""
        hyn = hyn_m.group(1).strip() if hyn_m else ""
        exp = exp_m.group(1).strip() if exp_m else ""

        parsed_data[qnum] = {
            "educational_objective": obj,
            "high_yield_note": hyn,
            "explanation": exp
        }

    return parsed_data

def main():
    print("=== Merging Explanations for General Surgery ===")

    # 1. Parse Explanations.txt
    print(f"Loading {EXP_FILE.name}...")
    exp_map = parse_explanations(EXP_FILE)
    print(f"[✓] Successfully parsed {len(exp_map)} explanation blocks")

    # 2. Update Master JSON
    with open(JSON_MASTER, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    for idx, q in enumerate(questions, start=1):
        if idx in exp_map:
            entry = exp_map[idx]
            q['educational_objective'] = entry['educational_objective']
            q['high_yield_note'] = entry['high_yield_note']
            q['explanation'] = entry['explanation']

    with open(JSON_MASTER, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"[✓] Updated {JSON_MASTER.name} ({len(questions)} items)")

    # 3. Update Master CSV
    df = pd.read_csv(CSV_MASTER, encoding='utf-8-sig')
    for idx in range(len(df)):
        qnum = idx + 1
        if qnum in exp_map:
            entry = exp_map[qnum]
            df.at[idx, 'Explanation'] = entry['explanation']
            df.at[idx, 'High_Yield_Note'] = entry['high_yield_note']

    df.to_csv(CSV_MASTER, index=False, encoding='utf-8-sig')
    # Also sync general_surgery.csv
    df.to_csv(WORKING_DIR / "general_surgery.csv", index=False, encoding='utf-8-sig')
    print(f"[✓] Updated {CSV_MASTER.name} and general_surgery.csv")

    # 4. Update Sliced Chunks in working_on/json/ and working_on/csv/
    json_dir = WORKING_DIR / "json"
    csv_dir = WORKING_DIR / "csv"
    chunk_size = 12
    total_chunks = (len(questions) + chunk_size - 1) // chunk_size

    for c_idx in range(total_chunks):
        c_num = c_idx + 1
        tag = f"{c_num:02d}"
        c_json_path = json_dir / f"general_surgery_{tag}.json"
        c_csv_path = csv_dir / f"general_surgery_{tag}.csv"

        start_i = c_idx * chunk_size
        end_i = min(start_i + chunk_size, len(questions))

        chunk_q = questions[start_i:end_i]
        chunk_df = df.iloc[start_i:end_i]

        with open(c_json_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_q, f, ensure_ascii=False, indent=2)

        chunk_df.to_csv(c_csv_path, index=False, encoding='utf-8-sig')

    print(f"[✓] Updated all {total_chunks} chunk files in json/ and csv/")

    # 5. Generate Full AI Markdown with Explanations: working_on/general_surgery_all_ai_temp.md
    temp_md_lines = []
    for idx, q in enumerate(questions, start=1):
        num_str = f"{idx:03d}"
        qid = q['id']
        topic = q['topic_name']
        title = q['title']
        cor_let = q.get('correct_option', '')

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

    temp_md_path = WORKING_DIR / "general_surgery_all_ai_temp.md"
    with open(temp_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(temp_md_lines).strip() + "\n")
    print(f"[✓] Created full explanations Markdown: {temp_md_path.name}")

    print("=== Explanations Merge Completed Successfully ===")

if __name__ == "__main__":
    main()
