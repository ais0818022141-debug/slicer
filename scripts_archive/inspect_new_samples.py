import json

for s in ['gync', 'obs', 'peds', 'peds1']:
    with open(f'final/{s}/{s}_all.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n=================== {s.upper()} SAMPLES ===================")
    for idx in [0, 1, 5, 10, 50, 100]:
        if idx < len(data):
            print(f"--- Q{idx+1} ---")
            print(data[idx]['explanation'])
