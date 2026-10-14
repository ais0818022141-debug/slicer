import json
from pathlib import Path

final_dir = Path("final")

with open("sample_explanations.txt", "w", encoding="utf-8") as out:
    for sub in ['cardio', 'endo', 'gastro', 'renal', 'hema', 'rheuma', 'peds', 'peds1', 'gync', 'obs']:
        data = json.load(open(final_dir / sub / f'{sub}_all.json', encoding='utf-8'))
        out.write(f"==================== {sub.upper()} ====================\n")
        for i in range(min(3, len(data))):
            out.write(f"--- Q{i+1} [{data[i]['id']}] (Correct: {data[i]['correct_option']}) ---\n")
            out.write(data[i]['explanation'] + "\n\n")

print("Saved sample_explanations.txt")
