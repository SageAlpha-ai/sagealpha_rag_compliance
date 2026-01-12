"""
Chat Memory Module - Stores chat interactions in ChromaDB.
Uses Chroma's default embeddings (no Azure needed for chat history).
"""

import os
import uuid
from datetime import datetime, timezone

import chromadb
from chromadb.api.models.Collection import Collection


CHAT_HISTORY_COLLECTION_NAME = "chat_history"


def get_chat_collection(chroma_client: chromadb.ClientAPI) -> Collection:
    """
    Gets or creates the chat_history collection.
    Uses Chroma's default embedding function (all-MiniLM-L6-v2).
    """
    return chroma_client.get_or_create_collection(name=CHAT_HISTORY_COLLECTION_NAME)


def store_chat_turn(
    collection: Collection,
    query_text: str,
    response_text: str,
    session_id: str
) -> None:
    """
    Stores query and response as TWO separate records in ChromaDB.
    Chroma auto-generates embeddings using its default model.
    """
    ts = datetime.now(timezone.utc).isoformat()
    
    # Store query - Chroma will auto-embed using default model
    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[query_text],
        metadatas=[{
            "type": "query",
            "session_id": session_id,
            "timestamp": ts
        }]
    )
    
    # Store response - Chroma will auto-embed using default model
    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[response_text],
        metadatas=[{
            "type": "response",
            "session_id": session_id,
            "timestamp": ts
        }]
    )


def generate_session_id() -> str:
    """Generates a unique session ID."""
    return str(uuid.uuid4())


def get_chat_history_count(collection: Collection) -> int:
    """Returns the number of documents in the chat history collection."""
    return collection.count()
