import pandas as pd
import random
import re
import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

fpath = r'c:\Users\Toshiba\Desktop\slicer\working_on\تكملة أسئلة الجراحة العامة.csv'
df = pd.read_csv(fpath, encoding='utf-8-sig', header=None)

rng = random.Random(42)
LETTERS = ['A', 'B', 'C', 'D', 'E']

def norm_stem(s):
    if not s or not isinstance(s, str):
        return ''
    s = s.strip()
    s = re.sub(r'[\s:：]*رأس\s*[:：]*$', '', s)
    s = re.sub(r'[\s:：؟?.]+$', '', s)
    return s + ':'

def norm_option(s):
    if not s or not isinstance(s, str):
        return ''
    s = s.strip()
    s = re.sub(r'[\s.:：]+$', '', s)
    return s + '.'

def clean_topic(t):
    if not t or not isinstance(t, str):
        return ''
    return re.sub(r'^\d+\.\s*', '', t).strip()

questions = []
for i in range(len(df)):
    row = df.iloc[i]
    subj = row[0]
    date = row[1]
    topic = clean_topic(row[2])
    stem = norm_stem(row[3])
    corr = norm_option(row[4])
    wrongs = [norm_option(row[col]) for col in range(5, 9) if pd.notna(row[col]) and str(row[col]).strip()]
    
    choices = [{'text': corr, 'is_correct': True}]
    for w in wrongs:
        choices.append({'text': w, 'is_correct': False})
    
    rng.shuffle(choices)
    
    for idx, c in enumerate(choices):
        c['letter'] = LETTERS[idx]
        
    corr_let = next(c['letter'] for c in choices if c['is_correct'])
    questions.append({
        'id': f"q_general_surgery_supp_{i+1:02d}",
        'num': i + 1,
        'subject': subj,
        'date': date,
        'topic': topic,
        'stem': stem,
        'correct_letter': corr_let,
        'choices': choices
    })

print(f"Total parsed: {len(questions)}")
for q in questions:
    print(f"#{q['num']:02d} [{q['id']}] ({q['topic']}) -> Ans: {q['correct_letter']}")
    corr_choice = next(c['text'] for c in q['choices'] if c['is_correct'])
    print(f"    Correct: {corr_choice[:50]}")
