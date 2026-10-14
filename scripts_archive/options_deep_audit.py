import pandas as pd
import re

excel_path = r"c:\Users\Toshiba\Desktop\slicer\all_peds\أسئلة دورات الاطفال 2.xlsx"
df = pd.read_excel(excel_path)

faregh_rows = []
few_options_rows = []
duplicate_options_rows = []
short_question_rows = []

for idx, row in df.iterrows():
    row_num = idx + 2
    seq = row.get("الترتيب التسلسلي")
    q = str(row.get("نص السؤال", "")).strip() if pd.notna(row.get("نص السؤال")) else ""

    if len(q) < 10:
        short_question_rows.append((row_num, seq, q))

    opts = {}
    has_faregh = False
    for ch in "ABCDE":
        val = row.get(f"الخيار {ch}")
        if pd.notna(val):
            val_str = str(val).strip()
            if val_str == "فارغ":
                has_faregh = True
            elif val_str:
                opts[ch] = val_str

    if has_faregh:
        faregh_rows.append((row_num, seq, q[:50], {ch: str(row.get(f"الخيار {ch}")) for ch in "ABCDE"}))

    if len(opts) < 4:
        few_options_rows.append((row_num, seq, len(opts), opts))

    # check duplicates among non-empty options
    seen = {}
    for ch, txt in opts.items():
        if txt in seen:
            duplicate_options_rows.append((row_num, seq, ch, seen[txt], txt))
        seen[txt] = ch

print(f"Total Rows: {len(df)}")
print(f"Rows with 'فارغ': {len(faregh_rows)}")
print(f"Rows with fewer than 4 options: {len(few_options_rows)}")
print(f"Rows with duplicate options: {len(duplicate_options_rows)}")
print(f"Rows with suspiciously short questions: {len(short_question_rows)}")

with open("options_deep_audit.txt", "w", encoding="utf-8") as f:
    f.write(f"=== ROWS WITH 'فارغ' ({len(faregh_rows)}) ===\n")
    for r in faregh_rows:
        f.write(f"Row {r[0]} (Seq {r[1]}): Q: {r[2]}\n")
        f.write(f"   Options: {r[3]}\n\n")

    f.write(f"\n=== ROWS WITH FEWER THAN 4 OPTIONS ({len(few_options_rows)}) ===\n")
    for r in few_options_rows:
        f.write(f"Row {r[0]} (Seq {r[1]}): Count={r[2]} | Options: {r[3]}\n\n")

    f.write(f"\n=== ROWS WITH DUPLICATE OPTIONS ({len(duplicate_options_rows)}) ===\n")
    for r in duplicate_options_rows:
        f.write(f"Row {r[0]} (Seq {r[1]}): Opt {r[2]} duplicates Opt {r[3]}: '{r[4]}'\n\n")

print("Saved options_deep_audit.txt")
