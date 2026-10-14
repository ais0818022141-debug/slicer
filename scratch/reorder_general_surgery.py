import sys
import csv
import shutil
from pathlib import Path
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
GS_DIR = BASE_DIR / "final" / "general_surgery"
CSV_PATH = GS_DIR / "general_surgery_all.csv"

def backup_file(p: Path):
    backup_dir = p.parent / ".backup"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    b_path = backup_dir / f"{p.stem}_prereorder_{ts}{p.suffix}"
    shutil.copyfile(p, b_path)
    print(f"[Backup] Created: {b_path.name}")
    return b_path

def reorder():
    backup_file(CSV_PATH)

    with open(CSV_PATH, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    print(f"Read {len(rows)} rows from CSV.")

    # Normalize 'أمراض المعدة والمعشري الجراحية' to 'أمراض المعدة والعفج الجراحية'
    renamed_count = 0
    for r in rows:
        if r.get('Chapter_or_Section') == 'أمراض المعدة والمعشري الجراحية':
            r['Chapter_or_Section'] = 'أمراض المعدة والعفج الجراحية'
            renamed_count += 1
    print(f"Renamed {renamed_count} questions to 'أمراض المعدة والعفج الجراحية'.")

    target_order = [
        "أمراض المري الجراحية",
        "أمراض المعدة والعفج الجراحية",
        "أمراض الأمعاء الدقيقة الجراحية",
        "أمراض الكولون والمستقيم الجراحية",
        "أمراض القناة الشرجية",
        "أمراض الكبد الجراحية",
        "أمراض الطرق الصفراوية والمرارة",
        "آفات البنكرياس الجراحية",
        "النزف الهضمي وآفات الطحال",
        "أمراض البريتوان والبطن الحاد",
        "الصدمة ورضوض البطن",
        "الفتوق وجدار البطن",
        "أمراض الثدي الجراحية",
        "الجراحة التنظيرية وجراحة البدانة والعناية حول الجراحية",
        "أورام الجلد والنسج الرخوة"
    ]

    # Group rows by topic
    topics_rows = {t: [] for t in target_order}
    other_rows = []

    for r in rows:
        t = r.get('Chapter_or_Section')
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
    print(f"Total reordered rows: {len(reordered_rows)} (original: {len(rows)})")
    assert len(reordered_rows) == len(rows), "Row count mismatch!"

    with open(CSV_PATH, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reordered_rows)

    print(f"[✓] Reordered CSV successfully written to {CSV_PATH.name}")

    # Remove old topic file if it exists
    old_topic_file = GS_DIR / "topics" / "general_surgery_all_أمراض_المعدة_والمعشري_الجراحية.html"
    if old_topic_file.exists():
        old_topic_file.unlink()
        print(f"[✓] Removed obsolete topic file: {old_topic_file.name}")

if __name__ == "__main__":
    reorder()
