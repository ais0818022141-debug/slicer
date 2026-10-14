import os
import sys
import re
import json
import shutil
from pathlib import Path

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
WORKING_DIR = BASE_DIR / "working_on"
BACKUP_DIR = WORKING_DIR / ".backup"
EXP_FILE = WORKING_DIR / "explanations.txt"
JSON_FILE = BASE_DIR / "final" / "optho" / "optho_all.json"

NUMS_TO_REMOVE = [53, 55, 57, 70, 71, 72, 73, 103, 105, 113, 114, 115, 143, 145, 147, 149, 160, 161, 162, 183, 188, 205, 207, 211]

def main():
    print("=== Deduplicating working_on/explanations.txt ===")

    # 1. Backup original file
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / "explanations_214_backup.txt"
    shutil.copyfile(EXP_FILE, backup_path)
    print(f"[✓] Created backup at {backup_path.name}")

    # 2. Read explanations.txt
    with open(EXP_FILE, 'r', encoding='utf-8') as f:
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

    print(f"Parsed {len(blocks)} blocks from original file.")
    assert len(blocks) == 214, f"Expected 214 blocks, found {len(blocks)}"

    # 3. Filter to kept numbers
    kept_nums = [i for i in range(1, 215) if i not in NUMS_TO_REMOVE]
    print(f"Kept blocks count: {len(kept_nums)}")
    assert len(kept_nums) == 190

    # 4. Format the 190 blocks sequentially from #01 to #190
    new_blocks = []
    for new_idx, orig_num in enumerate(kept_nums, start=1):
        raw_content = blocks[orig_num]
        # Strip trailing separator line if present
        cleaned_content = re.sub(r'\n\s*---\s*$', '', raw_content).strip()

        block_str = f"#{new_idx:02d}\n{cleaned_content}\n\n---"
        new_blocks.append(block_str)

    output_text = "\n\n".join(new_blocks).strip() + "\n"

    # 5. Save back to working_on/explanations.txt
    with open(EXP_FILE, 'w', encoding='utf-8') as f:
        f.write(output_text)
    print(f"[✓] Saved updated {EXP_FILE.name} with 190 blocks.")

    # 6. Verify with final/optho/optho_all.json
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        q_data = json.load(f)

    assert len(q_data) == 190, f"JSON has {len(q_data)} items"

    # Re-parse saved file to verify structure
    with open(EXP_FILE, 'r', encoding='utf-8') as f:
        re_read_text = f.read()

    re_lines = re_read_text.splitlines()
    re_blocks = {}
    c_num = None
    c_lines = []
    for line in re_lines:
        m = re.match(r'^\s*#(\d+)\s*$', line)
        if m:
            if c_num is not None:
                re_blocks[c_num] = "\n".join(c_lines).strip()
            c_num = int(m.group(1))
            c_lines = []
        else:
            c_lines.append(line)
    if c_num is not None:
        re_blocks[c_num] = "\n".join(c_lines).strip()

    assert len(re_blocks) == 190, f"Re-read found {len(re_blocks)} blocks"
    missing_nums = [i for i in range(1, 191) if i not in re_blocks]
    assert len(missing_nums) == 0, f"Missing numbers: {missing_nums}"

    for i in range(1, 191):
        q = q_data[i - 1]
        b = re_blocks[i]
        q_obj = q.get('educational_objective', '').strip()
        assert q_obj in b, f"Objective mismatch at question #{i}"

    print("[✓] 100% Verified: All 190 blocks match final/optho/optho_all.json perfectly!")
    print("=== Deduplication of explanations.txt Completed Successfully ===")

if __name__ == "__main__":
    main()
