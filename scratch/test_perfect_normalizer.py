# -*- coding: utf-8 -*-
import re
import csv

def normalize_explanation_text(text):
    if not text or not isinstance(text, str):
        return ""
    
    t = text.strip()
    
    # 0. Heal accidental splits like "(خلايا \n\n C)"
    t = re.sub(r'\(خلايا\s*\n*\s*C\)\s*', '(خلايا C) ', t)
    
    # 1. Standardize section headers on dedicated lines
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
    
    # 2. In options sections, separate options [A-F][.)] onto distinct paragraphs
    parts = re.split(r'(\n\n-\s*(?:الخيارات\s+الأخرى|تفنيد\s+الخيارات)\s*[:：]\s*\n)', t)
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            sec_header = parts[i]
            sec_body = parts[i+1] if i+1 < len(parts) else ""
            next_sec_m = re.search(r'\n\n-\s*[\u0600-\u06FF]', sec_body)
            if next_sec_m:
                opts_part = sec_body[:next_sec_m.start()]
                after_part = sec_body[next_sec_m.start():]
            else:
                opts_part = sec_body
                after_part = ""
                
            # Only match options at start of line or preceded by sentence endings (. ; ؛ !)
            # and NOT preceded by opening parenthesis '('
            opts_part = re.sub(r'(?:(?<=[\n.؛;!])|^)\s*(?<!\()([A-F])[:.)]\s*', r'\n\n\1) ', opts_part).strip()
            # Protect trailing English acronyms with \u200F
            opts_part = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', lambda m: m.group(1) + '.\u200F' + m.group(2), opts_part)
            
            parts[i] = sec_header
            parts[i+1] = opts_part + ('\n\n' + after_part.strip() if after_part else '')
        t = ''.join(parts).strip()
    else:
        # Check if there are options in general
        opts_found = list(re.finditer(r'(?:(?<=[\n.؛;!])|^)\s*(?<!\()([A-F])[:.)]\s*', t))
        if len(opts_found) > 1:
            t = re.sub(r'(?:(?<=[\n.؛;!])|^)\s*(?<!\()([A-F])[:.)]\s*', r'\n\n\1) ', t).strip()
            t = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', lambda m: m.group(1) + '.\u200F' + m.group(2), t)

    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

# Test on q_onco_02
q_onco_02_sample = """- التعليل السريري:
هناك خطأ في السؤال فالخيارات الخمسة المطروحة جميعها عبارات علمية صحيحة  (حيث إن السرطان اللامصنع سيء الإنذار بالفعل). ورد السؤال قبل ذلك وتم وضع خيار يتعلق بآلية انتشار السرطان الجريبي. يتميز السرطان اللامصنع بغياب التمايز الخلوي ونموه الارتشاحي السريع والمدمر للبنى المجاورة، ومقاومته لليود المشع والعلاجات التقليدية؛ مما يجعل إنذاره سيئاً للغاية ومعدل بقيا المرضى لا يتجاوز بضعة أشهر.

- الخيارات الأخرى:
A) عبارة صحيحة؛ يشكل التهاب درق هاشيموتو المناعي بيئة ليمفاوية مزمنة تؤهب لنشوء لمفوما الدرق تائية أو بائية الخلايا.

B) عبارة صحيحة؛ يمثل السرطان الحليمي نحو 80% من سرطانات الدرق وهو الأشيع مطلقاً.

C) عبارة صحيحة؛ ينشأ الورم اللبي من الخلايا المجاورة للجريب (خلايا

C) ويفرز الكالسيتونين نوعياً.

D) عبارة صحيحة؛ يميل السرطان الحليمي بشكل نموذجي للانتشار الباكر عبر الأوعية اللمفاوية إلى عقد العنق."""

norm = normalize_explanation_text(q_onco_02_sample)
print("=== Normalized q_onco_02 ===")
print(norm)
