import json

with open('final/obs/obs_all.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('scratch_obs_multiline.txt', 'w', encoding='utf-8') as out:
    count = 0
    for idx, q in enumerate(data):
        exp = q.get('explanation', '')
        lines = [line.strip() for line in exp.split('\n') if line.strip()]
        if len(lines) > 1:
            count += 1
            out.write(f"=== Q{idx+1} ===\n")
            for l_idx, l in enumerate(lines):
                out.write(f"  [{l_idx}]: {l}\n")
            out.write("\n")
            if count >= 10:
                break
