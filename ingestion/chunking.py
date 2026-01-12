"""
Text Chunking Module

Splits documents into chunks suitable for embedding.
Preserves metadata across chunks.
"""

import os
from typing import List, Dict
from tqdm import tqdm


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Splits text into overlapping chunks.
    
    Args:
        text: Input text to split
        chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence/paragraph boundary
        if end < len(text):
            # Look for sentence end
            for sep in ['. ', '.\n', '\n\n', '\n']:
                idx = text.rfind(sep, start, end)
                if idx > start + chunk_size // 2:
                    end = idx + len(sep)
                    break
        
        chunks.append(text[start:end].strip())
        start = end - overlap
    
    return chunks


def chunk_documents(documents: List[Dict], chunk_size: int = 1000) -> List[Dict]:
    """
    Chunks documents while preserving metadata.
    
    Args:
        documents: List of documents with 'text' and 'metadata'
        chunk_size: Maximum characters per chunk
    
    Returns:
        List of chunked documents with metadata
    """
    chunked = []
    
    for doc in tqdm(documents, desc="Chunking documents"):
        text = doc.get("text", "")
        metadata = doc.get("metadata", {})
        
        # Financial rows should not be further chunked
        if metadata.get("document_type") == "financial_row":
            chunked.append(doc)
            continue
        
        # Chunk longer documents
        text_chunks = chunk_text(text, chunk_size)
        
        for i, chunk in enumerate(text_chunks):
            # Skip empty or very short chunks
            chunk_text = chunk.strip()
            if not chunk_text or len(chunk_text) < 20:
                continue
            
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(text_chunks)
            
            chunked.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
    
    return chunked


def chunk_local_documents(directory: str = "documents") -> List[Dict]:
    """
    Loads and chunks local TXT documents.
    
    Args:
        directory: Path to documents directory
    
    Returns:
        List of chunked documents with metadata
    """
    print("=" * 60)
    print("LOADING LOCAL DOCUMENTS")
    print("=" * 60)
    
    documents = []
    
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        return documents
    
    for filename in os.listdir(directory):
        if not filename.endswith(".txt"):
            continue
        
        filepath = os.path.join(directory, filename)
        print(f"  Loading: {filename}")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Create per-line chunks for TXT files
            for i, line in enumerate(tqdm(lines, desc=f"Reading {filename}", leave=False)):
                line = line.strip()
                if len(line) < 10:
                    continue
                
                documents.append({
                    "text": line,
                    "metadata": {
                        "source": f"local/{filename}",
                        "filename": filename,
                        "line_number": i + 1,
                        "document_type": "text"
                    }
                })
            
            print(f"    [OK] {len(lines)} lines")
            
        except Exception as e:
            print(f"    [ERROR] {e}")
    
    print(f"\nTotal: {len(documents)} chunks from local files")
    print("=" * 60)
    
    return documents
