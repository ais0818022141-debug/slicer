import json
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for sub in ['onco', 'plastic', 'ped_surgery']:
    p = f'final/{sub}/{sub}_all.json'
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n=====================================")
    print(f"Sub: {sub}")
    print(f"=====================================")
    for q in data:
        exp = q.get('explanation', '')
        # Search if there is "الخيارات الأخرى:" or "تفنيد الخيارات:" followed by options without newlines
        m = re.search(r'(?:الخيارات\s+الأخرى|تفنيد\s+الخيارات)\s*[:：](.*)', exp, re.DOTALL)
        if m:
            opts_part = m.group(1).strip()
            # Count options
            found_opts = list(re.finditer(r'(?<![A-Za-z0-9])([A-F][:)])', opts_part))
            if len(found_opts) > 1:
                # Check how many are NOT preceded by newline
                inline_count = 0
                for o in found_opts:
                    pos = o.start()
                    if pos > 0 and opts_part[pos-1] != '\n':
                        inline_count += 1
                if inline_count > 0:
                    print(f"  [{q['id']}] has {inline_count} inline options in 'الخيارات الأخرى'")
