import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

csv_path = Path("working_on") / "أسئلة دورات جراحة عصبية واطفال.csv"
xlsx_path = Path("working_on") / "أسئلة دورات جراحة عصبية واطفال.xlsx"

print("Checking CSV:", csv_path.exists())
print("Checking XLSX:", xlsx_path.exists())

df = None
for enc in ["utf-8-sig", "utf-8", "cp1256"]:
    try:
        df = pd.read_csv(csv_path, encoding=enc)
        print(f"Loaded CSV with encoding: {enc}")
        break
    except Exception as e:
        pass

if df is None and xlsx_path.exists():
    df = pd.read_excel(xlsx_path)
    print("Loaded XLSX")

if df is not None:
    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())
    if "Medical_Subject" in df.columns:
        print("\nMedical_Subject counts:")
        print(df["Medical_Subject"].value_counts(dropna=False))
    if "Exam_Date" in df.columns:
        print("\nExam_Date counts:")
        print(df["Exam_Date"].value_counts(dropna=False))
    
    print("\nFirst 3 questions:")
    for i in range(min(3, len(df))):
        row = df.iloc[i]
        print(f"[{i+1}] {row.get('Question_Text', '')[:80]}")
        print(f"    Correct: {row.get('Correct_Answer')}")
        print(f"    W1: {row.get('Wrong_Answer_1')}")
        print(f"    W2: {row.get('Wrong_Answer_2')}")
        print(f"    W3: {row.get('Wrong_Answer_3')}")
        print(f"    W4: {row.get('Wrong_Answer_4')}")
