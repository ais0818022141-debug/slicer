import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

exp_path = Path("working_on") / "explanations.txt"
with open(exp_path, 'r', encoding='utf-8') as f:
    text = f.read()

print(f"Total characters: {len(text)}")
print(f"Total lines: {len(text.splitlines())}")

# Find all headers like #01 or #1
header_matches = list(re.finditer(r'(?:^|\n)\s*#\s*(\d+)', text))
print(f"Total #number headers found: {len(header_matches)}")

numbers_found = [int(m.group(1)) for m in header_matches]
print("Numbers range:", min(numbers_found) if numbers_found else None, "to", max(numbers_found) if numbers_found else None)

missing = [i for i in range(1, 97) if i not in numbers_found]
duplicates = [n for n in set(numbers_found) if numbers_found.count(n) > 1]
print(f"Missing numbers (1-96): {missing}")
print(f"Duplicate numbers: {duplicates}")

# Check sample block 1, 2, 50, 96
blocks = re.split(r'(?:^|\n)\s*#\s*(\d+)\s*\n', text)
# re.split with capturing parentheses produces: [before, num1, block1, num2, block2, ...]
parsed_blocks = {}
for i in range(1, len(blocks), 2):
    num = int(blocks[i])
    content = blocks[i+1]
    parsed_blocks[num] = content

print(f"Successfully split into {len(parsed_blocks)} blocks")

for check_num in [1, 2, 52, 53, 95, 96]:
    if check_num in parsed_blocks:
        b = parsed_blocks[check_num]
        has_obj = "EDUCATIONAL OBJECTIVE" in b or "الهدف التعليمي" in b
        has_note = "HIGH YIELD NOTE" in b or "ملاحظة عالية الأهمية" in b
        has_exp = "EXPLANATION" in b or "الشرح" in b or "التعليل" in b
        print(f"Block #{check_num:02d}: len={len(b)}, Obj={has_obj}, Note={has_note}, Exp={has_exp}")
