import re
import os
import json
import uuid
from typing import List, Dict, Any

def extract_metadata_from_filename(filename: str) -> Dict[str, Any]:
    """Extract basic legal metadata from filenames based on common naming patterns."""
    basename = os.path.splitext(filename)[0]
    metadata = {
        "filename": filename,
        "title": basename.replace("_", " ").title(),
        "doc_type": "unknown",
        "jurisdiction": "US"  # default
    }

    # Case law check
    # e.g., Brown_v_Board_of_Education_1954.txt
    if "_v_" in filename.lower() or "_vs_" in filename.lower():
        metadata["doc_type"] = "case"
        parts = basename.split("_")
        # Extract date/year if last part is 4 digits
        if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 4:
            metadata["date"] = f"{parts[-1]}-01-01"
            metadata["case_name"] = " v. ".join(" ".join(parts[:-1]).split(" v "))
        else:
            metadata["case_name"] = basename.replace("_", " ")
        
        # Infer court (standard fallbacks)
        if "supreme" in filename.lower():
            metadata["court"] = "Supreme Court of the United States"
        elif "circuit" in filename.lower():
            metadata["court"] = "US Court of Appeals"
        else:
            metadata["court"] = "US District Court"

    # Statute check
    # e.g., US_Code_Title_11_Bankruptcy.txt
    elif "statute" in filename.lower() or "code" in filename.lower() or "act" in filename.lower():
        metadata["doc_type"] = "statute"
        metadata["court"] = "Legislature"
        # Match common title/section codes
        match = re.search(r'title_(\d+)', filename.lower())
        if match:
            metadata["title"] = f"U.S. Code Title {match.group(1)}"
    
    # Custom/uploaded legal doc
    else:
        metadata["doc_type"] = "user_upload"

    return metadata

def chunk_text(text: str, max_chunk_words: int = 250, overlap_words: int = 50) -> List[Dict[str, Any]]:
    """
    Split text into logical chunks.
    Attempts to respect structural legal splits (e.g. sections or paragraph marks).
    """
    # Normalize newlines
    text = text.replace("\r\n", "\n")
    
    # Try splitting by double-newlines first (paragraphs/sections)
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
            
        # If a single paragraph is larger than our max limit, we slice it
        if len(para_words) > max_chunk_words:
            # Add existing accumulated chunk first
            if current_chunk_words:
                chunks.append(" ".join(current_chunk_words))
                current_chunk_words = []
                
            # Chunk the large paragraph
            for i in range(0, len(para_words), max_chunk_words - overlap_words):
                slice_words = para_words[i : i + max_chunk_words]
                chunks.append(" ".join(slice_words))
        else:
            # If adding this paragraph exceeds limits, flush first
            if len(current_chunk_words) + len(para_words) > max_chunk_words:
                chunks.append(" ".join(current_chunk_words))
                # Keep overlap words from the end of the previous chunk
                overlap_start = max(0, len(current_chunk_words) - overlap_words)
                current_chunk_words = current_chunk_words[overlap_start:]
            
            current_chunk_words.extend(para_words)

    # Add remaining text
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
        
    ext = os.path.splitext(filename)[1].lower()
    
    chunks_with_metadata = []
    
    if ext == ".json":
        # Structured JSON files (e.g., corpus dump)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # If it's a list of pre-configured documents/chunks
        if isinstance(data, list):
            for idx, item in enumerate(data):
                text = item.get("text", "")
                item_meta = base_metadata.copy()
                item_meta.update(item.get("metadata", {}))
                
                # Check for sub-chunking if item text is large
                sub_chunks = chunk_text(text)
                for sc in sub_chunks:
                    meta = item_meta.copy()
                    # Capture exact section if exists in text
                    section_match = re.search(r'(?:Section|§)\s*([\w\.\d\-]+)', sc["text"], re.IGNORECASE)
                    if section_match:
                        meta["section"] = section_match.group(1)
                    
                    chunks_with_metadata.append({
                        "id": sc["id"],
                        "text": sc["text"],
                        "metadata": meta
                    })
        elif isinstance(data, dict):
            # Single structured doc
            text = data.get("text", "")
            doc_meta = base_metadata.copy()
            doc_meta.update(data.get("metadata", {}))
            sub_chunks = chunk_text(text)
            for sc in sub_chunks:
                meta = doc_meta.copy()
                chunks_with_metadata.append({
                    "id": sc["id"],
                    "text": sc["text"],
                    "metadata": meta
                })
    else:
        # Default plain text / markdown file
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback for binary / latin-1
            with open(filepath, "r", encoding="latin-1") as f:
                content = f.read()
                
        sub_chunks = chunk_text(content)
        for sc in sub_chunks:
            meta = base_metadata.copy()
            
            # Extract section numbers (e.g., "Section 4.1" or "§ 102") to enrich search metadata
            section_match = re.search(r'(?:Section|§)\s*([\w\.\d\-]+)', sc["text"], re.IGNORECASE)
            if section_match:
                meta["section"] = section_match.group(1)
                
            chunks_with_metadata.append({
                "id": sc["id"],
                "text": sc["text"],
                "metadata": meta
            })
            
    return chunks_with_metadata
