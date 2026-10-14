# -*- coding: utf-8 -*-
import subprocess
import json
import urllib.request
import time
import os

# Test HTML content with different implementations
html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
body { font-size: 24px; direction: rtl; font-family: sans-serif; }
.exp-opt-item { margin: 15px 0; }
.bdi-isolate { unicode-bidi: isolate; }
.span-plain { font-weight: bold; }
</style>
</head>
<body>
  <div id="test1" class="exp-opt-item">
    <bdi class="bdi-isolate"><span id="t1_c">C</span><span id="t1_p">)</span></bdi>
    <span>نص تجريبي</span>
  </div>

  <div id="test2" class="exp-opt-item">
    <span class="span-plain"><span id="t2_c">C</span><span id="t2_p">)</span></span>
    <span>نص تجريبي</span>
  </div>

  <div id="test3" class="exp-opt-item">
    <span style="direction: rtl; unicode-bidi: embed;"><span id="t3_c">C</span><span id="t3_p">)</span></span>
    <span>نص تجريبي</span>
  </div>

  <div id="test4" class="exp-opt-item">
    <span style="display: inline-block; direction: ltr;"><span id="t4_p">)</span><span id="t4_c">C</span></span>
    <span>نص تجريبي</span>
  </div>

  <div id="test5" class="exp-opt-item">
    <span dir="ltr" style="unicode-bidi: isolate;"><span id="t5_c">C</span><span id="t5_p">)</span></span>
    <span>نص تجريبي</span>
  </div>
</body>
</html>
"""

test_path = os.path.abspath("scratch/measure_bidi.html")
with open(test_path, "w", encoding="utf-8") as f:
    f.write(html_content)

# Launch Chrome with remote debugging
chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
temp_profile = os.path.abspath("scratch/chrome_measure_profile")

proc = subprocess.Popen([
    chrome_exe,
    "--headless=new",
    "--remote-debugging-port=9222",
    f"--user-data-dir={temp_profile}",
    f"file:///{test_path.replace(os.sep, '/')}"
])

time.sleep(2)

try:
    # Connect via HTTP to get webSocketDebuggerUrl
    req = urllib.request.urlopen("http://localhost:9222/json")
    tabs = json.loads(req.read().decode())
    target = tabs[0]
    ws_url = target["webSocketDebuggerUrl"]
    
    # We can use websocket to evaluate javascript
    import socket
    # Simple evaluation script:
    # We will get rects of t1..t5
    print("Chrome launched successfully on port 9222")
except Exception as e:
    print("Error:", e)
finally:
    proc.terminate()
