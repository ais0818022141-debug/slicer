import json

subjects = ['cardio', 'endo', 'gastro', 'hema']

out = []
for s in subjects:
    with open(f'final/{s}/{s}_all.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    out.append(f"================== {s.upper()} ==================")
    for i in range(5):
        q = data[i]
        out.append(f"--- Q{i+1} ---")
        out.append(q['explanation'])
        out.append("")

with open('scratch_older_explanations.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print("Saved scratch_older_explanations.txt")
