import json
import re

def clean_gync_explanation(exp):
    raw = exp.strip()
    # Strip wrapping parentheses
    # Sometimes it is: (الإجابة الصحيحة: ... text) or (الإجابة الصحيحة: ... text).
    if raw.startswith('('):
        if raw.endswith(')'):
            raw = raw[1:-1].strip()
        elif raw.endswith(').'):
            raw = raw[1:-2].strip() + '.'
        elif raw.endswith(')'):
            raw = raw[1:-1].strip()
        else:
            # Check if matching ')' is at the very end
            raw = re.sub(r'^\(\s*', '', raw)
            raw = re.sub(r'\s*\)$', '', raw)

    # Strip leading 'الإجابة الصحيحة: X الشرح:'
    # Regex handles variations like:
    # الإجابة الصحيحة: E الشرح:
    # الإجابة الصحيحة: A
    # الإجابة الصحيحة: D:
    raw = re.sub(r'^(?:الإجابة الصحيحة|الاجابة الصحيحة)\s*:\s*[A-Ea-e]?\s*[:\-\.]?\s*(?:الشرح\s*:\s*)?', '', raw).strip()
    
    # Prepend standard clinical header
    return f"- التعليل السريري: {raw}"


def clean_obs_explanation(exp):
    raw = exp.strip()
    # Remove emojis
    raw = raw.replace('✅', '').replace('📝', '').strip()
    
    # Split into lines
    lines = [l.strip() for l in raw.split('\n') if l.strip()]
    if not lines:
        return ""
    
    first_line = lines[0]
    # Strip leading 'الإجابة الصحيحة: X (text) الشرح:'
    cleaned_first = re.sub(
        r'^(?:الإجابة الصحيحة|الاجابة الصحيحة)\s*:\s*[A-Ea-e]?\s*(?:\([^)]*\))?\s*[:\-\.]?\s*(?:الشرح\s*:\s*)?',
        '',
        first_line
    ).strip()
    
    result_lines = [f"- التعليل السريري: {cleaned_first}"]
    
    # If there are subsequent lines (option refutations, notes)
    if len(lines) > 1:
        other_lines = lines[1:]
        # Check if first subsequent line already has header
        has_options_header = False
        formatted_subsequent = []
        for l in other_lines:
            l = l.replace('✅', '').replace('📝', '').strip()
            if not l:
                continue
            if l.startswith('ملاحظة:'):
                formatted_subsequent.append(f"- {l}")
            elif l.startswith('- '):
                formatted_subsequent.append(l)
            else:
                formatted_subsequent.append(l)
        
        # In TealMed older format, options refutation starts with '- الخيارات الأخرى: '
        # Join options with ' - ' or list them
        # Let's combine them neatly under '- الخيارات الأخرى: '
        joined_options = []
        notes = []
        for l in formatted_subsequent:
            if l.startswith('- ملاحظة:'):
                notes.append(l)
            else:
                joined_options.append(l)
        
        if joined_options:
            result_lines.append(f"- الخيارات الأخرى: {' - '.join(joined_options)}")
        for n in notes:
            result_lines.append(n)
            
    return "\n".join(result_lines)


def clean_peds_explanation(exp):
    raw = exp.strip()
    # Strip leading 'الإجابة الصحيحة: "A" (text).الشرح:' or 'الإجابة الصحيحة: "D" (text) الشرح:'
    cleaned = re.sub(
        r'^(?:الإجابة الصحيحة|الاجابة الصحيحة)\s*:\s*["\']?[A-Ea-e]["\']?\s*(?:\([^)]*\))?\s*[:\-\.]?\s*(?:الشرح\s*:\s*)?',
        '',
        raw
    ).strip()
    
    # Now check for 'تفنيد الخيارات:' and 'ترميم امتحاني:'
    # We want:
    # - التعليل السريري: <explanation>
    # - الخيارات الأخرى: <tafneed>
    # - ترميم امتحاني: <tarmim> (if present)
    
    # Split by تفنيد الخيارات:
    if 'تفنيد الخيارات:' in cleaned:
        parts = cleaned.split('تفنيد الخيارات:', 1)
        clinical = parts[0].strip()
        rest = parts[1].strip()
        
        if 'ترميم امتحاني:' in rest:
            rest_parts = rest.split('ترميم امتحاني:', 1)
            options = rest_parts[0].strip()
            tarmim = rest_parts[1].strip()
            
            res = f"- التعليل السريري: {clinical}\n- الخيارات الأخرى: {options}"
            if tarmim:
                res += f"\n- ترميم امتحاني: {tarmim}"
            return res
        else:
            return f"- التعليل السريري: {clinical}\n- الخيارات الأخرى: {rest}"
    elif 'ترميم امتحاني:' in cleaned:
        parts = cleaned.split('ترميم امتحاني:', 1)
        clinical = parts[0].strip()
        tarmim = parts[1].strip()
        return f"- التعليل السريري: {clinical}\n- ترميم امتحاني: {tarmim}"
    else:
        return f"- التعليل السريري: {cleaned}"


# Test on all 4 subjects
subjects = {
    'gync': clean_gync_explanation,
    'obs': clean_obs_explanation,
    'peds': clean_peds_explanation,
    'peds1': clean_peds_explanation
}

out_samples = []

for s, func in subjects.items():
    p = f'final/{s}/{s}_all.json'
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    out_samples.append(f"==================== {s.upper()} ({len(data)} questions) ====================")
    errors = 0
    for idx, q in enumerate(data):
        orig = q.get('explanation', '')
        res = func(orig)
        
        # Sanity checks
        if not res.startswith('- التعليل السريري: '):
            print(f"ERROR: {s} Q{idx+1} does not start with clinical header: {repr(res[:60])}")
            errors += 1
        if any(c in res for c in ['✅', '📝']):
            print(f"ERROR: {s} Q{idx+1} contains emojis: {repr(res[:60])}")
            errors += 1
        if len(res) < 25:
            print(f"WARNING: {s} Q{idx+1} suspiciously short: {repr(res)}")
            errors += 1
            
        if idx < 3:
            out_samples.append(f"--- Q{idx+1} ---")
            out_samples.append(f"BEFORE: {orig[:180]}")
            out_samples.append(f"AFTER:\n{res[:350]}\n")
            
    print(f"{s}: Processed {len(data)} questions. Errors found: {errors}")

with open('scratch_clean_test_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_samples))

print("Results written to scratch_clean_test_results.txt")
