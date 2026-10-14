import sys
import re

with open("pdf_maker/generator.py", 'r', encoding='utf-8') as f:
    code = f.read()

# Search for how topics/ and sessions/ directories are created in generator.py
for line in code.splitlines():
    if "topics" in line.lower() or "sessions" in line.lower() or "mkdir" in line:
        print(line[:100])
