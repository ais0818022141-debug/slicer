import json
import re
from pathlib import Path
import pandas as pd


def clean_gync_explanation(exp):
    raw = exp.strip()
    raw = re.sub(r'^-\s*التعليل\s+السريري\s*:\s*', '', raw).strip()
    if raw.startswith('('):
        if raw.endswith(')'):
            raw = raw[1:-1].strip()
        elif raw.endswith(').'):
            raw = raw[1:-2].strip() + '.'
        else:
            raw = re.sub(r'^\(\s*', '', raw)
            raw = re.sub(r'\s*\)$', '', raw)

    # If it's not row 208 (which is the medical sentence "العبارة تمثل الإجابة الصحيحة لأن...")
    raw = re.sub(
        r'^(?:✅|📝)?\s*(?:الإجابة\s+الصحيحة|الاجابة\s+الصحيحة)\s*:\s*.*?(?:📝)?\s*(?:الشرح\s*:\s*)',
        '',
        raw,
        flags=re.DOTALL
    ).strip()
    
    return f"- التعليل السريري: {raw}"


def clean_obs_explanation(exp):
    raw = exp.strip().replace('✅', '').replace('📝', '').strip()
    raw = re.sub(r'^-\s*التعليل\s+السريري\s*:\s*', '', raw).strip()
    lines = [l.strip() for l in raw.split('\n') if l.strip()]
    if not lines:
        return ""
    
    first_line = lines[0]
    cleaned_first = re.sub(
        r'^(?:✅|📝)?\s*(?:الإجابة\s+الصحيحة|الاجابة\s+الصحيحة)\s*:\s*.*?(?:📝)?\s*(?:الشرح\s*:\s*)',
        '',
        first_line,
        flags=re.DOTALL
    ).strip()
    
    result_lines = [f"- التعليل السريري: {cleaned_first}"]
    
    if len(lines) > 1:
        other_lines = lines[1:]
        joined_options = []
        notes = []
        for l in other_lines:
            l = l.replace('✅', '').replace('📝', '').strip()
            if not l:
                continue
            if l.startswith('- ملاحظة:') or l.startswith('ملاحظة:'):
                clean_n = re.sub(r'^(?:-\s*)?ملاحظة\s*:\s*', '', l).strip()
                notes.append(f"- ملاحظة: {clean_n}")
            elif l.startswith('- الخيارات الأخرى:'):
                clean_opt = re.sub(r'^-\s*الخيارات\s+الأخرى\s*:\s*', '', l).strip()
                joined_options.append(clean_opt)
            else:
                clean_opt = re.sub(r'^-\s*', '', l).strip()
                joined_options.append(clean_opt)
        
        if joined_options:
            result_lines.append(f"- الخيارات الأخرى: {' - '.join(joined_options)}")
        for n in notes:
            result_lines.append(n)
            
    return "\n".join(result_lines)


def clean_peds_explanation(exp):
    raw = exp.strip()
    raw = re.sub(r'^-\s*التعليل\s+السريري\s*:\s*', '', raw).strip()
    if raw.startswith('('):
        raw = raw[1:].strip()
        
    cleaned = re.sub(
        r'^(?:✅|📝)?\s*(?:الإجابة\s+الصحيحة|الاجابة\s+الصحيحة)\s*:\s*.*?(?:📝)?\s*(?:الشرح\s*:\s*)',
        '',
        raw,
        flags=re.DOTALL
    ).strip()
    
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
    elif '- الخيارات الأخرى:' in cleaned:
        # If it was already processed, preserve the split
        parts = cleaned.split('- الخيارات الأخرى:', 1)
        clinical = parts[0].strip()
        rest = parts[1].strip()
        if '- ترميم امتحاني:' in rest:
            r_parts = rest.split('- ترميم امتحاني:', 1)
            return f"- التعليل السريري: {clinical}\n- الخيارات الأخرى: {r_parts[0].strip()}\n- ترميم امتحاني: {r_parts[1].strip()}"
        else:
            return f"- التعليل السريري: {clinical}\n- الخيارات الأخرى: {rest}"
    elif 'ترميم امتحاني:' in cleaned:
        parts = cleaned.split('ترميم امتحاني:', 1)
        clinical = parts[0].strip()
        tarmim = parts[1].strip()
        return f"- التعليل السريري: {clinical}\n- ترميم امتحاني: {tarmim}"
    else:
        return f"- التعليل السريري: {cleaned}"


def json_to_csv_dataframe(questions):
    rows = []
    for q in questions:
        options = q.get('options', [])
        correct_opt = q.get('correct_option', '')
        
        correct_text = ''
        wrong_texts = []
        for opt in options:
            let = opt.get('letter', '')
            txt = opt.get('text', '')
            if let == correct_opt or opt.get('is_correct', False):
                correct_text = txt
            else:
                wrong_texts.append(txt)
                
        while len(wrong_texts) < 5:
            wrong_texts.append('')
            
        rows.append({
            'Question_ID': q.get('id', ''),
            'Medical_Subject': q.get('subject_name', ''),
            'Exam_Date': q.get('exam_period', ''),
            'Chapter_or_Section': q.get('topic_name', ''),
            'Question_Text': q.get('title', ''),
            'Explanation': q.get('explanation', ''),
            'High_Yield_Note': q.get('high_yield_note', ''),
            'Correct_Answer': correct_text,
            'Wrong_Answer_1': wrong_texts[0],
            'Wrong_Answer_2': wrong_texts[1],
            'Wrong_Answer_3': wrong_texts[2],
            'Wrong_Answer_4': wrong_texts[3],
            'Wrong_Answer_5': wrong_texts[4]
        })
    return pd.DataFrame(rows)


def main():
    print("=== UNIFYING ALL EXPLANATIONS TO CLINICAL STANDARD ===")
    
    cleaners = {
        'gync': clean_gync_explanation,
        'obs': clean_obs_explanation,
        'peds': clean_peds_explanation,
        'peds1': clean_peds_explanation
    }
    
    for sub, func in cleaners.items():
        json_path = Path(f'final/{sub}/{sub}_all.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"[*] Processing {sub} ({len(data)} questions)...")
        for q in data:
            orig = q.get('explanation', '')
            q['explanation'] = func(orig)
            
        # Write updated JSON to final/
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        # Write updated CSV to final/
        csv_path = Path(f'final/{sub}/{sub}_all.csv')
        df = json_to_csv_dataframe(data)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # Mirror to all_{sub}/
        all_folder = Path(f'all_{sub}')
        if all_folder.exists():
            with open(all_folder / f'{sub}_all.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            df.to_csv(all_folder / f'{sub}_all.csv', index=False, encoding='utf-8-sig')
            
        print(f"[OK] {sub} unified and saved (JSON & CSV).")

    print("\n=== FINAL AUDIT OF EXPLANATIONS ===")
    subjects = ['cardio', 'endo', 'gastro', 'renal', 'hema', 'rheuma', 'gync', 'obs', 'peds', 'peds1']
    for s in subjects:
        with open(f'final/{s}/{s}_all.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        non_clinical = []
        for idx, q in enumerate(data):
            exp = q.get('explanation', '').strip()
            if not exp.startswith('- التعليل السريري:') and exp != '#NAME?':
                non_clinical.append((idx+1, exp[:50]))
        if non_clinical:
            print(f"[!] {s} has {len(non_clinical)} non-standard: {non_clinical[:2]}")
        else:
            print(f"[OK] {s}: ALL {len(data)} questions strictly start with '- التعليل السريري:'")

if __name__ == '__main__':
    main()
