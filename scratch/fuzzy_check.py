import sys
import csv
import difflib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def check_fuzzy(source_csv, target_csv):
    with open(target_csv, 'r', encoding='utf-8-sig') as f:
        target_rows = list(csv.DictReader(f))
    
    with open(source_csv, 'r', encoding='utf-8-sig') as f:
        source_rows = list(csv.reader(f))

    print(f"\nComparing {source_csv} ({len(source_rows)} items) against {target_csv} ({len(target_rows)} items):")
    
    for i, srow in enumerate(source_rows):
        s_id = srow[0]
        s_text = srow[4]
        best_ratio = 0
        best_match = None
        for trow in target_rows:
            ratio = difflib.SequenceMatcher(None, s_text, trow['Question_Text']).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = trow
        
        print(f"[{i+1}] {s_id}: '{s_text[:40]}...'")
        print(f"    Highest match ({best_ratio:.2f}): [{best_match['Question_ID']}] '{best_match['Question_Text'][:40]}...'")
        if best_ratio > 0.6:
            print("    *** POTENTIAL DUPLICATE ***")

check_fuzzy("working_on/أسئلة دورات أورام.csv", "final/onco/onco_all.csv")
check_fuzzy("working_on/أسئلة دورات تجميلية.csv", "final/plastic/plastic_all.csv")
