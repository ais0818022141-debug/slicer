import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open('working_on/thoracic_cardio_vasc_all.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for i, q in enumerate(data, start=1):
    opts = q.get('options', [])
    if len(opts) < 4:
        letters = [o.get('letter') for o in opts]
        print(f"Question #{i} has only {len(opts)} options: {letters}")
    for o in opts:
        if '\n' in o.get('text', ''):
            print(f"Question #{i} option {o.get('letter')} has newline: {repr(o.get('text'))}")
