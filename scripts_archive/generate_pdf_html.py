import csv
import re
import os
import html
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def format_text(txt):
    if not txt:
        return ""
    return html.escape(txt).replace("\n", "<br>")

def get_column_mapping(header):
    hdr = [h.strip().replace('\ufeff', '') for h in header]
    mapping = {}
    
    keys = {
        'q_date': ['تاريخ الدورة'],
        'subject': ['المادة'],
        'topic': ['الموضوع'],
        'q_text': ['نص السؤال'],
        'opt_a': ['الخيار A', 'خيار A', 'أ'],
        'opt_b': ['الخيار B', 'خيار B', 'ب'],
        'opt_c': ['الخيار C', 'خيار C', 'ج'],
        'opt_d': ['الخيار D', 'خيار D', 'د'],
        'opt_e': ['الخيار E', 'خيار E', 'هـ', 'ه'],
        'explanation': ['الإجابة والشرح', 'الشرح']
    }
    
    for key, aliases in keys.items():
        found_idx = -1
        for alias in aliases:
            if alias in hdr:
                found_idx = hdr.index(alias)
                break
            for idx, h in enumerate(hdr):
                if alias in h:
                    found_idx = idx
                    break
            if found_idx != -1:
                break
        
        if found_idx == -1:
            if key == 'subject': found_idx = 0 if len(hdr) == 9 else 1
            elif key == 'topic': found_idx = 1 if len(hdr) == 9 else 2
            elif key == 'q_text': found_idx = 2 if len(hdr) == 9 else 3
            elif key == 'opt_a': found_idx = 3 if len(hdr) == 9 else 4
            elif key == 'opt_b': found_idx = 4 if len(hdr) == 9 else 5
            elif key == 'opt_c': found_idx = 5 if len(hdr) == 9 else 6
            elif key == 'opt_d': found_idx = 6 if len(hdr) == 9 else 7
            elif key == 'opt_e': found_idx = 7 if len(hdr) == 9 else 8
            elif key == 'explanation': found_idx = 8 if len(hdr) == 9 else 9
            
        mapping[key] = found_idx
    return mapping

def parse_csv(file_path):
    questions_by_topic = {}
    
    # Try reading first line with both utf-8-sig and cp1256 to check encoding
    encodings = ['utf-8-sig', 'cp1256', 'utf-8']
    success_enc = 'cp1256'
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(100)
            success_enc = enc
            break
        except Exception:
            pass
            
    with open(file_path, 'r', encoding=success_enc) as f:
        reader = csv.reader(f)
        header = next(reader)
        mapping = get_column_mapping(header)
        
        valid_indices = [idx for idx in mapping.values() if idx >= 0]
        max_idx = max(valid_indices) if valid_indices else 0
        
        for idx, row in enumerate(reader):
            if not row or len(row) < max_idx + 1:
                continue
                
            subject = format_text(re.sub(r'\s+', ' ', row[mapping['subject']]).strip())
            topic = format_text(re.sub(r'\s+', ' ', row[mapping['topic']]).strip())
            
            q_date = ""
            if mapping.get('q_date', -1) != -1 and len(row) > mapping['q_date']:
                q_date = format_text(row[mapping['q_date']].strip())
                
            raw_q_text = row[mapping['q_text']].strip()
            if raw_q_text and not (raw_q_text.endswith(':') or raw_q_text.endswith('：')):
                raw_q_text += ':'
            q_text = format_text(raw_q_text)
            opt_a = format_text(row[mapping['opt_a']].strip())
            opt_b = format_text(row[mapping['opt_b']].strip())
            opt_c = format_text(row[mapping['opt_c']].strip())
            opt_d = format_text(row[mapping['opt_d']].strip())
            opt_e = format_text(row[mapping['opt_e']].strip())
            raw_exp = row[mapping['explanation']].strip()
            if raw_exp.startswith('('):
                raw_exp = raw_exp[1:].strip()
                if raw_exp.endswith(').'):
                    raw_exp = raw_exp[:-2].strip() + '.'
                elif raw_exp.endswith(')'):
                    raw_exp = raw_exp[:-1].strip()
            explanation = raw_exp
            
            if not q_text or q_text == "نص السؤال":
                continue
                
            # Parse the correct answer letter from the raw explanation with robust regex
            correct_ans = ""
            match = re.search(r'(?:الإجابة\s+الصحيحة|الإجابة|الجواب)\s*(?:هي)?\s*[:：=]?\s*[\(\["\'\s]*([A-Ea-e])[\)"\'\s]*', raw_exp, flags=re.IGNORECASE)
            if match:
                correct_ans = match.group(1).upper()
                
            question_data = {
                'id': idx,
                'subject': subject,
                'topic': topic,
                'q_date': q_date,
                'q_text': q_text,
                'options': {
                    'A': opt_a,
                    'B': opt_b,
                    'C': opt_c,
                    'D': opt_d,
                    'E': opt_e
                },
                'correct_ans': correct_ans,
                'explanation': explanation
            }
            
            key = (subject, topic)
            if key not in questions_by_topic:
                questions_by_topic[key] = []
            questions_by_topic[key].append(question_data)
            
    # Clean and coerce minor subject outliers (typos in CSV where topic name got copied into subject column)
    subject_counts = {}
    for (subject, topic), qs in questions_by_topic.items():
        subject_counts[subject] = subject_counts.get(subject, 0) + len(qs)
        
    if not subject_counts:
        return questions_by_topic
        
    primary_subject = max(subject_counts, key=subject_counts.get)
    
    cleaned_questions_by_topic = {}
    for (subject, topic), qs in questions_by_topic.items():
        # Coerce minor subjects (with count < 10 questions) to the primary subject
        target_subject = subject
        if subject != primary_subject and subject_counts[subject] < 10:
            target_subject = primary_subject
            
        key = (target_subject, topic)
        if key not in cleaned_questions_by_topic:
            cleaned_questions_by_topic[key] = []
        cleaned_questions_by_topic[key].extend(qs)
        
    return cleaned_questions_by_topic

def clean_badge_text(badge_raw):
    b = badge_raw.strip()
    b = re.sub(r'^[(\s✅]+', '', b).strip()
    if b.endswith('):') or b.endswith(')：'):
        b = b[:-2].strip() + ')'
    elif b.endswith(':') or b.endswith('：'):
        b = b[:-1].strip()
    
    # Balance parentheses if an opening paren is missing its closing paren
    open_c = b.count('(')
    close_c = b.count(')')
    if open_c > close_c:
        if b.endswith('.'):
            b = b[:-1].strip() + ')'
        else:
            b = b + ')'
    return b.strip()

def format_explanation(text):
    if not text:
        return ""

    # Preprocess terms to ensure they start on newlines
    text = re.sub(r'\s*تفنيد\s+الخيارات\s*[:：]', r'\nتفنيد الخيارات:', text)
    text = re.sub(r'\s*(?:ترميم\s+امتحاني|الترميم\s+الشامل)\s*[:：]', r'\nترميم امتحاني:', text)

    # Detect delimiter "الشرح:" (or variants)
    match_sharah = re.search(r'\s*(?:📝)?\s*الشرح\s*[:：]\s*', text)
    
    badge_html = ""
    main_exp_text = ""
    rest_text = ""

    if match_sharah:
        before_part = text[:match_sharah.start()].strip()
        after_part = text[match_sharah.end():].strip()
        
        if before_part:
            badge_content = clean_badge_text(before_part)
            badge_html = f'<span class="exp-correct-badge">{html.escape(badge_content)}</span>'
        
        rest_text = after_part
    else:
        # Fallback if "الشرح:" is not present
        match_ans = re.match(r'^(?:✅)?\s*(الإجابة\s+الصحيحة\s*:\s*[^.\n]+(?:\.[^.\n]+)?)\s*(.*)', text, flags=re.DOTALL)
        if match_ans:
            badge_content = clean_badge_text(match_ans.group(1))
            badge_html = f'<span class="exp-correct-badge">{html.escape(badge_content)}</span>'
            rest_text = match_ans.group(2).strip()
        else:
            rest_text = text.strip()

    lines = [l.strip() for l in rest_text.split('\n') if l.strip()]
    
    parsed_html = []
    bullet_lines = []
    first_main_found = False

    for line in lines:
        # Check for exclusion term
        match_exclusion_term = re.match(r'^تفنيد\s+الخيارات\s*[:：]\s*(.*)', line)
        if match_exclusion_term:
            desc = html.escape(match_exclusion_term.group(1).strip())
            svg_icon = '<svg class="exp-trans-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>'
            bullet_lines.append(f'<div class="exp-bullet-item exp-exclusion-line">{svg_icon}<span>{desc}</span></div>')
            first_main_found = True
            continue

        # Check for remediation term
        match_remediation_term = re.match(r'^(?:ترميم\s+امتحاني|الترميم\s+الشامل)\s*[:：]\s*(.*)', line)
        if match_remediation_term:
            desc = html.escape(match_remediation_term.group(1).strip())
            svg_icon = '<svg class="exp-trans-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>'
            bullet_lines.append(f'<div class="exp-bullet-item exp-remediation-line">{svg_icon}<span>{desc}</span></div>')
            first_main_found = True
            continue

        # Check for note or tip
        match_note = re.match(r'^💡\s*(ملاحظة\s+\w+|ملاحظة)\s*:\s*(.*)', line)
        if match_note:
            note_title = html.escape(match_note.group(1))
            note_text = html.escape(match_note.group(2))
            bullet_lines.append(f'<div class="exp-bullet-item"><strong>💡 {note_title}:</strong> {note_text}</div>')
            first_main_found = True
            continue

        # Check for individual option exclusions
        match_exclusion = re.match(r'^(.*?)\s*\(([A-Ea-e])\)\s*[:：]\s*(.*)', line)
        if match_exclusion:
            opt_title = html.escape(match_exclusion.group(1).strip())
            opt_letter = match_exclusion.group(2).upper()
            opt_desc = html.escape(match_exclusion.group(3).strip())
            bullet_lines.append(f'<div class="exp-bullet-item"><strong>({opt_letter}) {opt_title}:</strong> {opt_desc}</div>')
            first_main_found = True
            continue

        if not first_main_found:
            if main_exp_text:
                main_exp_text += "<br>" + html.escape(line)
            else:
                main_exp_text = html.escape(line)
        else:
            bullet_lines.append(f'<div class="exp-bullet-item">{html.escape(line)}</div>')

    label_html = '<span class="exp-label">الشرح:</span> ' if match_sharah else ''
    
    first_line_html = f"""
    <div class="exp-first-line">
        {badge_html}
        <span class="exp-main-text">{label_html}{main_exp_text}</span>
    </div>"""
    
    parsed_html.append(first_line_html)

    if bullet_lines:
        parsed_html.append('<div class="exp-bullet-list">')
        parsed_html.extend(bullet_lines)
        parsed_html.append('</div>')

    return "\n".join(parsed_html)

def generate_html(grouped_questions, output_path, theme_name=None):
    # Group by subject to prevent subjects from alternating and repeating index HTML
    subject_order = []
    grouped_by_subject = {} # subject -> { topic: qs }
    for (sub, top), qs in grouped_questions.items():
        if sub not in grouped_by_subject:
            subject_order.append(sub)
            grouped_by_subject[sub] = {}
        grouped_by_subject[sub][top] = qs

    # Pre-calculate mapping of subjects to their topics, and assign robust unique IDs for anchor linking
    subject_topics = {}
    topic_ids = {}
    global_topic_counter = 1
    for subject in subject_order:
        subject_topics[subject] = list(grouped_by_subject[subject].keys())
        for topic in subject_topics[subject]:
            topic_ids[(subject, topic)] = f"topic-{global_topic_counter}"
            global_topic_counter += 1

    html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بنك الأسئلة المنسق - القلبية</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800;900&display=swap" rel="stylesheet">
    <style>
        /* Embedding local fonts */
        @font-face {
            font-family: 'BoutrosJazirah';
            src: url('../fonts/BoutrosJazirahTextLight.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'BoutrosJazirah';
            src: url('../fonts/BoutrosJazirahTextLight.ttf') format('truetype');
            font-weight: 500;
            font-style: normal;
        }
        @font-face {
            font-family: 'BoutrosJazirah';
            src: url('../fonts/BoutrosNewsH1-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }
        @font-face {
            font-family: 'BoutrosJazirah';
            src: url('../fonts/BoutrosNewsH1-Bold.ttf') format('truetype');
            font-weight: 700;
            font-style: normal;
        }
        @font-face {
            font-family: 'BoutrosJazirah';
            src: url('../fonts/BoutrosNewsH1-Bold.ttf') format('truetype');
            font-weight: 800;
            font-style: normal;
        }
        @font-face {
            font-family: 'BoutrosJazirah';
            src: url('../fonts/BoutrosNewsH1-Bold.ttf') format('truetype');
            font-weight: 900;
            font-style: normal;
        }
        @font-face {
            font-family: 'BoutrosNews';
            src: url('../fonts/BoutrosNewsH1-Bold.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'BoutrosNews';
            src: url('../fonts/BoutrosNewsH1-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }
        @font-face {
            font-family: 'SakkalMajalla';
            src: url('../fonts/Sakkal Majalla Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'SakkalMajalla';
            src: url('../fonts/Sakkal Majalla Regular.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }

        /* CSS variables for consistent layout */
        :root {
            --primary-color: #9C1C1C;        /* Elegant Deep Crimson Red - comfortable for eye & printing */
            --primary-light: #C94A4A;        /* Soft Crimson Light */
            --primary-dark: #661010;         /* Dark Burgundy Red */
            --accent-color: #E28700;         /* Complementary warm amber accent */
            --bg-color: #FAF5F5;             /* Very soft rose-white background to prevent screen glare */
            --card-bg: #ffffff;              /* White */
            --shade-bg: #FFFBFB;             /* Extremely soft pastel rose-tint shade (prints almost white) */
            --question-bg: #FFF8F8;          /* Even more softened light red-tint for question headers (slightly darker than shade-bg) */
            --text-color: #262730;           /* Soft charcoal slate for text */
            --text-muted: #7f8c8d;
            --border-color: #EBC2C2;         /* Soft red border color */
            --question-text-color: #4A0707;  /* Dark text color for the question title */
            
            --correct-bg: #d1e7dd;           /* Soft green for correct option */
            --correct-border: #badbcc;
            --correct-text: #0f5132;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'BoutrosJazirah', 'Tajawal', sans-serif; /* Set default text typography to BoutrosJazirah */
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.4;
            font-size: 0.95rem;
            padding-bottom: 20px;
        }

        /* Top controls for interactive mode */
        .controls-header {
            background-color: var(--primary-dark);
            color: white;
            padding: 8px 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header-title-container {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .header-title-container h1 {
            font-family: 'BoutrosNews', 'Tajawal', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
        }

        .header-icon {
            font-size: 1.25rem;
        }

        .btn-group {
            display: flex;
            gap: 8px;
        }

        .btn {
            font-family: 'BoutrosJazirah', 'Tajawal', sans-serif;
            font-weight: 600;
            font-size: 0.8rem;
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-primary {
            background-color: var(--primary-light);
            color: white;
        }

        .btn-primary:hover {
            background-color: #ffffff;
            color: var(--primary-dark);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
        }

        .btn-outline {
            background-color: transparent;
            border: 1px solid white;
            color: white;
        }

        .btn-outline:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }

        .btn-active {
            background-color: var(--accent-color) !important;
            color: var(--primary-dark) !important;
            border-color: var(--accent-color) !important;
        }

        /* Container & Layout */
        .container {
            max-width: 900px;
            margin: 10px auto;
            padding: 0 10px;
        }

        .subject-group {
            margin-bottom: 15px;
        }

        .subject-title {
            font-family: 'BoutrosNews', 'Tajawal', sans-serif;
            font-size: 2.2rem;       /* Much larger for the main heading */
            color: var(--primary-dark);
            text-align: center;
            margin-top: 30px;
            margin-bottom: 15px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            border: none;
            padding-bottom: 10px;
        }

        .subject-title::after {
            content: "";
            display: block;
            width: 120px;
            height: 3px;
            background-color: var(--primary-color);
            border-radius: 2px;
            margin-top: 4px;
        }

        /* Index / Table of Contents Styles */
        .subject-index {
            background-color: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px 20px;
            margin-bottom: 25px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            page-break-after: always;
            break-after: page;
        }

        .index-title {
            font-family: 'BoutrosNews', 'Tajawal', sans-serif;
            font-size: 1.15rem;
            color: var(--primary-color);
            margin-bottom: 12px;
            font-weight: bold;
            border-bottom: 1px dashed var(--border-color);
            padding-bottom: 6px;
        }

        .index-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px 24px;
        }

        .index-item {
            font-family: 'BoutrosJazirah', 'Tajawal', sans-serif;
            font-size: 0.95rem;
            color: var(--text-color);
            text-decoration: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 4px 8px;
            border-radius: 4px;
            transition: all 0.15s ease;
        }

        .index-item:hover {
            background-color: var(--shade-bg);
            color: var(--primary-color);
        }

        .index-badge {
            font-size: 0.65rem;
            color: var(--text-muted);
            background-color: var(--question-bg);
            padding: 1px 5px;
            border-radius: 8px;
            font-weight: 500;
            opacity: 0.85;
        }

        .title-bullet {
            color: var(--primary-color);
            margin-left: 6px;
            font-size: 1.1rem;
        }

        .index-bullet {
            color: var(--primary-color);
            margin-left: 8px;
            font-size: 0.85rem;
        }

        .topic-section {
            background-color: transparent;
            margin-bottom: 12px;
        }

        .topic-header-wrapper {
            page-break-inside: avoid;
            break-inside: avoid;
            page-break-after: avoid;
            break-after: avoid;
        }

        :is(h1, h2, h3, h4, h5, h6, .subject-title, .topic-header, .topic-header-wrapper, .question-header) {
            page-break-after: avoid !important;
            break-after: avoid !important;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }

        :is(h1, h2, h3, h4, h5, h6, .subject-title, .topic-header, .topic-header-wrapper) + * {
            page-break-before: avoid !important;
            break-before: avoid !important;
        }

        /* Topic Header: Centered pill-shaped container with transparent background and border */
        .topic-header {
            font-family: 'BoutrosNews', 'Tajawal', sans-serif;
            background-color: transparent;
            border: 1px solid var(--border-color);
            border-radius: 20px;
            color: var(--primary-color);
            font-size: 1.4rem;     /* Enlarged topic title */
            font-weight: bold;
            padding: 6px 20px;
            margin-top: 20px;
            margin-bottom: 12px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            width: max-content;
            max-width: 90%;
            margin-left: auto;
            margin-right: auto;
            scroll-margin-top: 110px; /* Leaves space for sticky header in browser study/exam modes */
        }

        .topic-badge {
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 600;
            background: transparent;
            padding: 0;
        }

        .questions-list {
            padding: 0;
        }

        /* Standalone Question Cards: Compact spacing */
        .question-card {
            background-color: transparent;
            border: none;
            border-radius: 0;
            margin-bottom: 8px; 
            overflow: visible;
            padding: 0;
        }

        /* Question Header: Light red-tint background with a deep red right vertical border, dark burgundy text. Snug padding and line-height */
        .question-header {
            background-color: var(--question-bg);
            color: var(--question-text-color);            /* Darker text color for high contrast and elegance */
            padding: 4px 8px;          /* Symmetrical padding for comfortable text alignment inside colored box */
            font-size: 1.05rem;    /* Uniform font size */
            font-weight: 700;      /* Thicker font weight */
            border: none;
            border-right: 4px solid var(--primary-color); /* Vertical right border */
            border-radius: 0 4px 4px 0; /* Soft rounded corners on starting border */
            line-height: 1.25;     /* Snug line-height */
            margin-bottom: 6px;    /* Small gap below header */
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }

        .q-number {
            flex-shrink: 0;
        }

        .q-text {
            flex: 1;
        }

        .q-date {
            font-size: 0.8rem;
            background-color: rgba(255, 255, 255, 0.55);
            color: var(--primary-dark);
            padding: 2px 6px;
            border-radius: 3px;
            white-space: nowrap;
            font-weight: 500;
            margin-right: auto;   /* Push date to the far left in RTL layout */
            margin-left: 0;
            flex-shrink: 0;
            align-self: flex-start;
            margin-top: 1px;
        }

        .question-body {
            padding: 0;
        }

        /* Options layout: 3 equal columns, row 2 column 3 remains empty */
        .options-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 4px;              /* Reduced gap */
            margin-bottom: 4px;
        }

        /* Option Card: Soft Pastel Rose background, NORMAL and SOLID BLACK text. No border */
        .option-card {
            background-color: var(--shade-bg); /* Soft shade background */
            border: none;                       /* No border */
            padding: 2px 6px;      /* Minimized padding so font fills box */
            border-radius: 4px;
            display: flex;
            align-items: flex-start;
            gap: 4px;
        }

        .option-letter {
            font-weight: 500;  /* Medium */
            color: var(--primary-color);
            margin-left: 4px;
            font-size: 1.25rem;/* Uniform font size */
        }

        .option-text {
            color: #000000;    /* Solid black */
            font-weight: 500;  /* Medium weight */
            font-size: 1.25rem;/* Uniform font size */
            text-align: right;
            display: inline-block;
        }

        .option-card.last-stretch {
            grid-column: span 2; /* Stretch E to fill the 2 remaining columns */
        }

        /* Study Mode styles (applied when answers are shown) */
        .study-mode .option-card.correct {
            background-color: var(--correct-bg);
            border-color: var(--correct-border);
        }

        .study-mode .option-card.correct .option-text,
        .study-mode .option-card.correct .option-letter {
            color: var(--correct-text) !important;
            font-weight: 700;
        }

        .study-mode .option-card.correct::before {
            content: "✓ ";
            color: var(--correct-text);
            font-weight: bold;
            margin-left: 2px;
        }

        /* Explanation Box: White background, BoutrosJazirah font, Clear Black. High-density layout */
        .explanation-box {
            font-family: 'BoutrosJazirah', 'Tajawal', sans-serif;
            background-color: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 12px;      
            font-size: 1.25rem;    /* Legible but compact font size */
            font-weight: 500;
            color: #262730;
            margin-top: 6px;
            line-height: 1.45;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.01);
        }

        /* First Line: Answer badge and explanation starting immediately on the same line */
        .exp-first-line {
            margin-bottom: 4px;
        }

        .exp-correct-badge {
            background-color: transparent;
            color: var(--primary-color);
            padding: 2px 6px;
            border: 1px solid var(--primary-color);
            border-radius: 4px;
            font-weight: 700;
            font-size: 0.95rem; /* Uniform font size */
            display: inline-block;
            margin-left: 6px; /* RTL space after badge */
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }

        .exp-main-text {
            font-size: 1.25rem; /* Uniform font size */
            color: #262730;
        }

        .exp-label {
            font-size: 0.85em; /* Reduced by 2 steps relative to explanation font size */
            font-weight: 700;
            color: var(--primary-dark);
            margin-left: 4px;
        }

        /* Bullet List for subsequent lines */
        .exp-bullet-list {
            margin-top: 4px;
            display: flex;
            flex-direction: column;
            gap: 3px; /* Small distance between lines */
            border-top: 1px dashed var(--border-color);
            padding-top: 4px;
        }

        .exp-bullet-title {
            font-size: 1.25rem; /* Uniform font size */
            color: var(--primary-color);
            margin-top: 2px;
            margin-bottom: 1px;
        }

        .exp-bullet-item {
            font-size: 1.25rem; /* Uniform font size */
            line-height: 1.4;
            padding-right: 14px; /* RTL indent for bullet */
            position: relative;
            color: #2b2c35;
        }

        .exp-bullet-item::before {
            content: "✦"; /* Elegant bullet shape */
            color: var(--primary-color); /* Matching color */
            position: absolute;
            right: 0;
            top: 0.35em; /* Aligns perfectly with the middle of the first line of text */
            font-size: 0.8rem;
            line-height: 1;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }

        .exp-exclusion-line::before,
        .exp-remediation-line::before {
            content: none !important; /* Hide default ✦ bullet */
        }
        .exp-exclusion-line,
        .exp-remediation-line {
            padding-right: 0 !important; /* Reset indent since we have custom inline icons */
            display: flex;
            align-items: flex-start;
            gap: 6px;
        }
        .exp-trans-icon {
            width: 1.15rem;
            height: 1.15rem;
            margin-top: 2px; /* Center-align icon visually with the first line of text */
            color: var(--primary-color);
            flex-shrink: 0;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }

        /* Toggle study/exam elements */
        .exam-mode .explanation-box {
            display: none !important;
        }

        /* Print formatting */
        @media print {
            body {
                background-color: white;
                color: black;
                font-size: 8.5pt;  
                line-height: 1.3;
            }

            .controls-header {
                display: none !important;
            }

            .container {
                max-width: 100%;
                margin: 0;
                padding: 0;
            }

            .topic-section {
                margin-bottom: 8px;
            }

            .subject-title {
                font-size: 20pt !important;
                margin-top: 20px !important;
                margin-bottom: 15px !important;
                text-align: center !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                border: none !important;
                padding-bottom: 10px !important;
            }

            .subject-title::after {
                content: "" !important;
                display: block !important;
                width: 100px !important;
                height: 2px !important;
                background-color: var(--primary-color) !important;
                margin-top: 3px !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }

            .subject-index {
                border: 1px solid var(--border-color) !important;
                background-color: #ffffff !important;
                padding: 12px 15px !important;
                margin-bottom: 20px !important;
                page-break-after: avoid;
            }

            .index-title {
                font-size: 11pt !important;
                color: var(--primary-color) !important;
                border-bottom: 1px dashed var(--border-color) !important;
                padding-bottom: 4px !important;
            }

            .index-item {
                font-size: 9pt !important;
                color: black !important;
            }

            .index-badge {
                font-size: 8pt !important;
                color: var(--text-muted) !important;
                background-color: var(--question-bg) !important;
            }

            .title-bullet, .index-bullet {
                color: var(--primary-color) !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }

            .topic-header {
                background-color: transparent !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 20px !important;
                color: var(--primary-color) !important;
                font-size: 13pt;       /* Enlarged topic size on print */
                font-weight: bold;
                padding: 4px 15px;
                margin-top: 12px;
                margin-bottom: 8px;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 6px;
                width: max-content;
                max-width: 95%;
                margin-left: auto;
                margin-right: auto;
                border-right: none !important;
            }

            .topic-badge {
                font-size: 8.5pt;
                color: var(--text-muted);
            }

            .topic-header-wrapper {
                page-break-inside: avoid;
                break-inside: avoid;
            }

            .question-card {
                page-break-inside: avoid;
                break-inside: avoid;
                border: none;
                margin-bottom: 6px;
            }

            .question-header {
                background-color: var(--question-bg) !important;
                color: var(--question-text-color) !important; /* Darker Burgundy text on print */
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                font-size: 10pt;     /* Enlarged question text on print */
                font-weight: bold;   /* Bold on print */
                padding: 3px 6px;    /* Symmetrical padding for print */
                border: none !important;
                border-right: 3px solid var(--primary-color) !important;
                line-height: 1.25;   /* Snug line-height */
            }

            .option-card {
                border: none !important;            /* No border on print */
                background-color: var(--shade-bg) !important; /* Soft shade background on print */
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                padding: 1px 4px;   /* Minimized padding */
            }

            .option-text {
                font-size: 12pt;    /* Enlarged options text on print */
                color: #000000 !important;
                font-weight: 500;
            }

            .option-letter {
                font-size: 12pt;
                font-weight: 500;
            }

            .study-mode .option-card.correct {
                background-color: var(--correct-bg) !important;
                border-color: var(--correct-border) !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }

            .study-mode .option-card.correct .option-text,
            .study-mode .option-card.correct .option-letter {
                color: var(--correct-text) !important;
            }

            .explanation-box {
                font-family: 'BoutrosJazirah', 'Tajawal', sans-serif;
                background-color: #ffffff !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                border: 1px solid var(--border-color);
                padding: 3px 6px;   
                font-size: 12pt;    /* Enlarged explanation text size to match options */
                color: #000000 !important;
                font-weight: 500;
                margin-top: 3px;
                line-height: 1.3;
            }

            .exp-correct-badge {
                background-color: transparent !important;
                color: var(--primary-color) !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                border: 1px solid var(--primary-color) !important;
                font-size: 9pt !important;
            }

            .exp-main-text,
            .exp-bullet-title,
            .exp-bullet-item {
                font-size: 12pt !important;
            }

            .exp-label {
                font-size: 0.85em !important; /* 2 steps smaller in print */
                font-weight: 700;
            }

            .exp-bullet-item::before {
                font-size: 8.5pt !important;
            }

            .exp-title {
                color: var(--primary-dark) !important;
            }

            .no-print {
                display: none !important;
            }

            @page {
                size: A4;
                margin: 0.8cm;
            }
        }

        .card-action-buttons {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-bottom: 12px;
            padding: 0 4px;
        }
        
        .action-btn {
            font-family: 'BoutrosJazirah', 'Tajawal', sans-serif;
            font-size: 0.85rem;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background-color: var(--shade-bg);
            color: var(--primary-color);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }

        .action-btn:hover {
            background-color: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
</head>
<body class="study-mode">

    <!-- Interactive top panel for user ease -->
    <div class="controls-header no-print">
        <div class="header-title-container">
            <span class="header-icon">🫀</span>
            <h1>بنك الأسئلة المنسق والمجدول</h1>
        </div>
        <div class="btn-group">
            <button id="btnStudy" class="btn btn-outline btn-active" onclick="setMode('study')">
                <span>📖</span> وضع الدراسة (إجابات ملونة + شرح)
            </button>
            <button id="btnExport" class="btn btn-outline" onclick="setMode('export')">
                <span>📄</span> وضع التصدير (إجابات نصية + شرح)
            </button>
            <button id="btnExam" class="btn btn-outline" onclick="setMode('exam')">
                <span>📝</span> وضع الاختبار (إخفاء الإجابات والشرح)
            </button>
            <button class="btn btn-primary" onclick="window.print()">
                <span>🖨️</span> حفظ كـ PDF / طباعة
            </button>
        </div>
    </div>

    <div class="container">
"""
    
    for subject in subject_order:
        # Generate the index (Table of Contents) HTML for this subject
        index_html = '        <div class="subject-index">\n'
        index_html += '            <div class="index-title"><span class="title-bullet">✦</span> فهرس المواضيع والتصنيفات</div>\n'
        index_html += '            <div class="index-grid">\n'
        for top in subject_topics[subject]:
            t_id = topic_ids[(subject, top)]
            qs_list = grouped_by_subject[subject][top]
            index_html += f'                <a href="#{t_id}" class="index-item"><span class="index-bullet">✦</span> {top} <span class="index-badge">({len(qs_list)} سؤال)</span></a>\n'
        index_html += '            </div>\n'
        index_html += '        </div>\n'

        html_content += f"""
        <div class="subject-group">
            <h1 class="subject-title">
                {subject}
            </h1>
            {index_html}
"""
        
        for topic in subject_topics[subject]:
            qs = grouped_by_subject[subject][topic]
            q_count = len(qs)
            t_id = topic_ids[(subject, topic)]
            html_content += f"""
            <div class="topic-section">
                <div class="questions-list">
"""
            
            for i, q in enumerate(qs, 1):
                opts_html = ""
                
                option_keys = ['A', 'B', 'C', 'D', 'E']
                for k in option_keys:
                    opt_val = q['options'][k]
                    if not opt_val:
                        continue
                    
                    is_correct = (k == q['correct_ans'])
                    cls = "option-card"
                    if is_correct:
                        cls += " correct"
                    if k == 'E':
                        cls += " last-stretch"
                        
                    opts_html += f"""
                            <div class="{cls}">
                                <span class="option-letter">{k}.</span>
                                <span class="option-text">{opt_val}</span>
                            </div>"""
                
                exp_html = ""
                if q['explanation']:
                    exp_html = f"""
                        <div class="explanation-box">
                            {format_explanation(q['explanation'])}
                        </div>"""
                
                date_html = ""
                if q.get('q_date'):
                    date_html = f'<span class="q-date">{q["q_date"]}</span>'

                card_html = f"""
                        <div class="question-card" id="q-{q['id']}">
                            <div class="question-header">
                                <span class="q-number">{i}.</span>
                                <span class="q-text">{q['q_text']}</span>
                                {date_html}
                            </div>
                            <div class="card-action-buttons no-print">
                                <button class="action-btn" onclick="downloadScreenshot('q-{q['id']}', 'vignette')">📸 صورة الحالة</button>
                                <button class="action-btn" onclick="downloadScreenshot('q-{q['id']}', 'explanation')">📸 صورة الشرح</button>
                                <button class="action-btn" onclick="copyOptions('q-{q['id']}', this)">📋 نسخ الخيارات</button>
                                <button class="action-btn" onclick="copyStem('q-{q['id']}', this)">📋 نسخ جذع السؤال</button>
                            </div>
                            <div class="question-body">
                                <div class="options-grid">
                                    {opts_html}
                                </div>
                                {exp_html}
                            </div>
                        </div>"""

                if i == 1:
                    html_content += f"""
                        <div class="topic-header-wrapper">
                            <div class="topic-header" id="{t_id}">
                                <span>{topic}</span>
                                <span class="topic-badge">({q_count} أسئلة)</span>
                            </div>
                            {card_html}
                        </div>"""
                else:
                    html_content += card_html
                
            html_content += """
                </div><!-- end questions-list -->
            </div><!-- end topic-section -->
"""
            
        html_content += "    </div><!-- end subject-group -->\n"
        
    html_content += """
    </div><!-- end container -->

    <script>
        function setMode(mode) {
            const body = document.body;
            const btnStudy = document.getElementById('btnStudy');
            const btnExport = document.getElementById('btnExport');
            const btnExam = document.getElementById('btnExam');
            
            // Reset classes and active buttons
            body.classList.remove('study-mode', 'export-mode', 'exam-mode');
            btnStudy.classList.remove('btn-active');
            btnExport.classList.remove('btn-active');
            btnExam.classList.remove('btn-active');
            
            if (mode === 'study') {
                body.classList.add('study-mode');
                btnStudy.classList.add('btn-active');
            } else if (mode === 'export') {
                body.classList.add('export-mode');
                btnExport.classList.add('btn-active');
            } else if (mode === 'exam') {
                body.classList.add('exam-mode');
                btnExam.classList.add('btn-active');
            }
        }

        function downloadScreenshot(questionId, mode) {
            const card = document.getElementById(questionId);
            if (!card) return;

            // Find parts of the card
            const qHeader = card.querySelector('.question-header');
            const qNumber = card.querySelector('.q-number');
            const qText = card.querySelector('.q-text');
            const options = card.querySelector('.options-grid');
            const expBox = card.querySelector('.explanation-box');
            const actionButtons = card.querySelector('.card-action-buttons');

            // Store original display values
            const originalStates = [
                { el: qHeader, display: qHeader ? qHeader.style.display : '' },
                { el: qNumber, display: qNumber ? qNumber.style.display : '' },
                { el: qText, display: qText ? qText.style.display : '' },
                { el: options, display: options ? options.style.display : '' },
                { el: expBox, display: expBox ? expBox.style.display : '' },
                { el: actionButtons, display: actionButtons ? actionButtons.style.display : '' }
            ];

            // Hide action buttons so they don't show on screenshot
            if (actionButtons) actionButtons.style.display = 'none';

            if (mode === 'vignette') {
                // Keep header/number and the question text. Hide options and explanation box.
                if (options) options.style.display = 'none';
                if (expBox) expBox.style.display = 'none';
            } else if (mode === 'explanation') {
                // Keep header/number and explanation box. Hide question text and options.
                if (qText) qText.style.display = 'none';
                if (options) options.style.display = 'none';
                if (expBox) expBox.style.setProperty('display', 'block', 'important');
            }

            // Set temporary styling for card screenshot context (clean white bg, card padding and borders)
            const originalBg = card.style.backgroundColor;
            const originalPadding = card.style.padding;
            const originalShadow = card.style.boxShadow;
            const originalBorder = card.style.border;

            card.style.backgroundColor = '#ffffff';
            card.style.padding = '24px';
            card.style.boxShadow = 'none';
            card.style.border = '1px solid var(--border-color)';

            // Call html2canvas
            html2canvas(card, {
                scale: 2.5, // Ultra-high resolution (crisp text, very readable)
                useCORS: true,
                backgroundColor: '#ffffff'
            }).then(canvas => {
                // Restore all original styles
                originalStates.forEach(state => {
                    if (state.el) state.el.style.display = state.display;
                });
                card.style.backgroundColor = originalBg;
                card.style.padding = originalPadding;
                card.style.boxShadow = originalShadow;
                card.style.border = originalBorder;

                // Download the generated image
                const link = document.createElement('a');
                const qNumText = qNumber ? qNumber.textContent.trim() : 'question';
                link.download = `${qNumText}_${mode}.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();
            }).catch(err => {
                console.error('Screenshot capturing failed:', err);
                alert("تنبيه: فشل التقاط الصورة. قد يكون هذا بسبب قيود الأمان في المتصفح عند تشغيل الملف محلياً (CORS). يرجى محاولة فتح الملف باستخدام متصفح آخر مثل Firefox، أو تشغيل خادم محلي (Local Server) لحل المشكلة.");
                // Restore states on error
                originalStates.forEach(state => {
                    if (state.el) state.el.style.display = state.display;
                });
                card.style.backgroundColor = originalBg;
                card.style.padding = originalPadding;
                card.style.boxShadow = originalShadow;
                card.style.border = originalBorder;
            });
        }

        function copyToClipboard(text, btnElement, successMsg = "تم النسخ! ✓") {
            if (!text) return;
            const originalText = btnElement.innerHTML;
            
            function showSuccess() {
                btnElement.innerHTML = `<span>${successMsg}</span>`;
                btnElement.style.borderColor = "var(--correct-border, #badbcc)";
                btnElement.style.color = "var(--correct-text, #0f5132)";
                setTimeout(() => {
                    btnElement.innerHTML = originalText;
                    btnElement.style.borderColor = "";
                    btnElement.style.color = "";
                }, 1500);
            }

            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(showSuccess).catch(err => {
                    fallbackCopy(text, showSuccess);
                });
            } else {
                fallbackCopy(text, showSuccess);
            }
        }

        function fallbackCopy(text, callback) {
            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "fixed";
            textArea.style.left = "-999999px";
            textArea.style.top = "-999999px";
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                if (callback) callback();
            } catch (err) {
                console.error('Fallback copy failed', err);
            }
            document.body.removeChild(textArea);
        }

        function copyOptions(questionId, btn) {
            const card = document.getElementById(questionId);
            if (!card) return;
            
            const optionCards = card.querySelectorAll('.option-card');
            const optionsTextList = [];
            optionCards.forEach(opt => {
                const letterEl = opt.querySelector('.option-letter');
                const textEl = opt.querySelector('.option-text');
                if (letterEl && textEl) {
                    let letter = letterEl.textContent.trim();
                    let text = textEl.textContent.trim();
                    optionsTextList.push(`${letter} ${text}`);
                }
            });
            
            const textToCopy = optionsTextList.join('\\n');
            copyToClipboard(textToCopy, btn);
        }

        function copyStem(questionId, btn) {
            const card = document.getElementById(questionId);
            if (!card) return;
            
            const stemEl = card.querySelector('.question-text') || card.querySelector('.q-text');
            if (stemEl) {
                let text = stemEl.textContent.trim();
                copyToClipboard(text, btn);
            }
        }
    </script>
</body>
</html>
"""
    
    # Determine page title, header icon, and theme dynamically based on first subject or output path
    first_subject = next(iter(grouped_questions.keys()))[0] if grouped_questions else ""
    page_title = f"بنك الأسئلة المنسق - {first_subject}"
    
    is_gastro = False
    is_pulmo = False
    is_nephro = False
    is_ent = False
    is_obgyn = False
    is_obs = False
    is_peds2 = False
    is_peds = False
    
    if theme_name:
        is_gastro = theme_name.lower() == "gastroenterology"
        is_pulmo = theme_name.lower() == "pulmonology"
        is_nephro = theme_name.lower() == "nephrology"
        is_ent = theme_name.lower() in ["otolaryngology", "ent"]
        is_obgyn = theme_name.lower() in ["gynecology", "obgyn"]
        is_obs = theme_name.lower() in ["obstetrics", "obs", "tawlid"]
        is_peds2 = theme_name.lower() in ["pediatrics2", "peds2", "pediatrics 2", "اطفال 2", "الاطفال 2", "الأطفال 2"]
        is_peds = theme_name.lower() in ["pediatrics", "peds", "pediatrics1", "peds1"] and not is_peds2
    else:
        is_gastro = "هضمية" in first_subject.lower() or "الهضمية" in first_subject or "gastro" in output_path.lower()
        is_pulmo = "صدرية" in first_subject.lower() or "الصدرية" in first_subject or "pulmo" in output_path.lower()
        is_nephro = "كلية" in first_subject.lower() or "الكلية" in first_subject or "nephro" in output_path.lower()
        is_ent = "أذنية" in first_subject.lower() or "الأذنية" in first_subject or "أذن" in first_subject.lower() or "ent" in output_path.lower()
        is_obgyn = any(kw in first_subject.lower() or kw in output_path.lower() for kw in ["نسائية", "النسائية", "gyne"])
        is_obs = any(kw in first_subject.lower() or kw in output_path.lower() for kw in ["توليد", "التوليد", "obs", "obstetrics"])
        is_peds2 = any(kw in first_subject.lower() or kw in output_path.lower() for kw in ["اطفال 2", "الاطفال 2", "الأطفال 2", "peds2", "peds_2", "pediatrics2", "pediatrics 2"])
        is_peds = any(kw in first_subject.lower() or kw in output_path.lower() for kw in ["اطفال", "الأطفال", "الاطفال", "peds", "pediatrics"]) and not is_peds2
    
    if is_gastro:
        # Orange/Terracotta Theme for Gastroenterology
        header_icon = "🩺"
        primary_color = "#BD4B00"
        primary_light = "#E06D14"
        primary_dark = "#803000"
        accent_color = "#0284C7"
        bg_color = "#FAF6F2"
        shade_bg = "#FFF8F2"
        question_bg = "#FFF2E6"
        border_color = "#F5DCC4"
        question_text_color = "#4A1A07"
    elif is_pulmo:
        # Blue Theme for Pulmonology
        header_icon = "🫁"
        primary_color = "#0A5C8F"
        primary_light = "#0284C7"
        primary_dark = "#073B5E"
        accent_color = "#D97706"
        bg_color = "#F0F6FA"
        shade_bg = "#F5F9FC"
        question_bg = "#EAF2F8"
        border_color = "#C6DBEC"
        question_text_color = "#072C4A"
    elif is_ent:
        # Blue Theme for ENT / Otolaryngology
        header_icon = "👂"
        primary_color = "#0A5C8F"
        primary_light = "#0284C7"
        primary_dark = "#073B5E"
        accent_color = "#D97706"
        bg_color = "#F0F6FA"
        shade_bg = "#F5F9FC"
        question_bg = "#EAF2F8"
        border_color = "#C6DBEC"
        question_text_color = "#072C4A"
    elif is_obgyn:
        # Soft Pink/Rose Theme for Obstetrics & Gynecology (Tawlid & Nisa'iyyah)
        header_icon = "🌸"
        primary_color = "#B83262"
        primary_light = "#D85888"
        primary_dark = "#7A163D"
        accent_color = "#0D9488"
        bg_color = "#FAF2F4"
        shade_bg = "#FFF7F9"
        question_bg = "#FCE8EE"
        border_color = "#F5CCD7"
        question_text_color = "#4C0822"
    elif is_obs:
        # Soft Purple/Indigo Theme for Obstetrics (Tawlid)
        header_icon = "🤰"
        primary_color = "#6A1B9A"
        primary_light = "#8E24AA"
        primary_dark = "#4A148C"
        accent_color = "#10B981"
        bg_color = "#FBF8FD"
        shade_bg = "#FFF9FF"
        question_bg = "#F5EBFA"
        border_color = "#E8D0F5"
        question_text_color = "#3A0F5C"
    elif is_nephro:
        # Purple Theme for Nephrology
        header_icon = "🔬"
        primary_color = "#5A189A"
        primary_light = "#7B2CBF"
        primary_dark = "#3C096C"
        accent_color = "#10B981"
        bg_color = "#FAF5FF"
        shade_bg = "#FCF8FF"
        question_bg = "#F3E8FF"
        border_color = "#E9D5FF"
        question_text_color = "#3C096C"
    elif is_peds2:
        # Soft Ocean Cyan / Sky Blue Theme for Pediatrics 2 (الأطفال 2)
        header_icon = "🪁"
        primary_color = "#0284C7"
        primary_light = "#38BDF8"
        primary_dark = "#0369A1"
        accent_color = "#F59E0B"
        bg_color = "#F0F9FF"
        shade_bg = "#F8FAFC"
        question_bg = "#E0F2FE"
        border_color = "#BAE6FD"
        question_text_color = "#0C4A6E"
    elif is_peds:
        # Soft Teal/Mint Theme for Pediatrics 1 (الأطفال 1)
        header_icon = "🧸"
        primary_color = "#0D9488"
        primary_light = "#14B8A6"
        primary_dark = "#115E59"
        accent_color = "#F59E0B"
        bg_color = "#F2FAF9"
        shade_bg = "#F7FCFB"
        question_bg = "#E6F5F3"
        border_color = "#C5ECE7"
        question_text_color = "#0B4B47"
    else:
        # Red Theme for Cardiology
        header_icon = "🫀"
        primary_color = "#9C1C1C"
        primary_light = "#C94A4A"
        primary_dark = "#661010"
        accent_color = "#E28700"
        bg_color = "#FAF5F5"
        shade_bg = "#FFFBFB"
        question_bg = "#FFF8F8"
        border_color = "#EBC2C2"
        question_text_color = "#4A0707"
        
    html_content = html_content.replace("<title>بنك الأسئلة المنسق - القلبية</title>", f"<title>{page_title}</title>")
    html_content = html_content.replace('<span class="header-icon">🫀</span>', f'<span class="header-icon">{header_icon}</span>')
    
    # Replace theme color variables
    html_content = html_content.replace("--primary-color: #9C1C1C;", f"--primary-color: {primary_color};")
    html_content = html_content.replace("--primary-light: #C94A4A;", f"--primary-light: {primary_light};")
    html_content = html_content.replace("--primary-dark: #661010;", f"--primary-dark: {primary_dark};")
    html_content = html_content.replace("--accent-color: #E28700;", f"--accent-color: {accent_color};")
    html_content = html_content.replace("--bg-color: #FAF5F5;", f"--bg-color: {bg_color};")
    html_content = html_content.replace("--shade-bg: #FFFBFB;", f"--shade-bg: {shade_bg};")
    html_content = html_content.replace("--question-bg: #FFF8F8;", f"--question-bg: {question_bg};")
    html_content = html_content.replace("--border-color: #EBC2C2;", f"--border-color: {border_color};")
    html_content = html_content.replace("--question-text-color: #4A0707;", f"--question-text-color: {question_text_color};")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Generated formatted HTML at: {output_path}")
    
    # Also sync to output directory if output_path is in output_mcq
    secondary_output_dir = os.path.join(os.path.dirname(os.path.dirname(output_path)), "output")
    if os.path.exists(secondary_output_dir):
        secondary_file = os.path.join(secondary_output_dir, os.path.basename(output_path))
        with open(secondary_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Synced formatted HTML to: {secondary_file}")

if __name__ == "__main__":
    import shutil
    # Base directory (where this script lives)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data_mcq")
    OUTPUT_DIR = os.path.join(BASE_DIR, "output_mcq")
    SECONDARY_OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    
    # Ensure output directories exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SECONDARY_OUTPUT_DIR, exist_ok=True)

    # Preset configurations for known files
    file_configs = {
        "أسئلة دورات القلبية.csv": ("medical_questions.html", "Cardiology"),
        "اسئلة دورات الهضمية.csv": ("gastro_questions.html", "Gastroenterology"),
        "أسئلة دورات الصدرية.csv": ("pulmo_questions.html", "Pulmonology"),
        "أسئلة دورات الكلية.csv": ("nephro_questions.html", "Nephrology"),
        "أسئلة دورات الأذنية.csv": ("ent_questions.html", "Otolaryngology"),
        "أسئلة دورات التوليد والنسائية.csv": ("obgyn_questions.html", "Gynecology"),
        "دورات التوليد.csv": ("obs_questions.html", "Obstetrics"),
        "أسئلة دورات الاطفال 1.csv": ("peds_questions.html", "Pediatrics"),
        "أسئلة دورات الاطفال 2.csv": ("peds2_questions.html", "Pediatrics2"),
        "اطفال 2 قلبية2.csv": ("peds_cardio_questions.html", "Cardiology"),
    }

    if os.path.exists(DATA_DIR):
        # Scan for all CSV files in the data directory
        csv_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith('.csv')]
        print(f"Found {len(csv_files)} CSV files in data folder: {DATA_DIR}")
        
        for file in csv_files:
            csv_path = os.path.join(DATA_DIR, file)
            
            # Determine output filename and theme configuration
            if file in file_configs:
                out_name, theme = file_configs[file]
            else:
                # Dynamic mapping for new files!
                clean_name = os.path.splitext(file)[0]
                out_name = f"{clean_name}_questions.html"
                
                # Deduce theme from filename keywords
                if any(kw in file for kw in ["هضمية", "الهضمية", "gastro"]):
                    theme = "Gastroenterology"
                elif any(kw in file for kw in ["صدرية", "الصدرية", "pulmo", "صدر"]):
                    theme = "Pulmonology"
                elif any(kw in file for kw in ["كلية", "الكلية", "nephro"]):
                    theme = "Nephrology"
                elif any(kw in file for kw in ["أذنية", "الأذنية", "أذن", "ent"]):
                    theme = "Otolaryngology"
                elif any(kw in file for kw in ["نسائية", "النسائية", "gyne"]):
                    theme = "Gynecology"
                elif any(kw in file for kw in ["توليد", "التوليد", "obs", "obstetrics"]):
                    theme = "Obstetrics"
                elif any(kw in file for kw in ["اطفال 2", "الاطفال 2", "الأطفال 2", "peds2", "peds_2"]):
                    theme = "Pediatrics2"
                elif any(kw in file for kw in ["اطفال", "الأطفال", "الاطفال", "peds", "pediatrics"]):
                    theme = "Pediatrics"
                else:
                    theme = "Cardiology" # default theme
            
            out_path = os.path.join(OUTPUT_DIR, out_name)
            print(f"Processing {file} -> {out_name} (Theme: {theme})...")
            
            try:
                data = parse_csv(csv_path)
                if data:
                    generate_html(data, out_path, theme_name=theme)
                else:
                    print(f"Warning: No valid data parsed from {file}")
            except Exception as e:
                print(f"Error processing {file}: {e}")
    else:
        print(f"Error: Data directory does not exist at: {DATA_DIR}")
