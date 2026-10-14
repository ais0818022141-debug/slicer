# -*- coding: utf-8 -*-
import csv
import re
import sys

def normalize_explanation_text(text):
    if not text or not isinstance(text, str):
        return ""
    
    t = text.strip()
    
    # 1. Standardize section headers:
    # ensure they are on their own lines with "- Header:"
    headers = [
        'التعليل السريري', 'التعليل', 'الشرح',
        'الخيارات الأخرى', 'تفنيد الخيارات',
        'ترميم امتحاني', 'الترميم الشامل',
        'ملاحظة سريرية', 'ملاحظة'
    ]
    for hdr in headers:
        t = re.sub(
            rf'(?:\n\s*)*\s*(?:-\s*)?({hdr})\s*[:：]\s*',
            rf'\n\n- \1:\n',
            t
        )
    t = t.strip()
    
    # 2. In "الخيارات الأخرى" or "تفنيد الخيارات", ensure each option [A-F]) is on a new paragraph
    parts = re.split(r'(\n\n-\s*(?:الخيارات\s+الأخرى|تفنيد\s+الخيارات)\s*[:：]\s*\n)', t)
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            sec_header = parts[i]
            sec_body = parts[i+1] if i+1 < len(parts) else ""
            
            # Find if there is another section following this
            next_sec_m = re.search(r'\n\n-\s*[\u0600-\u06FF]', sec_body)
            if next_sec_m:
                opts_part = sec_body[:next_sec_m.start()]
                after_part = sec_body[next_sec_m.start():]
            else:
                opts_part = sec_body
                after_part = ""
                
            # Place each option A), B), etc. on its own paragraph
            # We match A) or A: only if preceded by start or space or newline and not part of an English word
            opts_part = re.sub(r'(?:^|\s+|\n+)(?<![A-Za-z0-9])([A-F][:)])\s*', r'\n\n\1 ', opts_part).strip()
            
            # Prevent Bidi flip when English acronym precedes a period:
            # If an English word (e.g. MEN2B or RET) is followed by a period, insert \u200F before the period or after it
            # Placing \u200F directly after the period (e.g. "MEN2B.\u200F") anchors the neutral period in RTL
            opts_part = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', lambda m: m.group(1) + '.\u200F' + m.group(2), opts_part)
            
            parts[i] = sec_header
            parts[i+1] = opts_part + ('\n\n' + after_part.strip() if after_part else '')
        t = ''.join(parts).strip()
    else:
        # Check if there are option letters A), B), C) in general
        opts_found = list(re.finditer(r'(?<![A-Za-z0-9])([A-F][:)])', t))
        if len(opts_found) > 1:
            t = re.sub(r'(?:^|\s+|\n+)(?<![A-Za-z0-9])([A-F][:)])\s*', r'\n\n\1 ', t).strip()
            t = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', lambda m: m.group(1) + '.\u200F' + m.group(2), t)

    # Clean excessive newlines
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

def strip_formatting(s):
    # Strip whitespace, headers markers, dashes, newlines, RLM to verify raw text preservation
    s = s.replace('\u200F', '').replace('\u200E', '')
    s = re.sub(r'[-\s:：\n\r]+', '', s)
    return s

# Test on all questions in onco, plastic, ped_surgery
subjects = ['onco', 'plastic', 'ped_surgery']
total_tested = 0
all_passed = True

for s in subjects:
    csv_file = f'final/{s}/{s}_all.csv'
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            qid = r.get('Question_ID') or r.get('\ufeffQuestion_ID')
            orig_exp = r.get('Explanation', '')
            if not orig_exp:
                continue
            norm_exp = normalize_explanation_text(orig_exp)
            
            # Verify that all substantive words/characters are 100% preserved
            raw_orig = strip_formatting(orig_exp)
            raw_norm = strip_formatting(norm_exp)
            if raw_orig != raw_norm:
                print(f"[FAIL] Content mismatch in {qid}!")
                print("ORIG:", raw_orig[:100])
                print("NORM:", raw_norm[:100])
                all_passed = False
            total_tested += 1

print(f"Tested {total_tested} explanations across {subjects}.")
if all_passed:
    print("[PASS] 100% of scientific text preserved! Zero loss, zero corruption.")
else:
    print("[FAIL] Some text differences found!")
