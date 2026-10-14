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

def main():
    print("=== Synchronizing optho CSV changes across all files ===")

    # 1. Load the edited CSV from final/optho/optho_all.csv
    csv_final_path = FINAL_DIR / "optho_all.csv"
    df_final = pd.read_csv(csv_final_path, encoding='utf-8-sig')

    # Load master json from working_on to repair Excel #NAME? formula corruption in rows 157-162
    with open(WORKING_DIR / "optho_all.json", 'r', encoding='utf-8') as f:
        master_json = json.load(f)

    print("Checking and fixing Excel '#NAME?' artifacts in CSV...")
    fixed_explanations = 0
    for idx, row in df_final.iterrows():
        qid = row['Question_ID']
        exp_val = str(row['Explanation'])
        if '#NAME?' in exp_val or exp_val.strip() == '':
            # Restore genuine explanation from master_json
            orig_exp = master_json[idx]['explanation']
            df_final.at[idx, 'Explanation'] = orig_exp
            fixed_explanations += 1
            print(f"  [✓] Repaired explanation for row {idx+1} ({qid})")

    print(f"[✓] Repaired {fixed_explanations} '#NAME?' cells in CSV.")

    # 2. Save the cleaned CSV back to final/optho/optho_all.csv and sync to working_on
    df_final.to_csv(csv_final_path, index=False, encoding='utf-8-sig')
    df_final.to_csv(WORKING_DIR / "optho_all.csv", index=False, encoding='utf-8-sig')
    df_final.to_csv(WORKING_DIR / "optho.csv", index=False, encoding='utf-8-sig')
    print("[✓] Saved cleaned CSV to final/optho/optho_all.csv, working_on/optho_all.csv, and working_on/optho.csv")

    # 3. Synchronize Master JSON (both working_on and final)
    # The user updated row 156 (q_optho_156): Wrong_Answer_2 -> "اعتلال الشبكية والزجاجي التكاثري."
    q156 = master_json[155]
    print(f"Updating JSON for {q156['id']}...")
    for opt in q156['options']:
        if opt['letter'] == 'B' or 'اعتلال الشبكية والزجاجي التكاثري' in opt['text']:
            opt['text'] = "اعتلال الشبكية والزجاجي التكاثري."
            print("  [✓] Cleaned Option B text in JSON")

    # Save master_json
    with open(WORKING_DIR / "optho_all.json", 'w', encoding='utf-8') as f:
        json.dump(master_json, f, ensure_ascii=False, indent=2)
    with open(FINAL_DIR / "optho_all.json", 'w', encoding='utf-8') as f:
        json.dump(master_json, f, ensure_ascii=False, indent=2)
    print("[✓] Saved updated optho_all.json in both working_on and final/optho")

    # 4. Synchronize chunk files in working_on/json/ and working_on/csv/
    json_dir = WORKING_DIR / "json"
    csv_dir = WORKING_DIR / "csv"
    chunk_size = 12
    total_chunks = (len(master_json) + chunk_size - 1) // chunk_size

    for c_idx in range(total_chunks):
        c_num = c_idx + 1
        tag = f"{c_num:02d}"
        c_json_path = json_dir / f"optho_{tag}.json"
        c_csv_path = csv_dir / f"optho_{tag}.csv"

        start_i = c_idx * chunk_size
        end_i = min(start_i + chunk_size, len(master_json))

        chunk_q = master_json[start_i:end_i]
        chunk_df = df_final.iloc[start_i:end_i]

        with open(c_json_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_q, f, ensure_ascii=False, indent=2)
        chunk_df.to_csv(c_csv_path, index=False, encoding='utf-8-sig')

    print(f"[✓] Synced all {total_chunks} chunk files in working_on/json and working_on/csv")

    # 5. Generate optho_all_ai.md and optho_all_ai_temp.md from clean master_json
    ai_md_lines = []
    temp_md_lines = []

    for idx, q in enumerate(master_json, start=1):
        num_str = f"{idx:03d}"
        qid = q['id']
        topic = q['topic_name']
        title = q['title']
        cor_let = q.get('correct_option', '')

        # AI clean prompt lines
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

        # AI temp (with explanations) lines
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

    for out_dir in [WORKING_DIR, FINAL_DIR]:
        with open(out_dir / "optho_all_ai.md", 'w', encoding='utf-8') as f:
            f.write("\n".join(ai_md_lines).strip() + "\n")
        with open(out_dir / "optho_all_ai_temp.md", 'w', encoding='utf-8') as f:
            f.write("\n".join(temp_md_lines).strip() + "\n")

    print("[✓] Regenerated optho_all_ai.md and optho_all_ai_temp.md in both folders")

    print("=== Done base synchronization ===")

if __name__ == "__main__":
    main()
