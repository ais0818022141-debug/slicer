import re
import html
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

test_exp = """- التعليل السريري: تشتق الغدة الدرقية نسيجياً من مصدرين؛ الخلايا الجريبية المفرزة للهرمونات الدرقية (والتي ينشأ منها السرطان الحليمي والجريبي)، والخلايا المجاورة للجريب المسماة خلايا C المشتقة من العرف العصبي المسؤولة عن إفراز الكالسيتونين. وبما أن السرطان اللبي ورم عصبي صماوي ينشأ حصراً من خلايا C، فإن نشوءه على حساب الخلايا الجريبية أمر خاطئ تماماً (الخيار E).

- الخيارات الأخرى:
A) عبارة صحيحة؛ إنذاره أسوأ نسبياً من السرطانين الحليمي والجريبي (نظراً لميله للغزو الوعائي وعدم قبطه لليود المشع) ولكنه أفضل من اللامصنع؛ وبقيا 10 سنوات بين 70–90% بحسب المرحلة وترافقه مع MEN2B.

B) عبارة صحيحة؛ يترافق في 25% من الحالات مع أشكال عائلية وراثية كمتلازمتي MEN 2A و MEN 2B وطفرات RET.

C) عبارة صحيحة؛ يرتكز علاجه على الاستئصال التام للغدة مع تجريف العقد الرقبية المركزية ثنائي الجانب روتينياً (وتجريف عنق جذري عند وجود عقد رقبية مجسوسة أو إصابة العقد المركزية) بسبب الميل العالي للانتقال اللمفاوي.

D) عبارة صحيحة؛ يمثل ارتفاع مستوى كالسيتونين المصل الواسم التشخيصي والمتابعي النوعي له."""

def format_explanation_test(raw_exp):
    clean_exp = raw_exp.strip()
    
    # Define section patterns
    section_patterns = [
        (r'(?:-\s*)?(التعليل\s+السريري|التعليل|الشرح)\s*[:：]', 'exp-clinical', r'\1:'),
        (r'(?:-\s*)?(الخيارات\s+الأخرى|تفنيد\s+الخيارات)\s*[:：]', 'exp-other-opts', r'\1:'),
        (r'(?:-\s*)?(ترميم\s+امتحاني|الترميم\s+الشامل)\s*[:：]', 'exp-tarmim', r'\1:'),
        (r'(?:-\s*)?(ملاحظة\s+سريرية\s*\(Clinical\s+Error\s+Flag\)|CLINICAL\s+ERROR\s+FLAG)\s*[:：]', 'exp-flag', r'\1:'),
        (r'(?:-\s*)?(ملاحظة\s+\w+|ملاحظة)\s*[:：]', 'exp-note', r'\1:')
    ]
    
    headers = []
    for pat, cls, label in section_patterns:
        for m in re.finditer(pat, clean_exp):
            headers.append((m.start(), m.end(), cls, m.group(1) + ':'))
            
    headers.sort(key=lambda x: x[0])
    
    sections = []
    if not headers:
        sections.append(('exp-general', '', clean_exp))
    else:
        if headers[0][0] > 0:
            pre_txt = clean_exp[:headers[0][0]].strip()
            if pre_txt:
                sections.append(('exp-general', '', pre_txt))
        for i in range(len(headers)):
            start_content = headers[i][1]
            end_content = headers[i+1][0] if i + 1 < len(headers) else len(clean_exp)
            sec_cls = headers[i][2]
            sec_header = headers[i][3]
            sec_text = clean_exp[start_content:end_content].strip()
            sections.append((sec_cls, sec_header, sec_text))
            
    html_parts = []
    for cls, hdr, body in sections:
        part = f'<div class="exp-section {cls}">'
        if hdr:
            part += f'<b class="exp-header-tag">{html.escape(hdr)}</b> '
            
        # Only parse option items if in 'exp-other-opts' or body has option list items
        if cls == 'exp-other-opts' or re.search(r'(?:^|\n)\s*[A-F][:)ـ]', body):
            opt_matches = list(re.finditer(r'(?:(?<=\n)|^|(?<=\s))([A-F][:)])\s*', body))
            if opt_matches:
                pre_opt_text = body[:opt_matches[0].start()].strip()
                if pre_opt_text:
                    part += f'<div class="exp-lead">{html.escape(pre_opt_text)}</div>'
                    
                for idx in range(len(opt_matches)):
                    opt_tag = opt_matches[idx].group(1)
                    opt_start = opt_matches[idx].end()
                    opt_end = opt_matches[idx+1].start() if idx + 1 < len(opt_matches) else len(body)
                    opt_txt = body[opt_start:opt_end].strip()
                    
                    escaped_txt = html.escape(opt_txt)
                    part += f'<div class="exp-opt-item"><bdi class="opt-letter-tag">{html.escape(opt_tag)}</bdi> <span class="exp-opt-desc">{escaped_txt}</span></div>'
            else:
                part += html.escape(body)
        else:
            # Clinical or other section: highlight inline references like (الخيار E)
            escaped_body = html.escape(body)
            # Highlight (الخيار X) or الخيار X
            escaped_body = re.sub(
                r'(\(الخيار\s+[A-F]\)|الخيار\s+[A-F])',
                r'<bdi class="opt-ref-tag">\1</bdi>',
                escaped_body
            )
            # Handle paragraphs
            paras = [p.strip() for p in re.split(r'\n\s*\n', escaped_body) if p.strip()]
            if len(paras) > 1:
                part += ''.join(f'<div class="exp-para">{p}</div>' for p in paras)
            else:
                part += escaped_body
                
        part += '</div>'
        html_parts.append(part)
        
    return '\n'.join(html_parts)

result = format_explanation_test(test_exp)
print(result)
