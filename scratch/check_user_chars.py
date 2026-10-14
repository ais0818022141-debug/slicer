# -*- coding: utf-8 -*-
user_text_1 = "(c"
user_text_2 = "C)"

print("User text 1 chars:")
for ch in user_text_1:
    print(f"  {repr(ch)}: U+{ord(ch):04X} ({unicodedata.name(ch)})")

print("User text 2 chars:")
for ch in user_text_2:
    print(f"  {repr(ch)}: U+{ord(ch):04X} ({unicodedata.name(ch)})")
