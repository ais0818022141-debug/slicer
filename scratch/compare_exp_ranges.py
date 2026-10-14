import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from scratch.verify_167_blocks import blocks

for qnum in [96, 97, 98, 105, 120, 150, 167]:
    b = blocks[qnum]
    exp_m = re.search(r'EXPLANATION\s*:\s*(.*?)(?=\n\s*---\s*|\Z)', b, re.DOTALL | re.IGNORECASE)
    exp = exp_m.group(1).strip() if exp_m else "NOT FOUND"
    print(f"\n==================== Question #{qnum} EXPLANATION ====================")
    print(exp[:500])
