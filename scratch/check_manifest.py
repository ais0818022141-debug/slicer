import json
with open("final/manifest.json", 'r', encoding='utf-8') as f:
    d = json.load(f)
print("Keys in subjects:", list(d.get("subjects", {}).keys()))
