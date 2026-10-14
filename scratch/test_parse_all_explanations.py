import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

exp_path = Path("working_on") / "explanations.txt"
with open(exp_path, 'r', encoding='utf-8') as f:
    text = f.read()

def clean_and_format_exp(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    
    # 1. Preserve CLINICAL ERROR FLAG as a highlighted clinical note
    text = re.sub(
        r'(?:^|\n)\s*\(?\s*CLINICAL\s+ERROR\s+FLAG\s*[:：]?\s*(.*?)(?=\n---|\Z)',
        r'\n\n- ملاحظة سريرية (Clinical Error Flag): \1',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # 2. Standardize section headers with bullet dashes
    text = re.sub(r'^[ \t]*[*•-]?\s*(التعليل\s+السريري|التعليل|الشرح)\s*[:：]', r'- \1:', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*[*•-]?\s*(الخيارات\s+الأخرى|تفنيد\s+الخيارات)\s*[:：]', r'- \1:', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*[*•-]?\s*(ترميم\s+امتحاني|الترميم\s+الشامل)\s*[:：]', r'- \1:', text, flags=re.MULTILINE)
    
    # 3. Standardize distractor option bullets '* A:' or '* A)' or '* A: ' or 'A:' to 'A) '
    text = re.sub(r'^[ \t]*[*•-]?\s*([A-F])\s*[:）)]\s*', r'\1) ', text, flags=re.MULTILINE)
    
    # 4. Collapse excessive blank lines
    lines = [l.strip() for l in text.splitlines()]
    clean_lines = []
    for l in lines:
        if l:
            clean_lines.append(l)
        elif clean_lines and clean_lines[-1] != '':
            clean_lines.append('')
            
    return '\n'.join(clean_lines).strip()

def parse_all_blocks(text):
    # Split by delimiter '---' or header '#...'
    raw_blocks = re.split(r'\n(?=\s*#\s*\d+)', text)
    parsed = {}
    
    for b in raw_blocks:
        b = b.strip()
        if not b:
            continue
        
        # Match header like #01 or #1
        m_head = re.match(r'^#\s*(\d+)', b)
        if not m_head:
            continue
        num = int(m_head.group(1))
        
        # 1. Educational Objective
        obj_m = re.search(
            r'(?:EDUCATIONAL\s+OBJECTIVE|الهدف\s+التعليمي)\s*:\s*(.*?)(?=(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية|EXPLANATION|الشرح|التعليل)\s*:|$)',
            b, re.DOTALL | re.IGNORECASE
        )
        
        # 2. High Yield Note
        note_m = re.search(
            r'(?:HIGH\s+YIELD\s+NOTE|ملاحظة\s+عالية\s+الأهمية)\s*:\s*(.*?)(?=(?:EXPLANATION|الشرح|التعليل)\s*:|$)',
            b, re.DOTALL | re.IGNORECASE
        )
        
        # 3. Explanation: everything after EXPLANATION: up to '---' or end of block
        exp_m = re.search(
            r'(?:EXPLANATION|الشرح|التعليل\s+السريري|التعليل)\s*:\s*(.*?)(?=(?:\n\s*---\s*|\Z))',
            b, re.DOTALL | re.IGNORECASE
        )
        
        obj = obj_m.group(1).strip() if obj_m else ""
        note = note_m.group(1).strip() if note_m else ""
        raw_exp = exp_m.group(1).strip() if exp_m else ""
        clean_exp = clean_and_format_exp(raw_exp)
        
        parsed[num] = {
            "num": num,
            "educational_objective": obj,
            "high_yield_note": note,
            "explanation": clean_exp,
            "raw_exp": raw_exp
        }
    return parsed

parsed = parse_all_blocks(text)
print(f"Total parsed questions: {len(parsed)}")

missing_obj = [n for n, d in parsed.items() if not d['educational_objective']]
missing_note = [n for n, d in parsed.items() if not d['high_yield_note']]
missing_exp = [n for n, d in parsed.items() if not d['explanation']]

print(f"Questions missing Objective: {missing_obj}")
print(f"Questions missing Note: {missing_note}")
print(f"Questions missing Explanation: {missing_exp}")

# Check sample block 1
print("\n--- Parsed Block 1 ---")
print("OBJECTIVE:", parsed[1]['educational_objective'])
print("NOTE:", parsed[1]['high_yield_note'])
print("EXPLANATION:\n", parsed[1]['explanation'][:300])

# Check sample block 21 (has flag)
print("\n--- Parsed Block 21 (With Flag) ---")
print("OBJECTIVE:", parsed[21]['educational_objective'])
print("NOTE:", parsed[21]['high_yield_note'])
print("EXPLANATION:\n", parsed[21]['explanation'])
