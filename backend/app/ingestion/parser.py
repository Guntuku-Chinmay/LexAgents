import re
import os
import json
import uuid
import datetime
from typing import List, Dict, Any

# Source Tiers definition
AUTHORITY_TIERS = {
    "constitutional": "TIER 1",
    "constitutional_amendment": "TIER 1",
    "central_act": "TIER 2",
    "state_act": "TIER 2",
    "sc_judgment": "TIER 2",
    "hc_judgment": "TIER 2",
    "rules": "TIER 3",
    "regulation": "TIER 3",
    "government_notification": "TIER 3",
    "government_order": "TIER 3",
    "government_circular": "TIER 3",
    "user_upload": "TIER 4",
    "external_source": "TIER 4",
    "unknown": "TIER 4"
}

def extract_metadata_from_filename(filename: str) -> Dict[str, Any]:
    """
    Extract comprehensive Indian legal metadata from filenames based on common naming patterns.
    """
    basename = os.path.splitext(filename)[0]
    metadata = {
        "filename": filename,
        "title": basename.replace("_", " ").title(),
        "doc_type": "unknown",
        "jurisdiction": "IN",
        "authority_level": "TIER 4",
        "issuing_authority": "Government of India",
        "court": None,
        "court_level": None,
        "case_name": None,
        "case_citation": None,
        "act_name": None,
        "article": None,
        "section": None,
        "subsection": None,
        "rule": None,
        "regulation": None,
        "notification_number": None,
        "publication_date": None,
        "judgment_date": None,
        "effective_from": None,
        "effective_to": None,
        "amendment_status": "Current",
        "current_status": "Active",
        "source_url": None,
        "official_source": True,
        "ingestion_timestamp": datetime.datetime.utcnow().isoformat()
    }

    # Case law check (Supreme Court / High Court)
    if "_v_" in filename.lower() or "_vs_" in filename.lower():
        metadata["case_name"] = basename.replace("_", " ").title()
        metadata["case_name"] = re.sub(r'\bVs\b|\bV\b', "v.", metadata["case_name"], flags=re.IGNORECASE)
        
        parts = basename.split("_")
        year = None
        if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 4:
            year = parts[-1]
            metadata["judgment_date"] = f"{year}-01-01"
            metadata["publication_date"] = f"{year}-01-01"

        if "delhi_hc" in filename.lower() or "_hc_" in filename.lower():
            metadata["doc_type"] = "hc_judgment"
            metadata["court"] = "High Court of Delhi" if "delhi" in filename.lower() else "High Court"
            metadata["court_level"] = "High Court"
            metadata["jurisdiction"] = "Delhi" if "delhi" in filename.lower() else "State"
            if year:
                metadata["case_citation"] = f"({year}) Delhi HC 101"
        else:
            metadata["doc_type"] = "sc_judgment"
            metadata["court"] = "Supreme Court of India"
            metadata["court_level"] = "Supreme Court"
            metadata["jurisdiction"] = "IN"
            if year:
                metadata["case_citation"] = f"({year}) SEC SC 42"

    # Constitution check
    elif "constitution" in filename.lower():
        if "amendment" in filename.lower():
            metadata["doc_type"] = "constitutional_amendment"
            metadata["title"] = "Constitution Amendment Act"
            # Try matching number
            match = re.search(r'amendment_(\d+)', filename.lower())
            if match:
                metadata["title"] = f"Constitution ({match.group(1)}th Amendment) Act"
        else:
            metadata["doc_type"] = "constitutional"
            metadata["title"] = "Constitution of India, 1950"
            metadata["issuing_authority"] = "Constituent Assembly of India"

    # Regulations check
    elif "regulation" in filename.lower() or "sebi" in filename.lower():
        metadata["doc_type"] = "regulation"
        metadata["title"] = "SEBI Regulations"
        metadata["issuing_authority"] = "SEBI"
        if "insider" in filename.lower():
            metadata["title"] = "SEBI (Prohibition of Insider Trading) Regulations, 2015"
            metadata["publication_date"] = "2015-01-15"

    # Circulars / Guidelines check
    elif "circular" in filename.lower() or "guidelines" in filename.lower() or "rbi" in filename.lower():
        metadata["doc_type"] = "government_circular"
        metadata["title"] = "RBI Digital Lending Guidelines"
        metadata["issuing_authority"] = "RBI"
        if "digital_lending" in filename.lower():
            metadata["title"] = "Guidelines on Digital Lending (RBI)"
            metadata["publication_date"] = "2022-09-02"

    # Acts check
    elif "act" in filename.lower() or "code" in filename.lower():
        metadata["doc_type"] = "central_act"
        metadata["title"] = basename.replace("_", " ").title()
        if "penal" in filename.lower() or "ipc" in filename.lower():
            metadata["title"] = "Indian Penal Code, 1860"
            metadata["publication_date"] = "1860-10-06"
        elif "negotiable" in filename.lower() or "ni_act" in filename.lower():
            metadata["title"] = "Negotiable Instruments Act, 1881"
            metadata["publication_date"] = "1881-12-09"

    # Custom contract / User Upload
    else:
        metadata["doc_type"] = "user_upload"
        metadata["official_source"] = False
        metadata["issuing_authority"] = "Contracting Parties"

    # Assign Tier
    metadata["authority_level"] = AUTHORITY_TIERS.get(metadata["doc_type"], "TIER 4")
    return metadata

# Strict legal identifier regexes
ARTICLE_PATTERN = re.compile(
    r'\b(?:Article|Art\.|अनुच्छेद|ఆర్టికల్|నిబంధన)\s*(\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*|\b[IVXLCDM]+\b)',
    re.IGNORECASE
)
SECTION_PATTERN = re.compile(
    r'\b(?:Section|Sec\.|§|धारा|సెక్షన్|విభాగం)\s*(\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*|\b[IVXLCDM]+\b)',
    re.IGNORECASE
)
REGULATION_PATTERN = re.compile(
    r'\b(?:Regulation|Reg\.|विनियमन|రెగ్యులేషన్)\s*(\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*)(?=[^0-9a-zA-Z(]|$)',
    re.IGNORECASE
)
RULE_PATTERN = re.compile(
    r'\b(?:Rule|नियम|రూల్)\s*(\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*)(?=[^0-9a-zA-Z(]|$)',
    re.IGNORECASE
)
PARAGRAPH_PATTERN = re.compile(
    r'\b(?:Paragraph|Para\.)\s*(\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*)(?=[^0-9a-zA-Z(]|$)',
    re.IGNORECASE
)
CLAUSE_PATTERN = re.compile(
    r'\b(?:Clause)\s*(\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*)(?=[^0-9a-zA-Z(]|$)',
    re.IGNORECASE
)
STRUCTURAL_BOUNDARY_PATTERN = re.compile(
    r'(?m)^(?=(?:Article|Art\.|अनुच्छेद|ఆర్టికల్|Section|Sec\.|§|धारा|సెక్షన్|Regulation|Reg\.|Rule|Paragraph|Para\.|Clause)\s*\d+|CONSTITUTION\s*\([^)]*\)\s*ACT|THE\s+[A-Z\s,]+ACT)',
    re.IGNORECASE
)

def chunk_text(text: str, max_chunk_words: int = 350, overlap_words: int = 40) -> List[Dict[str, Any]]:
    """
    Split text into logical legal chunks.
    Preserves structural legal boundaries (Articles, Sections, Regulations, Rules, Clauses).
    Falls back to paragraph-level chunking when structural markers are absent.
    """
    text = text.replace("\r\n", "\n")
    
    # Check if document has structural legal boundaries
    has_structural_splits = bool(STRUCTURAL_BOUNDARY_PATTERN.search(text))
    
    if has_structural_splits:
        raw_sections = [s.strip() for s in STRUCTURAL_BOUNDARY_PATTERN.split(text) if s.strip()]
        chunks = []
        preamble = ""
        
        for sec in raw_sections:
            has_provision = (
                ARTICLE_PATTERN.search(sec) or 
                SECTION_PATTERN.search(sec) or 
                REGULATION_PATTERN.search(sec) or
                RULE_PATTERN.search(sec) or
                PARAGRAPH_PATTERN.search(sec) or
                CLAUSE_PATTERN.search(sec)
            )
            
            # If leading preamble without provisions, store to prepend to first provision
            if not has_provision and len(sec.split()) < 40 and not chunks:
                preamble = sec
                continue
                
            chunk_content = f"{preamble}\n\n{sec}".strip() if preamble else sec
            preamble = ""
            
            sec_words = chunk_content.split()
            if len(sec_words) <= max_chunk_words:
                chunks.append(chunk_content)
            else:
                # Split large provision across paragraphs
                para_splits = chunk_content.split("\n\n")
                current_sub = []
                for p in para_splits:
                    p = p.strip()
                    if not p:
                        continue
                    p_words = p.split()
                    if len(current_sub) + len(p_words) > max_chunk_words:
                        if current_sub:
                            chunks.append(" ".join(current_sub))
                            current_sub = []
                    current_sub.extend(p_words)
                if current_sub:
                    chunks.append(" ".join(current_sub))
        
        if chunks:
            return [{"text": c, "id": str(uuid.uuid4())} for c in chunks]

    # Standard paragraph-based fallback
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk_words = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        para_words = para.split()
        if not para_words:
            continue
            
        if len(para_words) > max_chunk_words:
            if current_chunk_words:
                chunks.append(" ".join(current_chunk_words))
                current_chunk_words = []
                
            for i in range(0, len(para_words), max_chunk_words - overlap_words):
                slice_words = para_words[i : i + max_chunk_words]
                chunks.append(" ".join(slice_words))
        else:
            if len(current_chunk_words) + len(para_words) > max_chunk_words:
                chunks.append(" ".join(current_chunk_words))
                overlap_start = max(0, len(current_chunk_words) - overlap_words)
                current_chunk_words = current_chunk_words[overlap_start:]
            
            current_chunk_words.extend(para_words)

    if current_chunk_words:
        chunks.append(" ".join(current_chunk_words))
        
    return [{"text": c, "id": str(uuid.uuid4())} for c in chunks]

def parse_constitution_hierarchy(content: str, base_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse authoritative Constitution of India text into a structured legal hierarchy:
    - Preamble
    - Parts I through XXII
    - Articles 1 through 395 (including sub-articles 21A, 31A, 39A, 43A, 43B, 48A, 51A, 243-series, 300A, etc.)
    - Clause and sub-clause splitting for long articles
    - Schedules 1 through 12 (with List I, II, III for Seventh Schedule)
    Strictly validates identifiers: no prose words, no years as article numbers.
    """
    chunks = []
    
    # 1. Preamble
    p_match = re.search(r'PREAMBLE\s*\n\s*(.*?)(?=\n\s*PART\s+I\b)', content, re.DOTALL | re.IGNORECASE)
    if p_match:
        p_text = p_match.group(1).strip()
        p_meta = base_meta.copy()
        p_meta.update({
            "part": "PREAMBLE",
            "article": None,
            "parent_article": None,
            "clause": None,
            "sub_clause": None,
            "schedule": None,
            "primary_article": None,
            "articles": []
        })
        chunks.append({
            "id": str(uuid.uuid4()),
            "text": f"THE CONSTITUTION OF INDIA\n\nPREAMBLE\n\n{p_text}",
            "metadata": p_meta
        })
        
    # Split text into Articles zone and Schedules zone
    delimiter = "========================================\nSCHEDULES OF THE CONSTITUTION OF INDIA\n========================================"
    if delimiter in content:
        art_zone, sched_zone = content.split(delimiter, 1)
    else:
        sched_start_match = re.search(r'(?:\n|\A)\s*(?:\[?\d*\]?\s*)?FIRST\s+SCHEDULE\b', content, re.IGNORECASE)
        if sched_start_match:
            art_zone = content[:sched_start_match.start()]
            sched_zone = content[sched_start_match.start():]
        else:
            art_zone = content
            sched_zone = ""
            
    # 2. Parts & Articles
    part_pattern = re.compile(r'(?:^|\n)\s*PART\s+([IVXLCDM]+[A-Z]?)\s*\n([^\n]+)', re.MULTILINE)
    parts_pos = []
    for m in part_pattern.finditer(art_zone):
        parts_pos.append((m.start(), m.group(1).upper(), m.group(2).strip()))

    def get_part_for_pos(pos):
        current_part = "PART I: THE UNION AND ITS TERRITORY"
        for p_start, p_num, p_title in parts_pos:
            if pos >= p_start:
                current_part = f"PART {p_num}: {p_title}"
            else:
                break
        return current_part

    art_reg = re.compile(r'(?:^|\n)\s*(?:(?:\[|\d+\[|\[\d+\])\s*)?(\d+[A-Z]?)\.\s*(?:(?:\[|\d+\[|\[\d+\])\s*)?(\[?[A-Z][^\n]+)')
    
    matches = []
    for m in art_reg.finditer(art_zone):
        num = m.group(1).upper()
        title_line = m.group(2).strip()
        
        m_val = re.match(r'^(\d+)', num)
        if not m_val:
            continue
        val = int(m_val.group(1))
        # Strict validation: article must be 1 to 395, and not a year
        if val < 1 or val > 395 or val in [1950, 1976, 2016]:
            continue
            
        first_word = title_line.split()[0].lower().rstrip('.,:;[]-')
        PROSE_WORDS = {"has", "the", "provides", "shall", "subs", "ins", "omitted", "added", "see", "for", "in", "by", "that", "this", "and", "or", "clause"}
        if first_word in PROSE_WORDS:
            continue
            
        matches.append((m.start(), num, title_line))
        
    for i in range(len(matches)):
        start_pos = matches[i][0]
        end_pos = matches[i+1][0] if i + 1 < len(matches) else len(art_zone)
        num = matches[i][1]
        raw_content = art_zone[start_pos:end_pos].strip()
        part = get_part_for_pos(start_pos)
        
        # Clause splitting for articles with multiple numbered clauses (1), (2), (3)...
        clause_regex = re.compile(r'(?:^|\n|\s*—\s*|\.\s*)(?:(?:\[|\d+\[|\[\d+\]|\d+\[\d+\]|\d+)\s*)?\((\d+[A-Z]?)\)\s+', re.MULTILINE)
        c_matches = list(clause_regex.finditer(raw_content))
        
        if c_matches and len(c_matches) > 1:
            for ci in range(len(c_matches)):
                c_num = c_matches[ci].group(1)
                c_start = c_matches[ci].start()
                c_end = c_matches[ci+1].start() if ci + 1 < len(c_matches) else len(raw_content)
                c_body = raw_content[c_start:c_end].strip()
                c_body_clean = re.sub(r'^.*?\((\d+[A-Z]?)\)', r'(\1)', c_body).strip()
                
                sub_clauses = re.findall(r'\(([a-z])\)', c_body_clean)
                
                c_meta = base_meta.copy()
                c_meta.update({
                    "part": part,
                    "article": num,
                    "parent_article": num,
                    "clause": c_num,
                    "sub_clause": sub_clauses[0] if sub_clauses else None,
                    "sub_clauses": sub_clauses,
                    "schedule": None,
                    "primary_article": num,
                    "articles": [num, f"{num}({c_num})"]
                })
                
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "text": f"Article {num}({c_num}). {c_body_clean}",
                    "metadata": c_meta
                })
        else:
            sub_clauses = re.findall(r'\(([a-z])\)', raw_content)
            a_meta = base_meta.copy()
            a_meta.update({
                "part": part,
                "article": num,
                "parent_article": num,
                "clause": None,
                "sub_clause": sub_clauses[0] if sub_clauses else None,
                "sub_clauses": sub_clauses,
                "schedule": None,
                "primary_article": num,
                "articles": [num]
            })
            chunks.append({
                "id": str(uuid.uuid4()),
                "text": f"Article {num}. {raw_content}",
                "metadata": a_meta
            })
            
    # 3. Schedules
    sched_pattern = re.compile(
        r'(?:^|\n)\s*(?:(?:\[|\d+\[|\[\d+\])\s*)?((?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH)\s+SCHEDULE)\b([^\n]*)',
        re.MULTILINE
    )
    s_matches = list(sched_pattern.finditer(sched_zone))
    
    for i in range(len(s_matches)):
        start_pos = s_matches[i].start()
        end_pos = s_matches[i+1].start() if i + 1 < len(s_matches) else len(sched_zone)
        s_name = s_matches[i].group(1).upper()
        s_title_extra = s_matches[i].group(2).strip()
        s_content = sched_zone[start_pos:end_pos].strip()
        
        if any(k in s_title_extra.lower() for k in ["to the", "of the", "specified in", "omitted by"]):
            continue
            
        if s_name == "SEVENTH SCHEDULE":
            list_pat = re.compile(r'(?:^|\n)\s*(List\s+[I|V|X]+[^\n]*)', re.IGNORECASE)
            l_matches = list(list_pat.finditer(s_content))
            if l_matches:
                for li in range(len(l_matches)):
                    l_start = l_matches[li].start()
                    l_end = l_matches[li+1].start() if li + 1 < len(l_matches) else len(s_content)
                    l_title = l_matches[li].group(1).strip()
                    l_body = s_content[l_start:l_end].strip()
                    
                    s_meta = base_meta.copy()
                    s_meta.update({
                        "part": "SCHEDULES",
                        "article": None,
                        "parent_article": None,
                        "clause": None,
                        "sub_clause": None,
                        "schedule": "SEVENTH SCHEDULE",
                        "schedule_list": l_title,
                        "primary_article": None,
                        "articles": []
                    })
                    chunks.append({
                        "id": str(uuid.uuid4()),
                        "text": f"SEVENTH SCHEDULE — {l_title}\n\n{l_body}",
                        "metadata": s_meta
                    })
                continue
                
        if len(s_content) > 3000:
            paragraphs = s_content.split("\n\n")
            curr_text = []
            part_idx = 1
            for p in paragraphs:
                curr_text.append(p)
                if sum(len(x) for x in curr_text) >= 2000:
                    s_meta = base_meta.copy()
                    s_meta.update({
                        "part": "SCHEDULES",
                        "article": None,
                        "parent_article": None,
                        "clause": None,
                        "sub_clause": None,
                        "schedule": s_name,
                        "schedule_part": f"Part {part_idx}",
                        "primary_article": None,
                        "articles": []
                    })
                    chunks.append({
                        "id": str(uuid.uuid4()),
                        "text": f"{s_name} (Part {part_idx})\n\n" + "\n\n".join(curr_text),
                        "metadata": s_meta
                    })
                    curr_text = []
                    part_idx += 1
            if curr_text:
                s_meta = base_meta.copy()
                s_meta.update({
                    "part": "SCHEDULES",
                    "article": None,
                    "parent_article": None,
                    "clause": None,
                    "sub_clause": None,
                    "schedule": s_name,
                    "schedule_part": f"Part {part_idx}",
                    "primary_article": None,
                    "articles": []
                })
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "text": f"{s_name} (Part {part_idx})\n\n" + "\n\n".join(curr_text),
                    "metadata": s_meta
                })
        else:
            s_meta = base_meta.copy()
            s_meta.update({
                "part": "SCHEDULES",
                "article": None,
                "parent_article": None,
                "clause": None,
                "sub_clause": None,
                "schedule": s_name,
                "primary_article": None,
                "articles": []
            })
            chunks.append({
                "id": str(uuid.uuid4()),
                "text": f"{s_name}\n\n{s_content}",
                "metadata": s_meta
            })
            
    return chunks

def parse_and_chunk_file(filepath: str, metadata_override: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Parse a file (.txt, .md, .json) and return list of chunk dictionaries with metadata.
    """
    filename = os.path.basename(filepath)
    base_metadata = extract_metadata_from_filename(filename)
    if metadata_override:
        base_metadata.update(metadata_override)
        if "doc_type" in metadata_override:
            base_metadata["authority_level"] = AUTHORITY_TIERS.get(metadata_override["doc_type"], "TIER 4")
        
    ext = os.path.splitext(filename)[1].lower()
    chunks_with_metadata = []
    
    if ext == ".json":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if isinstance(data, list):
            for idx, item in enumerate(data):
                text = item.get("text", "")
                item_meta = base_metadata.copy()
                item_meta.update(item.get("metadata", {}))
                
                sub_chunks = chunk_text(text)
                for sc in sub_chunks:
                    meta = item_meta.copy()
                    _extract_inline_identifiers(sc["text"], meta)
                    chunks_with_metadata.append({
                        "id": sc["id"],
                        "text": sc["text"],
                        "metadata": meta
                    })
        elif isinstance(data, dict):
            text = data.get("text", "")
            doc_meta = base_metadata.copy()
            doc_meta.update(data.get("metadata", {}))
            sub_chunks = chunk_text(text)
            for sc in sub_chunks:
                meta = doc_meta.copy()
                _extract_inline_identifiers(sc["text"], meta)
                chunks_with_metadata.append({
                    "id": sc["id"],
                    "text": sc["text"],
                    "metadata": meta
                })
    else:
        # Load companion metadata JSON if available
        meta_json_path = os.path.splitext(filepath)[0] + ".meta.json"
        if os.path.exists(meta_json_path):
            try:
                with open(meta_json_path, "r", encoding="utf-8") as mf:
                    comp_meta = json.load(mf)
                    base_metadata.update(comp_meta)
            except Exception:
                pass

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="latin-1") as f:
                content = f.read()

        # Check if this is the complete Constitution of India
        if base_metadata.get("doc_type") == "constitutional" or "constitution" in filename.lower():
            if "PART I" in content or "PREAMBLE" in content:
                return parse_constitution_hierarchy(content, base_metadata)
                
        sub_chunks = chunk_text(content)
        for sc in sub_chunks:
            meta = base_metadata.copy()
            _extract_inline_identifiers(sc["text"], meta)
            chunks_with_metadata.append({
                "id": sc["id"],
                "text": sc["text"],
                "metadata": meta
            })
            
    return chunks_with_metadata

def _extract_inline_identifiers(text: str, meta: Dict[str, Any]):
    """Strictly extract legal identifiers without false positives on English prose."""
    # 1. Articles
    articles = []
    for m in ARTICLE_PATTERN.finditer(text):
        val = m.group(1).strip()
        if val and val not in articles:
            articles.append(val)
    primary_article = articles[0] if articles else None

    # 2. Sections
    sections = []
    for m in SECTION_PATTERN.finditer(text):
        val = m.group(1).strip()
        if val and val not in sections:
            sections.append(val)
    primary_section = sections[0] if sections else None

    # 3. Regulations (excluding 4-digit years like Regulations, 2015)
    regulations = []
    for m in REGULATION_PATTERN.finditer(text):
        val = m.group(1).strip()
        if val and val.isdigit() and len(val) == 4 and int(val) in range(1900, 2100):
            continue
        if val and val not in regulations:
            regulations.append(val)
    primary_regulation = regulations[0] if regulations else None

    # 4. Rules
    rules = []
    for m in RULE_PATTERN.finditer(text):
        val = m.group(1).strip()
        if val and val not in rules:
            rules.append(val)
    primary_rule = rules[0] if rules else None

    # 5. Paragraphs
    paragraphs = []
    for m in PARAGRAPH_PATTERN.finditer(text):
        val = m.group(1).strip()
        if val and val not in paragraphs:
            paragraphs.append(val)
    primary_para = paragraphs[0] if paragraphs else None

    # Populate metadata preserving backward compatibility
    meta["article"] = primary_article
    meta["primary_article"] = primary_article
    meta["articles"] = articles

    meta["section"] = primary_section
    meta["primary_section"] = primary_section
    meta["sections"] = sections

    meta["regulation"] = primary_regulation
    meta["primary_regulation"] = primary_regulation
    meta["regulations"] = regulations

    meta["rule"] = primary_rule
    meta["primary_rule"] = primary_rule
    meta["rules"] = rules

    meta["paragraph"] = primary_para
    meta["primary_paragraph"] = primary_para
    meta["paragraphs"] = paragraphs
