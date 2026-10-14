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
ARCHIVE_DIR = WORKING_DIR / "archive" / "plastic_onco"
BACKUP_DIR = WORKING_DIR / ".backup"

print("=" * 60)
print("Step 1: Archiving previous plastic_onco files")
print("=" * 60)

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
files_to_archive = ['topics.txt', 'explanations.txt']
for fn in files_to_archive:
    src = WORKING_DIR / fn
    dst = ARCHIVE_DIR / fn
    if src.exists():
        shutil.copyfile(src, dst)
        print(f"[✓] Archived file: {fn} -> {dst}")

print("\n" + "=" * 60)
print("Step 2: Preparing source CSV for Neurosurgery & Pediatric Surgery")
print("=" * 60)

raw_csv = WORKING_DIR / "أسئلة دورات جراحة عصبية واطفال.csv"
target_csv = WORKING_DIR / "neuro_peds.csv"
backup_raw = BACKUP_DIR / "أسئلة دورات جراحة عصبية واطفال_original.csv"

if not backup_raw.exists():
    shutil.copyfile(raw_csv, backup_raw)
    print(f"[✓] Backed up original CSV to {backup_raw.name}")

# Standardize encoding & save to neuro_peds.csv
df = pd.read_csv(raw_csv, encoding='utf-8-sig')
print(f"[✓] Read raw questions: {len(df)} rows")
df.to_csv(target_csv, index=False, encoding='utf-8-sig')
print(f"[✓] Saved standardized CSV -> {target_csv.name}")

print("\n" + "=" * 60)
print("Step 3: Running slicer.py to slice into 12-question chunks")
print("=" * 60)

# Run slicer tool
cmd = [
    sys.executable,
    str(BASE_DIR / "tools" / "slicer.py"),
    "--file", str(target_csv),
    "--prefix", "neuro_peds",
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

print("\n" + "=" * 60)
print("Step 4: Generating template topics.txt (96 entries)")
print("=" * 60)

topics_file = WORKING_DIR / "topics.txt"
with open(topics_file, 'w', encoding='utf-8') as f:
    for i in range(1, len(df) + 1):
        num_str = f"{i:02d}"
        f.write(f"#{num_str} [q_neuro_peds_{num_str}] ()\n")

print(f"[✓] Generated template {topics_file.name} with {len(df)} question placeholders.")

# Initialize fresh explanations.txt
expl_file = WORKING_DIR / "explanations.txt"
with open(expl_file, 'w', encoding='utf-8') as f:
    f.write("# TealMED Clinical Explanations - Neurosurgery & Pediatric Surgery\n")
    f.write("# Paste explanations here when ready.\n\n")

print(f"[✓] Initialized fresh {expl_file.name}")

print("\n" + "=" * 60)
print("Summary of Generated Files in working_on/:")
print(f"  - CSV chunks:  {len(list((WORKING_DIR / 'csv').glob('*.csv')))} files")
print(f"  - JSON chunks: {len(list((WORKING_DIR / 'json').glob('*.json')))} files")
print(f"  - MD prompts:  {len(list((WORKING_DIR / 'md').glob('*.md')))} files")
print(f"  - Topics:      {topics_file.name} (ready for filling)")
print("=" * 60)
