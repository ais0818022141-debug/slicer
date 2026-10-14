import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('final/onco/onco_all.html', 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'(<div class="question-card" id="q_onco_04".*?)(?=<div class="question-card"|$)', content, re.DOTALL)
if m:
    print(m.group(1))
