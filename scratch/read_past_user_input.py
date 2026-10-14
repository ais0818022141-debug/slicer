import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

log_path = r'C:\Users\Toshiba\.gemini\antigravity-ide\brain\115252fb-8086-4abc-beca-211b11cc41d7\.system_generated\logs\transcript.jsonl'
with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('type') == 'USER_INPUT':
            print("USER INPUT:", obj.get('content'))
