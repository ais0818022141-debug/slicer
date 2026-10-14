import json
import re

subjects = ['cardio', 'endo', 'gastro', 'renal', 'hema', 'rheuma', 'gync', 'obs', 'peds', 'peds1']

stats = {}

for s in subjects:
    p = f'final/{s}/{s}_all.json'
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total = len(data)
    starts_with_clinical = 0
    has_correct_ans_phrase = 0
    has_sharh = 0
    has_tafneed = 0
    has_emojis = 0
    has_outer_parens = 0

    for q in data:
        exp = q.get('explanation', '').strip()
        if exp.startswith('- التعليل السريري:') or exp.startswith('- التعليل السريري'):
            starts_with_clinical += 1
        if 'الإجابة الصحيحة' in exp or 'الاجابة الصحيحة' in exp:
            has_correct_ans_phrase += 1
        if 'الشرح:' in exp or 'الشرح :' in exp:
            has_sharh += 1
        if 'تفنيد الخيارات' in exp:
            has_tafneed += 1
        if any(c in exp for c in ['✅', '📝', '❌', '💡']):
            has_emojis += 1
        if exp.startswith('(') and exp.endswith(')'):
            has_outer_parens += 1

    stats[s] = {
        'total': total,
        'starts_clinical': starts_with_clinical,
        'has_correct_ans': has_correct_ans_phrase,
        'has_sharh': has_sharh,
        'has_tafneed': has_tafneed,
        'has_emojis': has_emojis,
        'has_outer_parens': has_outer_parens
    }

print(json.dumps(stats, indent=2, ensure_ascii=False))
