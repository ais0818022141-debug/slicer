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

# Find all question headers like #001, #96, #096, #97, #097
blocks = re.split(r'\n(?=\s*#\s*\d+)', text)
print(f"Total raw blocks split by header: {len(blocks)}")

# Let's see how headers are formatted for questions 90-105
for b in blocks[:5]:
    first_lines = "\n".join(b.strip().splitlines()[:5])
    print("--- Block start sample ---")
    print(first_lines)

print("\n=== Inspecting Blocks 95 to 102 ===")
for b in blocks:
    m = re.match(r'^\s*#\s*(\d+)', b.strip())
    if m:
        num = int(m.group(1))
        if 95 <= num <= 100:
            print(f"\n================ Question #{num} ================")
            print(b[:700])
