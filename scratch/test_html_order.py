import re, sys
sys.stdout.reconfigure(encoding='utf-8')

for sub in ['thoracic_surgery', 'vascular_surgery']:
    p = f'final/{sub}/{sub}_all_topics.html'
    with open(p, 'r', encoding='utf-8') as f:
        html = f.read()

    # Look for section headers or navigation pills
    # Let's inspect how generator.py renders topics in HTML
    # Check data-topic or topic buttons
    matches = re.findall(r'data-topic="([^"]+)"', html)
    seen = []
    for m in matches:
        if m not in seen:
            seen.append(m)

    print(f"=== {sub} ===")
    print("data-topic count:", len(matches))
    for i, s in enumerate(seen, 1):
        print(f"  {i}. {s}")
