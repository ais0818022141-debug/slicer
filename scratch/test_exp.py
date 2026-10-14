import re

with open(r"c:\Users\Toshiba\Desktop\slicer\working_on\Explanations.txt", "r", encoding="utf-8") as f:
    text = f.read()

lines = text.splitlines()
blocks = {}
current_num = None
current_lines = []

for line in lines:
    m = re.match(r'^\s*#(\d+)\s*$', line)
    if m:
        if current_num is not None:
            blocks[current_num] = "\n".join(current_lines).strip()
        current_num = int(m.group(1))
        current_lines = []
    else:
        current_lines.append(line)

if current_num is not None:
    blocks[current_num] = "\n".join(current_lines).strip()

print("Parsed blocks count:", len(blocks))
print("Min key:", min(blocks.keys()), "Max key:", max(blocks.keys()))

parsed_data = {}
for qnum, block_text in blocks.items():
    # 1. Educational objective
    obj_m = re.search(r'EDUCATIONAL\s+OBJECTIVE\s*:\s*(.*?)(?=\nHIGH\s+YIELD\s+NOTE\s*:|\nEXPLANATION\s*:|\n---|\Z)', block_text, re.DOTALL | re.IGNORECASE)
    # 2. High yield note
    hyn_m = re.search(r'HIGH\s+YIELD\s+NOTE\s*:\s*(.*?)(?=\nEXPLANATION\s*:|\n---|\Z)', block_text, re.DOTALL | re.IGNORECASE)
    # 3. Explanation
    exp_m = re.search(r'EXPLANATION\s*:\s*(.*?)(?=\n---|\Z)', block_text, re.DOTALL | re.IGNORECASE)

    obj = obj_m.group(1).strip() if obj_m else ""
    hyn = hyn_m.group(1).strip() if hyn_m else ""
    exp = exp_m.group(1).strip() if exp_m else ""

    parsed_data[qnum] = {
        "educational_objective": obj,
        "high_yield_note": hyn,
        "explanation": exp
    }

missing = [k for k, v in parsed_data.items() if not v['educational_objective'] or not v['high_yield_note'] or not v['explanation']]
print("Blocks with missing fields:", len(missing), missing)
