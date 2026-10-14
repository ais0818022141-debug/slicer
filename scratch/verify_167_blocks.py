import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

exp_path = Path("working_on") / "explanations.txt"
with open(exp_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Split by header: e.g. #001, #1, #096, #97, #167
header_regex = r'(?:^|\n)\s*#\s*(\d+)\s*\n'
matches = list(re.finditer(header_regex, text))
print(f"Total question headers matched: {len(matches)}")

found_nums = []
for m in matches:
    found_nums.append(int(m.group(1)))

print(f"Numbers count: {len(found_nums)}")
print(f"Min: {min(found_nums)}, Max: {max(found_nums)}")

missing = [i for i in range(1, 168) if i not in found_nums]
duplicates = [n for n in set(found_nums) if found_nums.count(n) > 1]
print(f"Missing (1-167): {missing}")
print(f"Duplicates: {duplicates}")

# Extract each block: from match[i].end() to match[i+1].start()
blocks = {}
for i in range(len(matches)):
    num = int(matches[i].group(1))
    start_pos = matches[i].end()
    end_pos = matches[i+1].start() if i + 1 < len(matches) else len(text)
    block_content = text[start_pos:end_pos].strip()
    blocks[num] = block_content

print(f"Extracted blocks: {len(blocks)}")

# Verify sections for all 167 blocks
missing_obj = []
missing_hyn = []
missing_exp = []

for num, content in blocks.items():
    has_obj = bool(re.search(r'EDUCATIONAL\s+OBJECTIVE\s*:', content, re.IGNORECASE))
    has_hyn = bool(re.search(r'HIGH\s+YIELD\s+NOTE\s*:', content, re.IGNORECASE))
    has_exp = bool(re.search(r'EXPLANATION\s*:', content, re.IGNORECASE))
    
    if not has_obj: missing_obj.append(num)
    if not has_hyn: missing_hyn.append(num)
    if not has_exp: missing_exp.append(num)

print(f"Blocks missing Objective: {missing_obj}")
print(f"Blocks missing Note: {missing_hyn}")
print(f"Blocks missing Explanation: {missing_exp}")
