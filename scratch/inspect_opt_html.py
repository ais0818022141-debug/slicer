# -*- coding: utf-8 -*-
with open('final/onco/onco_all.html', 'r', encoding='utf-8') as f:
    c = f.read()

import re
matches = re.findall(r'<div class="exp-opt-item">.*?</div>', c)
for idx, m in enumerate(matches[:8], 1):
    print(f"[{idx}] {m}")
