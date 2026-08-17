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

def chunk_text(text: str, max_chunk_words: int = 250, overlap_words: int = 50) -> List[Dict[str, Any]]:
    """
    Split text into logical chunks.
    Attempts to respect structural legal splits (e.g. sections or paragraph marks).
    """
    text = text.replace("\r\n", "\n")
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

def parse_and_chunk_file(filepath: str, metadata_override: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Parse a file (.txt, .md, .json) and return list of chunk dictionaries with metadata.
    """
    filename = os.path.basename(filepath)
    base_metadata = extract_metadata_from_filename(filename)
    if metadata_override:
        base_metadata.update(metadata_override)
        # Ensure authority level stays in sync if doc_type is overridden
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
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="latin-1") as f:
                content = f.read()
                
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
    """Extract section numbers, article numbers, rule numbers, regulation numbers from text."""
    # Match Articles (e.g. Article 21 or Art. 21)
    article_match = re.search(r'\b(?:Article|Art\.)\s*([A-Za-z0-9\(\)]+)\b', text, re.IGNORECASE)
    if article_match:
        meta["article"] = article_match.group(1)

    # Match Sections (e.g. Section 138 or Sec. 138 or Section 420)
    section_match = re.search(r'\b(?:Section|Sec\.|§)\s*([A-Za-z0-9\(\)]+)\b', text, re.IGNORECASE)
    if section_match:
        meta["section"] = section_match.group(1)

    # Match Regulation (e.g. Regulation 3 or Reg 3)
    reg_match = re.search(r'\b(?:Regulation|Reg\.|Reg)\s*([A-Za-z0-9\(\)]+)\b', text, re.IGNORECASE)
    if reg_match:
        meta["regulation"] = reg_match.group(1)

    # Match Rule (e.g. Rule 4 or Rule 4(1))
    rule_match = re.search(r'\b(?:Rule)\s*([A-Za-z0-9\(\)]+)\b', text, re.IGNORECASE)
    if rule_match:
        meta["rule"] = rule_match.group(1)
