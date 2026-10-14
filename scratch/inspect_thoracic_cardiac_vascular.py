import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

csv_path = Path("working_on") / "أسئلة دورات جراحة صدرية وقلبية وأوعية.csv"
xlsx_path = Path("working_on") / "أسئلة دورات جراحة صدرية وقلبية وأوعية.xlsx"

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
        print(f"    Subject: {row.get('Medical_Subject')}")
        print(f"    Correct: {row.get('Correct_Answer')}")
        print(f"    W1: {row.get('Wrong_Answer_1')}")
