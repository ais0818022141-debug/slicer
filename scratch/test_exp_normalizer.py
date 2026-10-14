import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def normalize_explanation_text(text):
    if not text or not isinstance(text, str):
        return ""
    
    t = text.strip()
    
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
                
            opts_part = re.sub(r'(?:^|\s+|\n+)(?<![A-Za-z0-9])([A-F][:)])\s*', r'\n\n\1 ', opts_part).strip()
            opts_part = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', lambda m: m.group(1) + '\u200F.' + m.group(2), opts_part)
            
            parts[i] = sec_header
            parts[i+1] = opts_part + ('\n\n' + after_part.strip() if after_part else '')
        t = ''.join(parts).strip()
    else:
        opts_found = list(re.finditer(r'(?<![A-Za-z0-9])([A-F][:)])', t))
        if len(opts_found) > 1:
            t = re.sub(r'(?:^|\s+|\n+)(?<![A-Za-z0-9])([A-F][:)])\s*', r'\n\n\1 ', t).strip()
            t = re.sub(r'([A-Za-z0-9_-]{2,})\.([^\u200F]|$)', lambda m: m.group(1) + '\u200F.' + m.group(2), t)

    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

sample_onco_04 = """- التعليل السريري: تشتق الغدة الدرقية نسيجياً من مصدرين؛ الخلايا الجريبية المفرزة للهرمونات الدرقية (والتي ينشأ منها السرطان الحليمي والجريبي)، والخلايا المجاورة للجريب المسماة خلايا C المشتقة من العرف العصبي المسؤولة عن إفراز الكالسيتونين. وبما أن السرطان اللبي ورم عصبي صماوي ينشأ حصراً من خلايا C، فإن نشوءه على حساب الخلايا الجريبية أمر خاطئ تماماً (الخيار E).

- الخيارات الأخرى:
A) عبارة صحيحة؛ إنذاره أسوأ نسبياً من السرطانين الحليمي والجريبي (نظراً لميله للغزو الوعائي وعدم قبطه لليود المشع) ولكنه أفضل من اللامصنع؛ وبقيا 10 سنوات بين 70–90% بحسب المرحلة وترافقه مع MEN2B.

B) عبارة صحيحة؛ يترافق في 25% من الحالات مع أشكال عائلية وراثية كمتلازمتي MEN 2A و MEN 2B وطفرات RET.

C) عبارة صحيحة؛ يرتكز علاجه على الاستئصال التام للغدة مع تجريف العقد الرقبية المركزية ثنائي الجانب روتينياً (وتجريف عنق جذري عند وجود عقد رقبية مجسوسة أو إصابة العقد المركزية) بسبب الميل العالي للانتقال اللمفاوي.

D) عبارة صحيحة؛ يمثل ارتفاع مستوى كالسيتونين المصل الواسم التشخيصي والمتابعي النوعي له."""

sample_plastic_45 = """- التعليل السريري: الشفة السفلية أكثر تعرضاً لأشعة الشمس المباشرة من الشفة العليا بسبب زاوية سقوط الأشعة، ما يؤهب لتراكم الطفرات في الخلايا الشائكة للظهارة الحرشفية المبطنة للشفة فينشأ عنها SCC كأشيع نمط.
- الخيارات الأخرى: B) الميلانوما نادرة في الشفة مقارنة بـ SCC. C) BCC أشيع في الشفة العليا والوجه لكنه أقل شيوعاً من SCC في الشفة السفلية تحديداً. D) داء بوفن سرطان شائك خلايا موضع داخل البشرة، نادر نسبياً كشكل سريري."""

print("=== Normalized onco 04 ===")
print(normalize_explanation_text(sample_onco_04))

print("\n=== Normalized plastic 45 ===")
print(normalize_explanation_text(sample_plastic_45))
