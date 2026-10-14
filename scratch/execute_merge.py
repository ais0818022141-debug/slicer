import sys
import csv
import shutil
from pathlib import Path
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
WORKING_DIR = BASE_DIR / "working_on"
FINAL_DIR = BASE_DIR / "final"

def backup_file(p: Path):
    backup_dir = p.parent / ".backup"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    b_path = backup_dir / f"{p.stem}_premerge_{ts}{p.suffix}"
    shutil.copyfile(p, b_path)
    print(f"[Backup] Created: {b_path.name}")
    return b_path

def merge_onco():
    source_csv = WORKING_DIR / "أسئلة دورات أورام.csv"
    target_csv = FINAL_DIR / "onco" / "onco_all.csv"

    backup_file(target_csv)

    # Read existing target
    with open(target_csv, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        target_headers = list(reader.fieldnames)
        existing_rows = list(reader)

    print(f"[Onco] Existing questions in target: {len(existing_rows)}")

    # Read source
    with open(source_csv, 'r', encoding='utf-8-sig', errors='replace', newline='') as f:
        source_rows = list(csv.reader(f))

    print(f"[Onco] Source questions to merge: {len(source_rows)}")

    # The 13 standard columns
    headers_13 = ['Question_ID', 'Medical_Subject', 'Exam_Date', 'Chapter_or_Section', 
                  'Question_Text', 'Explanation', 'High_Yield_Note', 'Correct_Answer', 
                  'Wrong_Answer_1', 'Wrong_Answer_2', 'Wrong_Answer_3', 'Wrong_Answer_4', 
                  'Wrong_Answer_5']

    new_rows = []
    start_num = len(existing_rows) + 1  # 12
    for idx, srow in enumerate(source_rows):
        qid = f"q_onco_{start_num + idx:02d}"
        subj = "جراحة الأورام"
        date = srow[2].strip() if len(srow) > 2 else ""
        topic = "جراحة أورام الغدة الدرقية وجارات الدرق"
        qtext = srow[4].strip() if len(srow) > 4 else ""
        exp = srow[5].strip() if len(srow) > 5 else ""
        hy = srow[6].strip() if len(srow) > 6 else ""
        cor = srow[7].strip() if len(srow) > 7 else ""
        w1 = srow[8].strip() if len(srow) > 8 else ""
        w2 = srow[9].strip() if len(srow) > 9 else ""
        w3 = srow[10].strip() if len(srow) > 10 else ""
        w4 = srow[11].strip() if len(srow) > 11 else ""
        w5 = srow[12].strip() if len(srow) > 12 else ""

        row_dict = {
            'Question_ID': qid,
            'Medical_Subject': subj,
            'Exam_Date': date,
            'Chapter_or_Section': topic,
            'Question_Text': qtext,
            'Explanation': exp,
            'High_Yield_Note': hy,
            'Correct_Answer': cor,
            'Wrong_Answer_1': w1,
            'Wrong_Answer_2': w2,
            'Wrong_Answer_3': w3,
            'Wrong_Answer_4': w4,
            'Wrong_Answer_5': w5,
        }
        new_rows.append(row_dict)

    combined_rows = existing_rows + new_rows
    print(f"[Onco] Combined total rows: {len(combined_rows)}")

    with open(target_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers_13)
        writer.writeheader()
        writer.writerows(combined_rows)

    print(f"[✓] Successfully wrote {len(combined_rows)} rows to {target_csv.name}")

def merge_plastic():
    source_csv = WORKING_DIR / "أسئلة دورات تجميلية.csv"
    target_csv = FINAL_DIR / "plastic" / "plastic_all.csv"

    backup_file(target_csv)

    # Read existing target
    with open(target_csv, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        target_headers = list(reader.fieldnames)
        existing_rows = list(reader)

    print(f"[Plastic] Existing questions in target: {len(existing_rows)}")

    # Read source
    with open(source_csv, 'r', encoding='utf-8-sig', errors='replace', newline='') as f:
        source_rows = list(csv.reader(f))

    print(f"[Plastic] Source questions to merge: {len(source_rows)}")

    headers_13 = ['Question_ID', 'Medical_Subject', 'Exam_Date', 'Chapter_or_Section', 
                  'Question_Text', 'Explanation', 'High_Yield_Note', 'Correct_Answer', 
                  'Wrong_Answer_1', 'Wrong_Answer_2', 'Wrong_Answer_3', 'Wrong_Answer_4', 
                  'Wrong_Answer_5']

    new_rows = []
    start_num = len(existing_rows) + 1  # 67
    for idx, srow in enumerate(source_rows):
        qid = f"q_plastic_{start_num + idx:02d}"
        subj = "الجراحة التجميلية"
        date = srow[2].strip() if len(srow) > 2 else ""
        topic = "سرطانات الجلد والآفات السطحية"
        qtext = srow[4].strip() if len(srow) > 4 else ""
        exp = srow[5].strip() if len(srow) > 5 else ""
        hy = srow[6].strip() if len(srow) > 6 else ""
        cor = srow[7].strip() if len(srow) > 7 else ""
        w1 = srow[8].strip() if len(srow) > 8 else ""
        w2 = srow[9].strip() if len(srow) > 9 else ""
        w3 = srow[10].strip() if len(srow) > 10 else ""
        w4 = srow[11].strip() if len(srow) > 11 else ""
        w5 = srow[12].strip() if len(srow) > 12 else ""

        row_dict = {
            'Question_ID': qid,
            'Medical_Subject': subj,
            'Exam_Date': date,
            'Chapter_or_Section': topic,
            'Question_Text': qtext,
            'Explanation': exp,
            'High_Yield_Note': hy,
            'Correct_Answer': cor,
            'Wrong_Answer_1': w1,
            'Wrong_Answer_2': w2,
            'Wrong_Answer_3': w3,
            'Wrong_Answer_4': w4,
            'Wrong_Answer_5': w5,
        }
        new_rows.append(row_dict)

    combined_rows = existing_rows + new_rows
    print(f"[Plastic] Combined total rows: {len(combined_rows)}")

    with open(target_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers_13)
        writer.writeheader()
        writer.writerows(combined_rows)

    print(f"[✓] Successfully wrote {len(combined_rows)} rows to {target_csv.name}")

if __name__ == "__main__":
    print("=== STARTING MERGE OPERATION ===")
    merge_onco()
    print()
    merge_plastic()
    print("\n=== MERGE OPERATION COMPLETED ===")
