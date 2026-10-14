import json, csv
with open('final/rheuma/rheuma_all.csv', 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r.get('Question_ID') == 'q_rheuma_28':
            print('CSV Row 28:')
            for k, v in r.items():
                print(f'  {k}: {v}')
            break

with open('final/rheuma/rheuma_all.json', 'r', encoding='utf-8') as f:
    for it in json.load(f):
        if it.get('id') == 'q_rheuma_28':
            print('\nJSON Row 28:')
            print('  title:', it.get('title'))
            print('  correct_option:', it.get('correct_option'))
            for o in it.get('options', []):
                let = o.get('letter')
                txt = o.get('text')
                cor = o.get('is_correct')
                print(f'    {let}: {txt} (correct={cor})')
            break
