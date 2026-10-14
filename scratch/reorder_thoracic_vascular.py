import sys
import csv
import shutil
import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
FINAL_DIR = BASE_DIR / "final"

def backup_file(p: Path):
    backup_dir = p.parent / ".backup"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    b_path = backup_dir / f"{p.stem}_prereorder_{ts}{p.suffix}"
    shutil.copyfile(p, b_path)
    print(f"[Backup] Created: {b_path.name}")
    return b_path

def reorder_subject(sub_slug: str, target_order: list):
    sub_dir = FINAL_DIR / sub_slug
    csv_path = sub_dir / f"{sub_slug}_all.csv"
    if not csv_path.exists():
        print(f"[!] Error: File not found {csv_path}")
        return False
    
    backup_file(csv_path)

    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = [c.lstrip('\ufeff') for c in reader.fieldnames]
        rows = list(reader)

    # Clean BOM from keys
    cleaned_rows = []
    for r in rows:
        cleaned_rows.append({(k.lstrip('\ufeff') if isinstance(k, str) else k): v for k, v in r.items()})
    rows = cleaned_rows

    print(f"\n=======================================================")
    print(f" Reordering {sub_slug} ({len(rows)} questions)")
    print(f"=======================================================")

    topics_rows = {t: [] for t in target_order}
    other_rows = []

    for r in rows:
        t = (r.get('Chapter_or_Section') or '').strip()
        if t in topics_rows:
            topics_rows[t].append(r)
        else:
            other_rows.append(r)

    if other_rows:
        print(f"[!] Warning: Found {len(other_rows)} rows in unexpected topics:")
        for r in other_rows:
            print(f"    {r.get('Question_ID')}: {r.get('Chapter_or_Section')}")

    reordered_rows = []
    for idx, t in enumerate(target_order, 1):
        qs = topics_rows[t]
        print(f"  {idx:02d}. {t}: {len(qs)} questions")
        reordered_rows.extend(qs)

    reordered_rows.extend(other_rows)
    assert len(reordered_rows) == len(rows), f"Row count mismatch in {sub_slug}!"

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reordered_rows)

    print(f"[✓] Successfully reordered {csv_path.name}")
    return True

def main():
    thoracic_order = [
        "رضوض الصدر والأذيات الإسعافية",
        "أمراض وجراحة الجنب",
        "سرطان الرئة والنقائل الورمية",
        "الآفات الرئوية الإنتانية والخمجية",
        "تشوهات جدار الصدر وأورام المنصف",
        "الإجراءات الصدرية وتدبير الطريق الهوائي"
    ]

    vascular_order = [
        "رضوض الشرايين والانسدادات الحادة",
        "التصلب العصيدي ونقص التروية المزمن",
        "تسلخ الأبهر وأمهات الدم الشريانية",
        "المتلازمات الوعائية والتهابات الشرايين",
        "أمراض الأوردة والأوعية اللمفية"
    ]

    reorder_subject("thoracic_surgery", thoracic_order)
    reorder_subject("vascular_surgery", vascular_order)

if __name__ == "__main__":
    main()
