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
EXP_FILE = WORKING_DIR / "explanations.txt"
JSON_MASTER = WORKING_DIR / "thoracic_cardio_vasc_all.json"
CSV_MASTER = WORKING_DIR / "thoracic_cardio_vasc_all.csv"

def parse_explanation_block(num: int, block_text: str):
    """
    Parses a single explanation block handling all styling differences:
    - 1-96 (bullet style * with separate lines A:, B:)
    - 97-120 (dash style - with inline options like B خطأ، ... C خطأ، ...)
    - 121-167 (dash style - with separate lines A) ..., B) ...)
    - Preserves clinical error flags
    """
    # 1. Educational objective
    obj_m = re.search(r'EDUCATIONAL\s+OBJECTIVE\s*:\s*(.*?)(?=\nHIGH\s+YIELD\s+NOTE|\Z)', block_text, re.DOTALL | re.IGNORECASE)
    obj = obj_m.group(1).strip() if obj_m else ""

    # 2. High yield note
    note_m = re.search(r'HIGH\s+YIELD\s+NOTE\s*:\s*(.*?)(?=\nEXPLANATION|\Z)', block_text, re.DOTALL | re.IGNORECASE)
    note = note_m.group(1).strip() if note_m else ""

    # 3. Raw explanation
    exp_m = re.search(r'EXPLANATION\s*:\s*(.*)', block_text, re.DOTALL | re.IGNORECASE)
    exp_raw = exp_m.group(1).strip() if exp_m else ""

    # Remove trailing ---
    exp_raw = re.sub(r'\n\s*---\s*$', '', exp_raw).strip()

    # 4. Extract clinical error flag if present (either (CLINICAL ERROR FLAG: ...) or CLINICAL ERROR FLAG: ...)
    flag = ""
    flag_m = re.search(r'\(?\s*CLINICAL\s+ERROR\s+FLAG\s*[:：]?\s*(.*?)\)?\s*$', exp_raw, re.DOTALL | re.IGNORECASE)
    if flag_m:
        flag = flag_m.group(1).strip().rstrip(')')
        exp_raw = exp_raw[:flag_m.start()].strip()

    # 5. Split into clinical reasoning and other options
    split_m = re.search(r'(?:^|\n)\s*[\*\-•]?\s*الخيارات\s+الأخرى\s*[:：]\s*(.*)', exp_raw, re.DOTALL)
    if split_m:
        khiarat_raw = split_m.group(1).strip()
        t3leel_raw = exp_raw[:split_m.start()].strip()
    else:
        khiarat_raw = ""
        t3leel_raw = exp_raw

    # Clean clinical reasoning header
    t3leel = re.sub(r'^(?:[\*\-•]\s*)?(التعليل\s+السريري|التعليل|الشرح)\s*[:：]\s*', '', t3leel_raw).strip()

    # 6. Parse and standardize other options
    lines = [l.strip() for l in khiarat_raw.splitlines() if l.strip()]
    formatted_options = []

    for l in lines:
        l = re.sub(r'^\*\s*', '', l).strip()
        
        # Check if line contains inline options like 'B خطأ، ... C خطأ، ...' or 'A ... B ...'
        parts = re.split(r'(?<=[.،؛\)])\s+(?=[A-E][:\)\s])', l)
        if len(parts) == 1 and not re.match(r'^[A-E][:\)]\s', l):
            # Check if start is e.g. 'B خطأ'
            parts = re.split(r'(?<=[.،؛])\s+(?=[A-E]\s)', l)

        for p in parts:
            p = p.strip()
            if not p:
                continue
            # Match A: or A)
            m_opt = re.match(r'^([A-E])\s*[:）)]\s*(.*)', p)
            if m_opt:
                formatted_options.append(f"{m_opt.group(1)}) {m_opt.group(2).strip()}")
            else:
                # Match A followed by Arabic text (e.g. 'B خطأ، فالجراحة...')
                m_opt2 = re.match(r'^([A-E])\s+([\u0600-\u06FF].*)', p)
                if m_opt2:
                    formatted_options.append(f"{m_opt2.group(1)}) {m_opt2.group(2).strip()}")
                else:
                    formatted_options.append(p)

    # 7. Assemble standardized explanation
    clean_parts = []
    clean_parts.append(f"- التعليل السريري: {t3leel}")
    if formatted_options:
        clean_parts.append("- الخيارات الأخرى:\n" + "\n\n".join(formatted_options))
    if flag:
        clean_parts.append(f"- تنبيه سريري (Clinical Error Flag): {flag}")

    final_exp = "\n\n".join(clean_parts).strip()

    return {
        "educational_objective": obj,
        "high_yield_note": note,
        "explanation": final_exp
    }

def parse_all_explanations(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Find headers like #001, #01, #1
    pattern = re.compile(r'(?:^|\n)\s*#\s*(\d+)(?:\s+\[.*?\])?(?:\s+\(.*?\))?\s*\n')
    matches = list(pattern.finditer(text))

    blocks = {}
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks[num] = text[start:end].strip()

    parsed_data = {}
    for num, block_text in blocks.items():
        parsed_data[num] = parse_explanation_block(num, block_text)

    return parsed_data

def main():
    print("=== Merging Explanations for Thoracic, Cardiac & Vascular Surgery ===")

    # 1. Parse explanations.txt
    print(f"Loading {EXP_FILE.name}...")
    exp_map = parse_all_explanations(EXP_FILE)
    print(f"[✓] Successfully parsed {len(exp_map)} explanation blocks")

    if len(exp_map) != 167:
        missing = [i for i in range(1, 168) if i not in exp_map]
        print(f"[!] Warning: Expected 167 items, got {len(exp_map)}. Missing: {missing}")
    else:
        print("[✓] All 167 explanation blocks matched!")

    # Check for clinical error flags
    flag_count = sum(1 for d in exp_map.values() if "Clinical Error Flag" in d["explanation"])
    print(f"[✓] Preserved {flag_count} CLINICAL ERROR FLAG note(s) inside explanations.")

    # 2. Update Master JSON
    with open(JSON_MASTER, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    print(f"Loaded {len(questions)} questions from {JSON_MASTER.name}")

    for idx, q in enumerate(questions, start=1):
        if idx in exp_map:
            entry = exp_map[idx]
            q['educational_objective'] = entry['educational_objective']
            q['high_yield_note'] = entry['high_yield_note']
            q['explanation'] = entry['explanation']
        else:
            print(f"[!] Question #{idx} not found in explanation map!")

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
    # Also sync thoracic_cardio_vasc.csv
    df.to_csv(WORKING_DIR / "thoracic_cardio_vasc.csv", index=False, encoding='utf-8-sig')
    print(f"[✓] Updated {CSV_MASTER.name} and thoracic_cardio_vasc.csv")

    # 4. Update Sliced Chunks in working_on/json/ and working_on/csv/
    json_dir = WORKING_DIR / "json"
    csv_dir = WORKING_DIR / "csv"
    chunk_size = 12
    total_chunks = (len(questions) + chunk_size - 1) // chunk_size

    for c_idx in range(total_chunks):
        c_num = c_idx + 1
        tag = f"{c_num:02d}"
        c_json_path = json_dir / f"thoracic_cardio_vasc_{tag}.json"
        c_csv_path = csv_dir / f"thoracic_cardio_vasc_{tag}.csv"

        start_i = c_idx * chunk_size
        end_i = min(start_i + chunk_size, len(questions))

        chunk_q = questions[start_i:end_i]
        with open(c_json_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_q, f, ensure_ascii=False, indent=2)

        chunk_df = df.iloc[start_i:end_i]
        chunk_df.to_csv(c_csv_path, index=False, encoding='utf-8-sig')

    print(f"[✓] Synchronized {total_chunks} chunk files in json/ and csv/")

    # 5. Generate thoracic_cardio_vasc_all_ai_temp.md (Full clinical review file)
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

    temp_md_path = WORKING_DIR / "thoracic_cardio_vasc_all_ai_temp.md"
    with open(temp_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(temp_md_lines).strip() + "\n")
    print(f"[✓] Created master AI review file: {temp_md_path.name} ({len(questions)} questions)")

    # 6. Update working_on/explanations.txt with clean formatted text
    clean_exp_lines = []
    for idx in range(1, len(questions) + 1):
        num_str = f"{idx:03d}"
        entry = exp_map[idx]
        q = questions[idx - 1]
        clean_exp_lines.append(f"#{num_str} [{q['id']}] ({q['topic_name']})")
        clean_exp_lines.append(f"EDUCATIONAL OBJECTIVE:\n{entry['educational_objective']}\n")
        clean_exp_lines.append(f"HIGH YIELD NOTE:\n{entry['high_yield_note']}\n")
        clean_exp_lines.append(f"EXPLANATION:\n{entry['explanation']}\n")
        clean_exp_lines.append("---\n")

    with open(EXP_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(clean_exp_lines).strip() + "\n")
    print(f"[✓] Refreshed {EXP_FILE.name} with clean standardized formatting")

    print("\n=== Explanation Merge Completed Successfully ===")

if __name__ == "__main__":
    main()
