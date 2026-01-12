"""
Document Loader - FINANCE-GRADE VERSION

Loads documents from:
1. Local TXT files (documents/ folder)
2. Azure Blob Storage (PDF + Excel with structured financial metadata)

All documents are embedded into the SAME Chroma collection
with rich metadata for financial accuracy.
"""

import os
import argparse

from dotenv import load_dotenv
from tqdm import tqdm

import chromadb

from azure_blob_loader import load_azure_documents


def load_local_documents(documents_directory: str) -> tuple[list, list]:
    """
    Loads local TXT files line by line with source metadata.
    """
    documents = []
    metadatas = []
    
    if not os.path.exists(documents_directory):
        print(f"Local documents directory '{documents_directory}' not found. Skipping local files.")
        return documents, metadatas
    
    files = os.listdir(documents_directory)
    
    for filename in files:
        filepath = os.path.join(documents_directory, filename)
        
        if os.path.isdir(filepath):
            continue
            
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                for line_number, line in enumerate(
                    tqdm((file.readlines()), desc=f"Reading {filename}"), 1
                ):
                    line = line.strip()
                    if len(line) == 0:
                        continue
                    documents.append(line)
                    metadatas.append({
                        "filename": filename,
                        "line_number": line_number,
                        "source": f"local/{filename}",
                        "document_type": "text"
                    })
        except Exception as e:
            print(f"Failed to read {filename}: {e}")
    
    print(f"Loaded {len(documents)} chunks from local TXT files")
    return documents, metadatas


def process_azure_documents(azure_docs: list[dict]) -> tuple[list, list]:
    """
    Processes Azure documents with their structured financial metadata.
    """
    documents = []
    metadatas = []
    
    for doc in azure_docs:
        text = doc.get("text", "")
        metadata = doc.get("metadata", {})
        
        if not text.strip():
            continue
        
        # Ensure source is present
        if "source" not in metadata:
            metadata["source"] = "azure_blob/unknown"
        
        # Add document type marker
        metadata["document_type"] = "financial"
        
        documents.append(text)
        metadatas.append(metadata)
    
    print(f"Processed {len(documents)} structured financial chunks from Azure")
    return documents, metadatas


def main(
    documents_directory: str = "documents",
    collection_name: str = "documents_collection",
    persist_directory: str = ".",
) -> None:
    load_dotenv()
    
    print("=" * 60)
    print("FINANCE-GRADE DOCUMENT INGESTION")
    print("=" * 60)
    
    # 1. Load local TXT documents
    print("\n[1] Loading local TXT documents...")
    local_docs, local_meta = load_local_documents(documents_directory)
    
    # 2. Load Azure Blob Storage documents (PDF + Excel with structured metadata)
    print("\n[2] Loading Azure Blob Storage documents (structured)...")
    azure_docs = load_azure_documents()
    azure_chunks, azure_meta = process_azure_documents(azure_docs)
    
    # 3. Combine all documents
    print("\n[3] Combining documents...")
    all_documents = local_docs + azure_chunks
    all_metadatas = local_meta + azure_meta
    
    print(f"\nTotal documents to embed: {len(all_documents)}")
    print(f"  - Local TXT: {len(local_docs)}")
    print(f"  - Azure Financial: {len(azure_chunks)}")
    
    # Show sample of Azure metadata
    if azure_meta:
        print("\nSample Azure document metadata:")
        sample = azure_meta[0]
        for key, value in sample.items():
            print(f"  {key}: {value}")
    
    if len(all_documents) == 0:
        print("No documents to load. Exiting.")
        return
    
    # 4. Initialize Chroma client
    print(f"\n[4] Connecting to Chroma at '{persist_directory}'...")
    client = chromadb.PersistentClient(path=persist_directory)
    
    # Delete existing collection to ensure fresh structured data
    try:
        client.delete_collection(name=collection_name)
        print(f"Deleted existing collection '{collection_name}' for fresh ingestion")
    except:
        pass
    
    collection = client.get_or_create_collection(name=collection_name)
    
    # 5. Create IDs and add documents
    print("\n[5] Adding documents to Chroma with structured metadata...")
    ids = [str(i) for i in range(len(all_documents))]
    
    # Add in batches
    batch_size = 100
    for i in tqdm(range(0, len(all_documents), batch_size), desc="Adding documents", unit_scale=batch_size):
        batch_end = min(i + batch_size, len(all_documents))
        collection.add(
            ids=ids[i:batch_end],
            documents=all_documents[i:batch_end],
            metadatas=all_metadatas[i:batch_end],
        )
    
    # 6. Report results
    final_count = collection.count()
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Total documents in collection: {final_count}")
    print(f"  - With financial metadata: {len(azure_chunks)}")
    print(f"  - Local text documents: {len(local_docs)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load documents with financial-grade metadata into Chroma"
    )
    
    parser.add_argument(
        "--data_directory",
        type=str,
        default="documents",
        help="The directory where your local TXT files are stored",
    )
    parser.add_argument(
        "--collection_name",
        type=str,
        default="documents_collection",
        help="The name of the Chroma collection",
    )
    parser.add_argument(
        "--persist_directory",
        type=str,
        default="chroma_storage",
        help="The directory where you want to store the Chroma collection",
    )
    
    args = parser.parse_args()
    
    main(
        documents_directory=args.data_directory,
        collection_name=args.collection_name,
        persist_directory=args.persist_directory,
    )
