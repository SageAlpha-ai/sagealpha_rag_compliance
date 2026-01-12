#!/usr/bin/env python3
"""
AI RAG Service API

Exposes the RAG query engine as a REST API using FastAPI.
Can be consumed by Node.js or any other service.

Run:
    uvicorn api:app --host 0.0.0.0 --port 8000

Swagger UI:
    http://localhost:8000/docs
"""

import logging
import os
import sys
from typing import List, Optional

# Add current directory to path for imports
sys.path.insert(0, ".")

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import existing logic
from config.settings import get_config, validate_config
from rag.query_engine import answer_query_simple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ================================
# Pydantic Models
# ================================

class QueryRequest(BaseModel):
    """Request body for /query endpoint."""
    question: str = Field(
        ...,
        description="The question to ask the AI",
        min_length=1,
        max_length=2000,
        examples=["What is the revenue of Oracle Financial Services for FY2023?"]
    )


class QueryResponse(BaseModel):
    """Response body for /query endpoint."""
    answer: str = Field(..., description="The generated answer")
    answer_type: str = Field(
        ...,
        description="'RAG' if answered from documents, 'LLM' if from training data"
    )
    sources: Optional[List[str]] = Field(
        None,
        description="List of source documents (null for LLM answers)"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    chroma_connected: bool
    document_count: int


# ================================
# FastAPI App
# ================================

app = FastAPI(
    title="AI RAG Service",
    description="""
Finance-Grade RAG API powered by:
- **Chroma Cloud** for vector storage
- **Azure OpenAI** for embeddings and chat
- **Hybrid RAG + LLM fallback** for guaranteed answers

## Features

- 📄 Answers from Azure Blob documents when available
- 🤖 Automatic LLM fallback when documents cannot answer
- 🏢 Finance-grade entity and year attribution
- ✅ Never returns "Not available"

## Usage

```javascript
// Node.js example
const response = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question: "What is Oracle's revenue in FY2023?" })
});
const data = await response.json();
console.log(data.answer);
```
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ================================
# CORS Middleware (for browser/Node.js clients)
# ================================

# CORS: Allow configurable origins via env (default: allow all)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================
# Optional API Key Authentication
# ================================

# Optional: set RAG_API_KEY env var to enable authentication (disabled if not set)
RAG_API_KEY = os.getenv("RAG_API_KEY")

def verify_api_key(x_api_key: Optional[str] = Header(None, alias="x-api-key")):
    """Optional API key authentication. Disabled if RAG_API_KEY env var is not set."""
    if RAG_API_KEY:
        if not x_api_key or x_api_key != RAG_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# ================================
# Startup Event
# ================================

@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup. App continues even if external services are unavailable."""
    try:
        config = get_config()
        validate_config(config)
        logger.info("Configuration loaded successfully")
    except ValueError as e:
        # Log error but don't crash - app can still serve health checks
        logger.error(f"Configuration error: {e}. Some endpoints may not work.")
    
    logger.info("=" * 60)
    logger.info("AI RAG SERVICE STARTED")
    logger.info("=" * 60)
    if RAG_API_KEY:
        logger.info("API Key authentication: ENABLED")
    else:
        logger.info("API Key authentication: DISABLED")
    logger.info("=" * 60)


# ================================
# Endpoints
# ================================

@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with service info."""
    return {
        "service": "AI RAG Service",
        "status": "running",
        "version": "1.0.0",
        "usage": "POST /query with JSON { question: string }",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Info"])
async def health_check():
    """Health check endpoint."""
    try:
        from vectorstore.chroma_client import get_collection
        collection = get_collection(create_if_missing=False)
        doc_count = collection.count()
        
        return HealthResponse(
            status="healthy",
            service="AI RAG Service",
            chroma_connected=True,
            document_count=doc_count
        )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            service="AI RAG Service",
            chroma_connected=False,
            document_count=0
        )


@app.get("/query", tags=["Query"])
async def query_help():
    """
    Usage instructions for the /query endpoint.
    
    This endpoint only accepts POST requests.
    Use POST /query with a JSON body containing your question.
    """
    return {
        "error": "Method not allowed",
        "message": "Use POST /query with a JSON body",
        "usage": {
            "method": "POST",
            "url": "/query",
            "headers": {"Content-Type": "application/json"},
            "body": {"question": "Your question here"}
        },
        "example": {
            "question": "What is the revenue of Oracle Financial Services for FY2023?"
        },
        "curl_example": 'curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d \'{"question": "What is Oracle revenue?"}\''
    }


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_rag(
    request: QueryRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Query the RAG system.
    
    - **question**: The question to ask
    
    Returns:
    - **answer**: The generated answer
    - **answer_type**: "RAG" (from documents) or "LLM" (from training data)
    - **sources**: List of document sources (null for LLM answers)
    """
    try:
        result = answer_query_simple(request.question)
        
        return QueryResponse(
            answer=result["answer"],
            answer_type=result["answer_type"],
            sources=result["sources"]
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        # Log error server-side but never expose stack traces to clients
        logger.error(f"Query processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your query. Please try again."
        )


# ================================
# Run directly (for development)
# ================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
