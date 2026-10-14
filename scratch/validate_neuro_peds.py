import sys
import re
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

csv_file = Path("working_on") / "أسئلة دورات جراحة عصبية واطفال.csv"
df = pd.read_csv(csv_file, encoding='utf-8-sig')

print(f"Total rows: {len(df)}")
print("Columns:", df.columns.tolist())

issues = []
for idx, row in df.iterrows():
    q_num = idx + 1
    q_text = str(row.get('Question_Text', '')).strip()
    c_ans = str(row.get('Correct_Answer', '')).strip()
    w1 = str(row.get('Wrong_Answer_1', '')).strip()
    w2 = str(row.get('Wrong_Answer_2', '')).strip()
    w3 = str(row.get('Wrong_Answer_3', '')).strip()
    w4 = str(row.get('Wrong_Answer_4', '')).strip()
    
    if not q_text or q_text == 'nan':
        issues.append(f"Row {q_num}: Missing Question_Text")
    if not c_ans or c_ans == 'nan':
        issues.append(f"Row {q_num}: Missing Correct_Answer")
    
    choices = [c_ans] + [w for w in [w1, w2, w3, w4] if w and w != 'nan']
    if len(choices) < 3:
        issues.append(f"Row {q_num}: Only {len(choices)} choices")
    
    # Check for HTML tags
    if '<' in q_text and '>' in q_text:
        print(f"HTML in Question {q_num}: {q_text[:60]}")

print(f"Total issues: {len(issues)}")
for iss in issues:
    print(" ", iss)
