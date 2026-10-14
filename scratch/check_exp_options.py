import csv
import sys
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for sub in ['onco', 'plastic', 'ped_surgery']:
    p = f'final/{sub}/{sub}_all.csv'
    with open(p, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    print(f"\n=====================================")
    print(f"Sub: {sub} ({len(rows)} rows)")
    print(f"=====================================")
    for idx, r in enumerate(rows, 1):
        exp = r.get('Explanation', '')
        # Check if there are patterns like "A) ", "B) ", etc.
        opt_matches = list(re.finditer(r'(?:^|\s|\n)([A-F]\))', exp))
        if len(opt_matches) > 1:
            # Check if options are on newlines or inline
            has_inline = False
            for m in opt_matches:
                pos = m.start()
                pre = exp[max(0, pos-15):pos]
                if pre and not pre.endswith('\n') and not pre.endswith('\n\n'):
                    has_inline = True
            if has_inline or 'MEN2B' in exp or 'RET' in exp:
                print(f"Row #{idx} [{r.get('Question_ID')}]: has multiple options in explanation")
                for m in opt_matches:
                    start = max(0, m.start() - 25)
                    end = min(len(exp), m.end() + 25)
                    print(f"   Snippet around {m.group(1)}: {repr(exp[start:end])}")
