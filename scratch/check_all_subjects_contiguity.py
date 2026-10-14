import json
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

final_dir = Path('final')
for sub_dir in sorted(final_dir.iterdir()):
    if not sub_dir.is_dir():
        continue
    j_files = list(sub_dir.glob('*_all.json'))
    if not j_files:
        continue
    with open(j_files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)
    topics = [q.get('topic_name') for q in data]
    # Check if contiguous
    seen = set()
    curr = None
    contiguous = True
    for t in topics:
        if t != curr:
            if t in seen:
                contiguous = False
                break
            seen.add(t)
            curr = t
    print(f"{sub_dir.name:20s}: {len(data):3d} questions | Contiguous topics: {contiguous}")
