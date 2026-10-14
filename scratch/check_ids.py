import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for s in ['cardio', 'urology', 'vascular_surgery', 'plastic', 'onco', 'ped_surgery']:
    p = f'final/{s}/{s}_all.json'
    try:
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"{s}: count={len(data)}, first_id={data[0]['id']}, last_id={data[-1]['id']}")
    except Exception as e:
        print(f"{s}: error {e}")
