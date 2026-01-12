"""
Embedding and Storage Module

Stores documents in Chroma Cloud using Chroma's default embedding function.
Uses deterministic IDs to prevent duplicates.

NOTE: Chroma Cloud will generate embeddings automatically using its default
embedding function (all-MiniLM-L6-v2). This avoids Azure OpenAI embedding
deployment issues while still providing semantic search capability.
"""

import hashlib
from typing import List, Dict
from tqdm import tqdm

from config.settings import get_config
from vectorstore.chroma_client import get_collection, delete_collection


def generate_deterministic_id(text: str, source: str) -> str:
    """
    Generates deterministic ID for deduplication.
    Same content + source = same ID = no duplicate.
    """
    content = f"{source}:{text[:500]}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def embed_and_store_documents(
    documents: List[Dict],
    collection_name: str = None,
    fresh: bool = False,
    batch_size: int = 100
) -> int:
    """
    Stores documents in Chroma Cloud.
    
    Chroma Cloud automatically generates embeddings using its default
    embedding function when documents are added without explicit embeddings.
    
    Args:
        documents: List of documents with 'text' and 'metadata'
        collection_name: Target collection (defaults to config)
        fresh: If True, delete existing collection first
        batch_size: Batch size for upsert
    
    Returns:
        Number of documents stored
    """
    print("=" * 60)
    print("STORING DOCUMENTS TO CHROMA CLOUD")
    print("=" * 60)
    
    if not documents:
        print("No documents to store")
        return 0
    
    config = get_config()
    collection_name = collection_name or config.chroma_cloud.collection_name
    
    # Delete existing if fresh ingestion
    if fresh:
        print(f"Fresh ingestion: deleting existing collection '{collection_name}'")
        delete_collection(collection_name)
    
    # Get collection (creates if needed)
    collection = get_collection(collection_name)
    
    print(f"\nStoring {len(documents)} documents...")
    print("Embeddings: Chroma Cloud default (all-MiniLM-L6-v2)")
    
    # Process in batches
    total_stored = 0
    
    for i in tqdm(range(0, len(documents), batch_size), desc="Upserting to Chroma Cloud"):
        batch = documents[i:i + batch_size]
        
        # Extract texts and filter empty
        texts = []
        valid_docs = []
        
        for doc in batch:
            text = doc.get("text", "").strip()
            if text:  # Only include non-empty texts
                texts.append(text)
                valid_docs.append(doc)
        
        if not texts:
            print(f"    [WARN] Batch {i // batch_size + 1}: All documents empty, skipping")
            continue
        
        # Generate deterministic IDs for valid docs only
        ids = [
            generate_deterministic_id(doc["text"], doc.get("metadata", {}).get("source", ""))
            for doc in valid_docs
        ]
        
        # Extract metadata
        metadatas = [doc.get("metadata", {}) for doc in valid_docs]
        
        # Clean metadata (remove None values and convert floats)
        for meta in metadatas:
            keys_to_remove = [k for k, v in meta.items() if v is None]
            for k in keys_to_remove:
                del meta[k]
            # Convert float values to strings for Chroma compatibility
            for k, v in list(meta.items()):
                if isinstance(v, float):
                    meta[k] = str(v)
        
        # Upsert to Chroma Cloud (no embeddings = Chroma generates them)
        try:
            collection.upsert(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            total_stored += len(valid_docs)
            
            # Log progress every 5 batches
            if (i // batch_size) % 5 == 0 and i > 0:
                print(f"\n  Upserted {total_stored}/{len(documents)} documents to Chroma Cloud")
            
            # Log first batch details for debugging
            if i == 0:
                print(f"\n  First batch: {len(valid_docs)} documents")
                if valid_docs:
                    first_source = valid_docs[0].get("metadata", {}).get("source", "unknown")
                    first_text_len = len(valid_docs[0].get("text", ""))
                    print(f"    Example: {first_source} ({first_text_len} chars)")
                
        except Exception as e:
            print(f"\n[ERROR] Upsert failed for batch {i // batch_size + 1}: {e}")
            import traceback
            traceback.print_exc()
            # Continue with next batch
            continue
    
    print(f"\n{'=' * 60}")
    print(f"INGESTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total documents stored: {total_stored}")
    print(f"Collection count: {collection.count()}")
    print("=" * 60)
    
    return total_stored
