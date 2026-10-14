import json
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

final_dir = Path('final')
subjects = [
    ('thoracic_surgery', 'الجراحة الصدرية', 73),
    ('cardiac_surgery', 'الجراحة القلبية', 39),
    ('vascular_surgery', 'جراحة الأوعية', 55)
]

for slug, name, expected_cnt in subjects:
    s_dir = final_dir / slug
    print(f"Checking {slug} ({name})...")
    assert s_dir.exists(), f"{slug} does not exist"
    
    # check files
    for ext in ['all.json', 'all.csv', 'all_ai.md', 'all_ai_temp.md', 'all.html', 'all_topics.html', 'all_sessions.html']:
        fname = f"{slug}_{ext}"
        fpath = s_dir / fname
        assert fpath.exists(), f"{fname} missing"
    assert (s_dir / 'explanations.txt').exists(), "explanations.txt missing"
    assert (s_dir / 'topics').exists(), "topics folder missing"
    assert (s_dir / 'sessions').exists(), "sessions folder missing"
    assert (s_dir / 'years').exists(), "years folder missing"
    
    # Check JSON
    with open(s_dir / f"{slug}_all.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert len(data) == expected_cnt, f"Count mismatch: {len(data)} != {expected_cnt}"
    
    for i, q in enumerate(data, start=1):
        expected_id = f"q_{slug}_{i:02d}"
        actual_id = q.get('id')
        assert actual_id == expected_id, f"ID mismatch: {actual_id} != {expected_id}"
        assert q.get('subject_name') == name, f"Subject mismatch: {q.get('subject_name')}"
        assert len(q.get('options', [])) >= 4, f"Options too few in {actual_id}"
        assert any(opt.get('is_correct') for opt in q.get('options', [])), f"No correct option in {actual_id}"
        assert len(q.get('educational_objective', '')) > 5, f"Missing objective in {actual_id}"
        assert len(q.get('high_yield_note', '')) > 5, f"Missing note in {actual_id}"
        exp = q.get('explanation', '')
        assert '- التعليل السريري:' in exp, f"Missing التعليل السريري in {actual_id}"
        assert '- الخيارات الأخرى:' in exp, f"Missing الخيارات الأخرى in {actual_id}"

    # Check CSV
    import pandas as pd
    df = pd.read_csv(s_dir / f"{slug}_all.csv", encoding='utf-8-sig')
    assert len(df) == expected_cnt, f"CSV row count mismatch: {len(df)} != {expected_cnt}"
    assert not df['Explanation'].isna().any(), f"Empty explanations in CSV for {slug}"
    assert not df['High_Yield_Note'].isna().any(), f"Empty notes in CSV for {slug}"

    print(f"[✓] {slug}: {expected_cnt} questions verified with 100% data integrity!")

print("\nAll 3 subjects verified with 100% integrity!")

with open(final_dir / 'manifest.json', 'r', encoding='utf-8') as f:
    manifest = json.load(f)

print(f"Manifest subjects count: {manifest.get('subjects_count')}")
print(f"Manifest total questions: {manifest.get('total_questions')}")
for slug in ['thoracic_surgery', 'cardiac_surgery', 'vascular_surgery']:
    entry = manifest['subjects'][slug]
    print(f" - {slug}: {entry['subject_name']} | {entry['questions_count']} questions | {len(entry['topics'])} topics")
