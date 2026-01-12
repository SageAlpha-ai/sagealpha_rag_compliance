"""
Chroma Cloud Client

STRICT RULES:
- NEVER use persist_directory
- NEVER use PersistentClient
- ONLY use HttpClient for Chroma Cloud
- ALL embeddings go to Chroma Cloud
- Local disk stores ZERO vectors
"""

from typing import Optional
import chromadb
from chromadb import HttpClient
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from config.settings import get_config, ChromaCloudConfig


# Module-level singleton
_client: Optional[ClientAPI] = None


def get_chroma_client() -> ClientAPI:
    """
    Gets Chroma Cloud HttpClient (singleton).
    
    NEVER uses local storage.
    ALL vectors stored in Chroma Cloud.
    """
    global _client
    
    if _client is not None:
        return _client
    
    config = get_config().chroma_cloud
    
    print("=" * 60)
    print("CONNECTING TO CHROMA CLOUD")
    print("=" * 60)
    print(f"Host: {config.host}")
    print(f"Tenant: {config.tenant}")
    print(f"Database: {config.database}")
    
    # Use CloudClient for Chroma Cloud
    # This is the recommended client for Chroma Cloud
    _client = chromadb.CloudClient(
        tenant=config.tenant,
        database=config.database,
        api_key=config.api_key,
    )
    
    # Verify connection
    heartbeat = _client.heartbeat()
    print(f"Connected to Chroma Cloud (heartbeat: {heartbeat})")
    print("=" * 60)
    
    return _client


def get_collection(
    name: Optional[str] = None,
    create_if_missing: bool = True
) -> Collection:
    """
    Gets or creates the main documents collection.
    
    Args:
        name: Collection name (defaults to config value)
        create_if_missing: Whether to create if doesn't exist
    
    Returns:
        Chroma Collection object
    """
    client = get_chroma_client()
    config = get_config().chroma_cloud
    
    collection_name = name or config.collection_name
    
    if create_if_missing:
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    else:
        collection = client.get_collection(name=collection_name)
    
    print(f"Collection: {collection_name} ({collection.count()} documents)")
    
    return collection


def get_chat_history_collection() -> Collection:
    """
    Gets or creates the chat history collection.
    
    Separate collection for storing query/response embeddings.
    """
    client = get_chroma_client()
    
    collection = client.get_or_create_collection(
        name="chat_history",
        metadata={"hnsw:space": "cosine"}
    )
    
    return collection


def delete_collection(name: str) -> None:
    """Deletes a collection (use for fresh re-ingestion)."""
    client = get_chroma_client()
    
    try:
        client.delete_collection(name=name)
        print(f"Deleted collection: {name}")
    except Exception as e:
        print(f"Collection {name} not found or could not be deleted: {e}")
