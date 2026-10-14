# -*- coding: utf-8 -*-
with open('final/onco/onco_all.html', 'r', encoding='utf-8') as f:
    c = f.read()

import re
idx2 = c.find('q_onco_02')
idx3 = c.find('q_onco_03')
q2_html = c[idx2:idx3]
print("=== Q_ONCO_02 Explanation items in HTML ===")
for m in re.finditer(r'<div class="exp-opt-item">.*?</div>', q2_html):
    print(" ", m.group(0))

idx4 = c.find('q_onco_04')
idx5 = c.find('q_onco_05')
q4_html = c[idx4:idx5]
print("\n=== Q_ONCO_04 Explanation items in HTML ===")
for m in re.finditer(r'<div class="exp-opt-item">.*?</div>', q4_html):
    print(" ", m.group(0))
