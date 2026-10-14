import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

exp_path = Path("working_on") / "explanations.txt"
with open(exp_path, 'r', encoding='utf-8') as f:
    text = f.read()

blocks = re.split(r'(?:^|\n)\s*#\s*(\d+)\s*\n', text)
parsed_blocks = {}
for i in range(1, len(blocks), 2):
    num = int(blocks[i])
    parsed_blocks[num] = blocks[i+1]

print("=== Sample Block 1 ===")
print(parsed_blocks[1][:600])

print("\n=== Sample Block 2 ===")
print(parsed_blocks[2][:600])

# Check for CLINICAL ERROR FLAG across all blocks
flags = []
for num, content in parsed_blocks.items():
    if "CLINICAL ERROR FLAG" in content or "خطأ علمي" in content or "تنبيه" in content:
        flags.append(num)

print(f"\nBlocks with potential flags/notes: {flags}")
for fn in flags:
    print(f"\n--- Flag in Block #{fn:02d} ---")
    for line in parsed_blocks[fn].splitlines():
        if any(w in line for w in ["CLINICAL ERROR FLAG", "خطأ علمي", "تنبيه"]):
            print(" ", line)
