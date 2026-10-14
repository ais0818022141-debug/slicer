# -*- coding: utf-8 -*-
with open('final/plastic/plastic_all.html', 'r', encoding='utf-8') as f:
    c = f.read()

count = c.count('class="exp-opt-item"')
print(f"Total exp-opt-item in plastic_all.html: {count}")
idx = c.find('class="exp-opt-item"')
if idx != -1:
    print("Sample:\n", c[idx-10:idx+250])
