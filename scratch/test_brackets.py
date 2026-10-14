# -*- coding: utf-8 -*-
test_html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 20px; padding: 30px; line-height: 2; }
.box { border: 1px solid #ccc; padding: 15px; margin: 15px 0; }
.opt-tag-bdi { color: #0284c7; font-weight: bold; margin-left: 8px; }
.opt-tag-ltr { color: #0284c7; font-weight: bold; margin-left: 8px; direction: ltr; unicode-bidi: isolate; display: inline-block; }
.opt-tag-span { color: #0284c7; font-weight: bold; margin-left: 8px; }
</style>
</head>
<body>
<h3>Test A: Current generator output with &lt;bdi class="opt-letter-tag"&gt;C)&lt;/bdi&gt;</h3>
<div class="box">
  <div><bdi class="opt-tag-bdi">C)</bdi> <span>عبارة صحيحة؛ يرتكز علاجه على الاستئصال التام</span></div>
</div>

<h3>Test B: With direction: ltr on the tag container &lt;span dir="ltr"&gt;C)&lt;/span&gt;</h3>
<div class="box">
  <div><span dir="ltr" class="opt-tag-ltr">C)</span> <span>عبارة صحيحة؛ يرتكز علاجه على الاستئصال التام</span></div>
</div>

<h3>Test C: With explicit LTR embedding &lrm;C)&lrm;</h3>
<div class="box">
  <div><span class="opt-tag-span">&lrm;C)&lrm;</span> <span>عبارة صحيحة؛ يرتكز علاجه على الاستئصال التام</span></div>
</div>

<h3>Test D: Plain text without tags: C) عبارة صحيحة</h3>
<div class="box">
  <div>C) عبارة صحيحة؛ يرتكز علاجه على الاستئصال التام</div>
</div>

<h3>Test E: Plain text with LRM: &lrm;C)&rlm; عبارة صحيحة</h3>
<div class="box">
  <div>&lrm;C)&rlm; عبارة صحيحة؛ يرتكز علاجه على الاستئصال التام</div>
</div>
</body>
</html>
"""

with open('scratch/test_brackets.html', 'w', encoding='utf-8') as f:
    f.write(test_html)
print("Wrote scratch/test_brackets.html")
