#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
FINAL = BASE / "final"


def build_explanations(items):
    lines = []
    for idx, item in enumerate(items, start=1):
        num_str = f"{idx:02d}"
        obj = (item.get("educational_objective") or "").strip()
        hy = (item.get("high_yield_note") or "").strip()
        exp = (item.get("explanation") or "").strip()
        lines.append(f"#{num_str}")
        lines.append("EDUCATIONAL OBJECTIVE:")
        lines.append(obj)
        lines.append("")
        lines.append("HIGH YIELD NOTE:")
        lines.append(hy)
        lines.append("")
        lines.append("EXPLANATION:")
        lines.append(exp)
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main():
    gs_json = FINAL / "general_surgery" / "general_surgery_all.json"
    gs_md = FINAL / "general_surgery" / "explanations.md"
    gs_items = json.loads(gs_json.read_text(encoding="utf-8"))
    gs_gen = build_explanations(gs_items)
    gs_exist = gs_md.read_text(encoding="utf-8")
    print("GS generated==existing", gs_gen == gs_exist)

    created = []
    skipped = []
    for d in sorted(p for p in FINAL.iterdir() if p.is_dir()):
        md_path = d / "explanations.md"
        json_files = list(d.glob("*_all.json"))
        if not json_files:
            skipped.append((d.name, "no json"))
            continue
        items = json.loads(json_files[0].read_text(encoding="utf-8"))
        if md_path.exists():
            skipped.append((d.name, f"already exists ({len(items)} q)"))
            continue
        content = build_explanations(items)
        md_path.write_text(content, encoding="utf-8")
        created.append((d.name, len(items), md_path.stat().st_size))

    print("CREATED", len(created))
    for name, n, sz in created:
        print(f"  {name:22s} {n:4d} questions  {sz:8d} bytes")
    print("SKIPPED")
    for name, reason in skipped:
        print(f"  {name:22s} {reason}")

    print("--- verify ---")
    failed = 0
    for d in sorted(p for p in FINAL.iterdir() if p.is_dir()):
        json_files = list(d.glob("*_all.json"))
        if not json_files:
            continue
        md = d / "explanations.md"
        n = len(json.loads(json_files[0].read_text(encoding="utf-8")))
        text = md.read_text(encoding="utf-8") if md.exists() else ""
        blocks = text.count("EXPLANATION:")
        headers = text.count("EDUCATIONAL OBJECTIVE:")
        hy = text.count("HIGH YIELD NOTE:")
        ok = md.exists() and blocks == n and headers == n and hy == n
        print(("OK" if ok else "FAIL"), d.name, "json", n, "exp", blocks, "edu", headers, "hy", hy)
        if not ok:
            failed += 1
    if failed:
        raise SystemExit(f"{failed} subjects failed verification")
    print("All subjects have matching explanations.md")


if __name__ == "__main__":
    main()
