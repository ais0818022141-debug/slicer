import json
from pathlib import Path

final_dir = Path("final")
total_all = 0
total_with_edu = 0

header = f"{'Subject':<20} | {'Total Qs':<8} | {'With Edu Obj':<12} | {'Missing/Empty':<12}"
print(header)
print("-" * len(header))

for p in sorted(final_dir.iterdir()):
    if not p.is_dir() or p.name.startswith("."):
        continue
    j_file = p / f"{p.name}_all.json"
    if not j_file.exists():
        continue
    with open(j_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    n = len(data)
    with_edu = sum(1 for q in data if (q.get("educational_objective") or "").strip())
    missing = n - with_edu
    total_all += n
    total_with_edu += with_edu
    print(f"{p.name:<20} | {n:<8} | {with_edu:<12} | {missing:<12}")

print("-" * len(header))
print(f"{'TOTAL':<20} | {total_all:<8} | {total_with_edu:<12} | {total_all - total_with_edu:<12}")
