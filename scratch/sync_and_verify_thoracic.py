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
    b_path = backup_dir / f"{p.stem}_before_sync_{ts}{p.suffix}"
    shutil.copyfile(p, b_path)
    print(f"[Backup] Created: {b_path.name}")
    return b_path

def reorder_thoracic():
    thoracic_order = [
        "رضوض الصدر والأذيات الإسعافية",
        "أمراض وجراحة الجنب",
        "سرطان الرئة والنقائل الورمية",
        "الآفات الرئوية الإنتانية والخمجية",
        "تشوهات جدار الصدر وأورام المنصف",
        "الإجراءات الصدرية وتدبير الطريق الهوائي"
    ]
    
    csv_path = FINAL_DIR / "thoracic_surgery" / "thoracic_surgery_all.csv"
    backup_file(csv_path)

    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = [c.lstrip('\ufeff') for c in reader.fieldnames]
        rows = list(reader)

    cleaned_rows = []
    for r in rows:
        cleaned_rows.append({(k.lstrip('\ufeff') if isinstance(k, str) else k): v for k, v in r.items()})
    rows = cleaned_rows

    topics_rows = {t: [] for t in thoracic_order}
    other_rows = []

    for r in rows:
        t = (r.get('Chapter_or_Section') or '').strip()
        if t in topics_rows:
            topics_rows[t].append(r)
        else:
            other_rows.append(r)

    reordered_rows = []
    for idx, t in enumerate(thoracic_order, 1):
        qs = topics_rows[t]
        print(f"  {idx:02d}. {t}: {len(qs)} questions")
        reordered_rows.extend(qs)

    reordered_rows.extend(other_rows)
    assert len(reordered_rows) == len(rows), "Row count mismatch in thoracic!"

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reordered_rows)

    print(f"[✓] Reordered thoracic_surgery_all.csv according to requested topic order.")

if __name__ == "__main__":
    reorder_thoracic()
