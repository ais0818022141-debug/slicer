import json

with open('final/gync/gync_all.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('scratch_gync_edges.txt', 'w', encoding='utf-8') as out:
    for idx in [15, 207]:
        out.write(f"=== ROW {idx+1} ===\n")
        out.write(data[idx]['explanation'] + "\n\n")
