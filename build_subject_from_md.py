#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TealMED Root Launcher: Build Subject From Markdown Template
===========================================================
Usage:
  python build_subject_from_md.py QUESTION_TEMPLATE.md
  python build_subject_from_md.py (opens file picker dialog)
"""

import sys
from pathlib import Path

# Add tools to sys.path
tools_dir = Path(__file__).resolve().parent / "tools"
sys.path.insert(0, str(tools_dir))

from build_from_md_template import main

if __name__ == "__main__":
    main()
