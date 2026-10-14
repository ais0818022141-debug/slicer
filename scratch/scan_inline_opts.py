import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for sub in ['onco', 'plastic', 'ped_surgery']:
    p = Path(f'final/{sub}/{sub}_all.json')
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n=====================================")
    print(f"Checking {sub} ({len(data)} questions)")
    print(f"=====================================")
    for q in data:
        exp = q.get('explanation', '')
        # Pattern 1: Option letter not at start of line
        # i.e. some non-newline character, then space, then [A-F]\)
        inline_opts = list(re.finditer(r'([^\n]{3,})\s+([A-F]\))', exp))
        # Filter out if it's "الخيارات الأخرى: A)"
        filtered = []
        for m in inline_opts:
            pre = m.group(1).strip()
            # If preceding text doesn't end with "الخيارات الأخرى:" or similar header
            if not re.search(r'(?:الخيارات\s+الأخرى|تفنيد\s+الخيارات)\s*[:：]$', pre):
                filtered.append((pre[-30:], m.group(2)))
        if filtered:
            print(f"  [{q['id']}] Inline options found:")
            for pre, opt in filtered:
                print(f"     ...{pre} ---> {opt}")
