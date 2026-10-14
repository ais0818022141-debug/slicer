import json
with open("final/manifest.json", 'r', encoding='utf-8') as f:
    d = json.load(f)
print("plastic:", json.dumps(d['subjects'].get('plastic'), ensure_ascii=False, indent=2))
print("onco:", json.dumps(d['subjects'].get('onco'), ensure_ascii=False, indent=2))
