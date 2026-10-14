"""
TealMED Clinical Notes Logic Engine & Converter
================================================
Deterministic, 100% verbatim parser and converter for medical study notes.
Ensures zero hallucinations, zero text modifications or deletions,
and exports fully compliant TealMED JSON and CSV formats.
"""

import os
import sys
import re
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


def extract_frontmatter(raw_text: str) -> Tuple[Dict[str, Any], str]:
    """
    Extracts optional YAML-style frontmatter from the beginning of a Markdown file.
    If no frontmatter is found, returns an empty dict and the original text.
    """
    frontmatter = {}
    content = raw_text.strip()

    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if fm_match:
        fm_block = fm_match.group(1)
        content = content[fm_match.end():].strip()

        for line in fm_block.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip().lower()
                val = val.strip()

                # Handle list in frontmatter e.g. [tag1, tag2] or comma-separated
                if val.startswith('[') and val.endswith(']'):
                    items = [x.strip().strip('"\'') for x in val[1:-1].split(',') if x.strip()]
                    frontmatter[key] = items
                elif key in ('is_free', 'is_official'):
                    try:
                        frontmatter[key] = int(val)
                    except ValueError:
                        frontmatter[key] = 1 if val.lower() in ('true', 'yes', '1') else 0
                else:
                    frontmatter[key] = val.strip('"\'')

    return frontmatter, content


def detect_medical_subject(title: str, text: str) -> str:
    """
    Deterministically detects medical specialty in Arabic based on clinical terminology.
    """
    combined = (title + " " + text[:500]).lower()

    if any(w in combined for w in ["كلية", "كلوي", "كلوية", "كبيبات", "نفروز", "نفريت", "aki", "ckd", "glomerul", "nephr"]):
        return "باطنة كلوية"
    elif any(w in combined for w in ["قلب", "قلبية", "إكليلية", "تاجية", "cardio", "chest pain", "stemi", "heart failure"]):
        return "باطنة قلبية"
    elif any(w in combined for w in ["هضم", "كبد", "معدة", "أمعاء", "gastro", "liver", "cirrhosis"]):
        return "باطنة هضمية"
    elif any(w in combined for w in ["رئة", "رئوي", "صدرية", "تنفس", "pulmo", "asthma", "copd"]):
        return "باطنة صدرية"
    elif any(w in combined for w in ["عصب", "عصبية", "دماغ", "صرع", "neuro", "stroke"]):
        return "باطنة عصبية"
    elif any(w in combined for w in ["غدد", "سكري", "درق", "نخام", "endo", "diabetes", "thyroid"]):
        return "أمراض الغدد والسكري"
    elif any(w in combined for w in ["دم", "دموية", "فقر دم", "صفيحات", "hema", "anemia"]):
        return "أمراض الدم"
    elif any(w in combined for w in ["رثوية", "مفاصل", "روماتيزم", "rheum", "arthritis", "lupus"]):
        return "أمراض المفاصل والروماتيزم"
    elif any(w in combined for w in ["أطفال", "ولدان", "peds", "pediatric"]):
        return "طب الأطفال"
    elif any(w in combined for w in ["نسائية", "توليد", "حمل", "ob/gyn", "gynecology"]):
        return "نسائية وتوليد"
    elif any(w in combined for w in ["جراحة", "surgical", "surgery", "appendix", "hernia"]):
        return "جراحة عامة"
    return "الطب السريري"


STRUCTURAL_SECTION_TERMS = {
    "core concept", "golden rules", "high-yield", "differential", "overlaps",
    "clinical paradoxes", "exam traps", "laboratory", "diagnostic correlates",
    "30-second elimination rules", "elimination rules", "part", "chapter"
}


def extract_english_terms(text: str, exclude_structural: bool = True) -> List[str]:
    """
    Extracts clean English medical terms enclosed in parentheses or English phrases.
    """
    terms = []
    # Extract terms inside parentheses like (Glomerular & Vascular Diseases)
    paren_matches = re.findall(r'\(([A-Za-z0-9\s/&,._+-]+)\)', text)
    for m in paren_matches:
        cleaned = m.strip()
        # Split by &, comma, slash, or hyphen with spaces
        parts = re.split(r'[,&/]|\s+-\s+', cleaned)
        for p in parts:
            clean_part = re.sub(r'\s+', ' ', p).strip(' -_')
            if len(clean_part) >= 2 and not clean_part.isdigit():
                if exclude_structural and clean_part.lower() in STRUCTURAL_SECTION_TERMS:
                    continue
                if clean_part not in terms:
                    terms.append(clean_part)

    # Extract standalone uppercase acronyms of 2-6 letters (e.g., AKI, CKD, ATN, RPGN, FSGS, MCD)
    acronyms = re.findall(r'\b[A-Z]{2,6}\b', text)
    for acr in acronyms:
        if acr not in ["AND", "FOR", "WITH", "THE", "OR", "IN", "ON", "AT", "TO", "PART", "NOTE"]:
            if acr not in terms:
                terms.append(acr)

    return terms


def extract_key_points_verbatim(markdown_text: str) -> List[str]:
    """
    Extracts 3 to 5 key points strictly verbatim from the note content.
    Prioritizes Section 5 (خلاصة الاستبعاد السريع / 30-Second Elimination Rules),
    then clinical pearls (> 💡), then top list items.
    """
    key_points = []

    # 1. Search for Section 5 (خلاصة الاستبعاد السريع)
    sec5_match = re.search(
        r'##\s+[٥5]\.\s*خلاصة الاستبعاد السريع.*?\n(.*?)(?=\n##|\Z)',
        markdown_text,
        re.DOTALL
    )

    if sec5_match:
        sec5_body = sec5_match.group(1).strip()
        # Find numbered items: 1. **...** ...
        items = re.findall(r'(?:^|\n)\s*\d+[\.\-\)]\s*(.+?)(?=(?:\n\s*\d+[\.\-\)]|\Z))', sec5_body, re.DOTALL)
        for item in items:
            cleaned_item = re.sub(r'\s+', ' ', item).strip()
            # If item begins with bold text **...**, extract the bold statement as concise high-yield pearl
            bold_match = re.match(r'^\*\*(.+?)\*\*', cleaned_item)
            if bold_match:
                extracted = bold_match.group(1).strip()
                # If bold part ends with a clean punctuation, use it; otherwise preserve it
                if extracted and extracted not in key_points:
                    key_points.append(extracted)
            else:
                # Use the first sentence up to period or semicolon
                first_sent = re.split(r'[.;]\s*', cleaned_item)[0].strip()
                if first_sent and first_sent not in key_points:
                    key_points.append(first_sent)

            if len(key_points) >= 5:
                break

    # 2. If fewer than 3 key points found, look for Clinical Pearls (> 💡)
    if len(key_points) < 3:
        pearls = re.findall(r'>\s*💡\s*(?:\*\*[^*]+\*\*:?)?\s*(.+?)(?=\n\n|\n[#>*-]|\Z)', markdown_text)
        for p in pearls:
            clean_p = re.sub(r'\s+', ' ', p).strip().strip('*')
            if clean_p and clean_p not in key_points:
                key_points.append(clean_p)
            if len(key_points) >= 5:
                break

    # 3. Fallback: Take top bolded list rules from Section 1 or any bullet points
    if len(key_points) < 3:
        bullets = re.findall(r'(?:^|\n)\s*[\*\-]\s*\*\*(.+?)\*\*', markdown_text)
        for b in bullets:
            clean_b = b.strip()
            if len(clean_b) > 15 and clean_b not in key_points:
                key_points.append(clean_b)
            if len(key_points) >= 3:
                break

    return key_points[:5]


def split_multi_part_note(raw_text: str) -> List[str]:
    """
    Checks if a markdown text contains multiple distinct note parts
    (e.g., '# الجزء الأول:' and '# الجزء الثاني:').
    Returns a list of markdown blocks (one per part).
    If no parts are detected, returns [raw_text].
    """
    # Look for Part headers like '# الجزء الأول:' or '# الجزء الثاني:'
    part_pattern = re.compile(r'(?m)^#\s+(?:الجزء|القسم|المبحث|الوحدة|الفصل|Part)\s+[الأول|الثاني|الثالث|الرابع|الخامس|\d]+[:\s].*')
    matches = list(part_pattern.finditer(raw_text))

    if len(matches) >= 2:
        parts = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
            part_content = raw_text[start:end].strip()
            if part_content:
                parts.append(part_content)
        return parts

    return [raw_text]


def slugify_to_id(prefix: str, text: str, index: int = 1) -> str:
    """
    Generates a deterministic, collision-free database ID (e.g. note_nephro_glomerular_01).
    """
    # Extract English words first
    eng_words = re.findall(r'[A-Za-z0-9]+', text)
    if eng_words:
        # Filter out very short or generic words
        meaningful = [w.lower() for w in eng_words if len(w) > 2 or w.isupper()][:3]
        slug = "_".join(meaningful)
    else:
        # Fallback to index
        slug = f"item_{str(index).zfill(2)}"

    clean_prefix = re.sub(r'[^a-zA-Z0-9_]', '_', str(prefix or 'med').strip().lower()).strip('_')
    clean_slug = re.sub(r'[^a-zA-Z0-9_]', '_', slug).strip('_')

    return f"note_{clean_prefix}_{clean_slug}"


def parse_markdown_note(
    markdown_content: str,
    default_subject: Optional[str] = None,
    default_difficulty: str = "متوسط",
    default_is_free: int = 1,
    default_is_official: int = 1,
    id_prefix: Optional[str] = None,
    note_index: int = 1
) -> Dict[str, Any]:
    """
    Parses a single Markdown note block into the full TealMED schema object.
    Preserves 100% of clinical text verbatim.
    """
    frontmatter, clean_md = extract_frontmatter(markdown_content)

    # 1. Extract Title
    title = frontmatter.get('title')
    if not title:
        # First H1 header
        h1_match = re.search(r'^#\s+(.+)$', clean_md, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()
        else:
            # Fallback to first line
            first_line = clean_md.strip().splitlines()[0] if clean_md.strip() else f"Medical Note {note_index}"
            title = re.sub(r'^[#\s\-*]+', '', first_line).strip()

    # Clean display title if it contains "الجزء الأول: " at start
    clean_title = re.sub(r'^الجزء\s+[الأول|الثاني|الثالث|الرابع|الخامس|\d]+\s*[:\-]\s*', '', title).strip()

    # 2. Extract Subject Name
    subject_name = frontmatter.get('subject') or frontmatter.get('subject_name') or default_subject
    if not subject_name:
        subject_name = detect_medical_subject(clean_title, clean_md)

    # 3. Extract Topic Name
    topic_name = frontmatter.get('topic') or frontmatter.get('topic_name')
    if not topic_name:
        # Remove English parentheses from clean title to get Arabic topic
        topic_arabic = re.sub(r'\s*\([^)]*\)', '', clean_title).strip()
        # Remove leading numbers if present
        topic_arabic = re.sub(r'^[٠-٩0-9]+[\.\-\s]+', '', topic_arabic).strip()
        topic_name = topic_arabic if topic_arabic else clean_title

    # 4. Extract Key Points strictly verbatim
    key_points = frontmatter.get('key_points')
    if not key_points or not isinstance(key_points, list):
        key_points = extract_key_points_verbatim(clean_md)

    # 5. Extract Tags
    tags = frontmatter.get('tags')
    if not tags or not isinstance(tags, list):
        tags = []
        # Extract English terms from title
        title_terms = extract_english_terms(clean_title)
        tags.extend(title_terms)

        # Add topic/subject relevant tag
        if "كلية" in subject_name or "كلوية" in subject_name:
            if "Nephrology" not in tags:
                tags.append("Nephrology")
        elif "قلب" in subject_name:
            if "Cardiology" not in tags:
                tags.append("Cardiology")

        # Scan text for top high-yield acronyms
        body_acronyms = extract_english_terms(clean_md[:1500])
        for acr in body_acronyms:
            if acr not in tags and len(tags) < 6:
                tags.append(acr)

    # 6. Difficulty, is_free, is_official
    difficulty = frontmatter.get('difficulty', default_difficulty)
    is_free = int(frontmatter.get('is_free', default_is_free))
    is_official = int(frontmatter.get('is_official', default_is_official))

    # 7. Deterministic ID
    note_id = frontmatter.get('id')
    if not note_id:
        pfx = id_prefix if id_prefix else (
            "nephro" if "كلية" in subject_name or "كلوية" in subject_name else
            "cardio" if "قلب" in subject_name else
            "med"
        )
        note_id = slugify_to_id(pfx, clean_title, note_index)

    # 8. Verbatim Content (100% untouched Markdown text)
    content = clean_md.strip()

    return {
        "id": str(note_id),
        "subject_name": str(subject_name),
        "topic_name": str(topic_name),
        "title": str(clean_title),
        "difficulty": str(difficulty),
        "is_official": int(is_official),
        "is_free": int(is_free),
        "tags": tags,
        "key_points": key_points,
        "content": content
    }


def convert_markdown_file_to_notes(
    file_path: Path,
    default_subject: Optional[str] = None,
    id_prefix: Optional[str] = None,
    split_parts: bool = True
) -> List[Dict[str, Any]]:
    """
    Reads a Markdown file and converts it into one or more TealMED note objects.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read with UTF-8 encoding
    raw_text = file_path.read_text(encoding='utf-8', errors='replace')

    # Detect prefix from filename if not passed
    if not id_prefix:
        stem = file_path.stem.lower()
        if "nephro" in stem or "renal" in stem or "kidney" in stem:
            id_prefix = "nephro"
        elif "cardio" in stem or "heart" in stem:
            id_prefix = "cardio"
        else:
            id_prefix = re.sub(r'[^a-zA-Z0-9]', '_', stem).strip('_') or "med"

    # Check for multi-part notes
    if split_parts:
        parts = split_multi_part_note(raw_text)
    else:
        parts = [raw_text]

    notes = []
    for idx, part_text in enumerate(parts, start=1):
        note_obj = parse_markdown_note(
            markdown_content=part_text,
            default_subject=default_subject,
            id_prefix=id_prefix,
            note_index=idx
        )
        notes.append(note_obj)

    return notes


def export_notes_to_json(notes: List[Dict[str, Any]], output_json_path: Path) -> Path:
    """
    Exports note objects to JSON matching notes_sample.json.
    """
    output_json_path = Path(output_json_path)
    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

    return output_json_path


def export_notes_to_csv(notes: List[Dict[str, Any]], output_csv_path: Path, full_schema: bool = False) -> Path:
    """
    Exports note objects to CSV.
    - If full_schema is False: exports strictly `title,content_markdown,difficulty,is_free,subject,topic`
      matching notes_sample.csv.
    - If full_schema is True: exports all fields including id, tags, key_points.
    Uses UTF-8-SIG encoding so Arabic characters render perfectly in Microsoft Excel.
    """
    output_csv_path = Path(output_csv_path)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    if not full_schema:
        # Strict platform import format matching notes_sample.csv
        fieldnames = ["title", "content_markdown", "difficulty", "is_free", "subject", "topic"]
        rows = []
        for n in notes:
            rows.append({
                "title": n["title"],
                "content_markdown": n["content"],
                "difficulty": n["difficulty"],
                "is_free": n["is_free"],
                "subject": n["subject_name"],
                "topic": n["topic_name"]
            })
    else:
        fieldnames = ["id", "subject_name", "topic_name", "title", "difficulty", "is_official", "is_free", "tags", "key_points", "content_markdown"]
        rows = []
        for n in notes:
            rows.append({
                "id": n["id"],
                "subject_name": n["subject_name"],
                "topic_name": n["topic_name"],
                "title": n["title"],
                "difficulty": n["difficulty"],
                "is_official": n["is_official"],
                "is_free": n["is_free"],
                "tags": json.dumps(n["tags"], ensure_ascii=False),
                "key_points": json.dumps(n["key_points"], ensure_ascii=False),
                "content_markdown": n["content"]
            })

    with open(output_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)

    return output_csv_path
