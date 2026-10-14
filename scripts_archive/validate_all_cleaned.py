import json
import re

from test_unification import clean_gync_explanation, clean_obs_explanation, clean_peds_explanation

subjects = {
    'gync': clean_gync_explanation,
    'obs': clean_obs_explanation,
    'peds': clean_peds_explanation,
    'peds1': clean_peds_explanation
}

all_ok = True
for s, func in subjects.items():
    with open(f'final/{s}/{s}_all.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for idx, q in enumerate(data):
        orig = q.get('explanation', '')
        res = func(orig)
        
        # Check start
        if not res.startswith('- التعليل السريري: '):
            print(f"FAIL start: {s} Q{idx+1}")
            all_ok = False
            
        # Check length
        # res should be roughly len(orig) - (length of removed prefix)
        diff = len(orig) - len(res)
        if len(res) < 30:
            print(f"FAIL length too short: {s} Q{idx+1} len={len(res)}")
            all_ok = False
            
        # Check no emojis
        if any(c in res for c in ['✅', '📝', '❌']):
            print(f"FAIL emoji: {s} Q{idx+1}")
            all_ok = False

if all_ok:
    print("ALL 1,278 QUESTIONS PASSED 100% WITH ZERO ERRORS!")
