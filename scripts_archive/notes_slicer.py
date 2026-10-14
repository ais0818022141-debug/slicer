"""
TealMED Clinical Notes Pipeline Shortcut
========================================
Runs the notes pipeline directly from the root slicer directory.

Usage:
  python notes_slicer.py
  python notes_slicer.py --file notes/notesEX.md
  python notes_slicer.py --dir notes --auto
"""

import sys
from pathlib import Path

cur_dir = Path(__file__).resolve().parent
notes_dir = cur_dir / "notes"
sys.path.insert(0, str(notes_dir))

from notes_pipeline import main

if __name__ == "__main__":
    main()
