import os
import sys
import shutil
import subprocess
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\Toshiba\Desktop\slicer")
WORKING_DIR = BASE_DIR / "working_on"
ARCHIVE_DIR = WORKING_DIR / "archive" / "neuro_peds"
BACKUP_DIR = WORKING_DIR / ".backup"

print("=" * 65)
print("Step 1: Archiving neuro_peds files to archive/neuro_peds/")
print("=" * 65)

ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# 1. Archive subfolders from working_on
subfolders = ['csv', 'json', 'md', 'sessions', 'topics', 'years']
for fld in subfolders:
    src = WORKING_DIR / fld
    dst = ARCHIVE_DIR / fld
    if src.exists() and any(src.iterdir()):
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"[✓] Archived folder: {fld} -> {dst}")
        # Clean source folder
        shutil.rmtree(src)
        src.mkdir(exist_ok=True)
    else:
        src.mkdir(exist_ok=True)

# 2. Archive files from working_on
files_to_archive = [
    'topics.txt', 'explanations.txt',
    'neuro_peds.csv', 'neuro_peds_all.csv',
    'neuro_peds_all.json', 'neuro_peds_all_ai.md',
    'neuro_peds_all_ai_temp.md'
]
for fn in files_to_archive:
    src = WORKING_DIR / fn
    dst = ARCHIVE_DIR / fn
    if src.exists():
        shutil.copyfile(src, dst)
        print(f"[✓] Archived file: {fn} -> {dst}")
        src.unlink()

print("\n" + "=" * 65)
print("Step 2: Preparing source CSV for Thoracic, Cardiac & Vascular Surgery")
print("=" * 65)

raw_csv = WORKING_DIR / "أسئلة دورات جراحة صدرية وقلبية وأوعية.csv"
target_csv = WORKING_DIR / "thoracic_cardio_vasc.csv"
backup_raw = BACKUP_DIR / "أسئلة دورات جراحة صدرية وقلبية وأوعية_original.csv"

if not backup_raw.exists():
    shutil.copyfile(raw_csv, backup_raw)
    print(f"[✓] Backed up raw CSV to {backup_raw.name}")

df = pd.read_csv(raw_csv, encoding='utf-8-sig')
print(f"[✓] Read raw questions: {len(df)} rows")
df.to_csv(target_csv, index=False, encoding='utf-8-sig')
print(f"[✓] Saved standardized CSV -> {target_csv.name}")

print("\n" + "=" * 65)
print("Step 3: Running slicer.py to slice into 12-question chunks")
print("=" * 65)

cmd = [
    sys.executable,
    str(BASE_DIR / "tools" / "slicer.py"),
    "--file", str(target_csv),
    "--prefix", "thoracic_cardio_vasc",
    "--rows", "12",
    "--out", str(WORKING_DIR),
    "--auto"
]

res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(res.stdout)
if res.returncode != 0:
    print("[!] Error running slicer.py:")
    print(res.stderr)
    sys.exit(1)

print("\n" + "=" * 65)
print(f"Step 4: Generating template topics.txt ({len(df)} entries)")
print("=" * 65)

topics_file = WORKING_DIR / "topics.txt"
q_pad_width = max(2, len(str(len(df))))

with open(topics_file, 'w', encoding='utf-8') as f:
    for i in range(1, len(df) + 1):
        num_str = f"{i:0{q_pad_width}d}"
        f.write(f"#{num_str} [q_thoracic_cardio_vasc_{num_str}] ()\n")

print(f"[✓] Generated template {topics_file.name} with {len(df)} question placeholders.")

# Initialize fresh explanations.txt
expl_file = WORKING_DIR / "explanations.txt"
with open(expl_file, 'w', encoding='utf-8') as f:
    f.write("# TealMED Clinical Explanations - Thoracic, Cardiac & Vascular Surgery\n")
    f.write("# Paste explanations here when ready.\n\n")

print(f"[✓] Initialized fresh {expl_file.name}")

print("\n" + "=" * 65)
print("Summary of Generated Files in working_on/:")
print(f"  - CSV chunks:  {len(list((WORKING_DIR / 'csv').glob('*.csv')))} files")
print(f"  - JSON chunks: {len(list((WORKING_DIR / 'json').glob('*.json')))} files")
print(f"  - MD prompts:  {len(list((WORKING_DIR / 'md').glob('*.md')))} files")
print(f"  - Topics:      {topics_file.name} (ready for filling)")
print("=" * 65)
