# AI RAG Service

Production-ready Finance-Grade RAG API powered by Chroma Cloud and Azure OpenAI.

## Overview

This is a FastAPI-based RAG (Retrieval-Augmented Generation) service that provides intelligent query answering over financial documents. It uses:

- **Chroma Cloud** for vector storage and retrieval
- **Azure OpenAI** for embeddings (`text-embedding-3-large`) and chat completion
- **OpenAI-style answerability validation** for accurate responses
- **Hybrid RAG + LLM fallback** for guaranteed answers

## Features

- 📄 **Document-Grounded Answers**: Answers from Azure Blob Storage documents when available
- 🔍 **Strict Answerability Validation**: Only answers when documents match entity, fiscal year, and metric requirements
- 🤖 **Automatic LLM Fallback**: Falls back to LLM when no documents are retrieved
- 🚫 **RAG_NO_ANSWER State**: Returns informative message when documents don't match query requirements
- 🏢 **Finance-Grade Attribution**: Entity and fiscal year tracking
- 🌐 **RESTful API**: Compatible with Node.js or any HTTP client
- ✅ **Production-Ready**: Startup safety checks, structured logging, health endpoints

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `env.example` to `.env` and fill in your credentials:

```bash
cp env.example .env
```

**Required environment variables:**
- `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint
- `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME` - Embedding model deployment (e.g., `text-embedding-3-large`)
- `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` - Chat model deployment
- `AZURE_STORAGE_CONNECTION_STRING` - Azure Blob Storage connection string
- `AZURE_BLOB_CONTAINER_NAME` - Azure Blob Storage container name
- `CHROMA_API_KEY` - Chroma Cloud API key
- `CHROMA_TENANT` - Chroma Cloud tenant ID
- `CHROMA_DATABASE` - Chroma Cloud database name

See `env.example` for all configuration options.

### 3. Ingest Documents (First Time)

```bash
python ingest.py --fresh
```

This will:
- Load documents from Azure Blob Storage (PDF, Excel, TXT)
- Load local documents from `documents/` directory (if exists)
- Chunk documents using LangChain's RecursiveCharacterTextSplitter
- Generate embeddings using Azure OpenAI (`text-embedding-3-large`)
- Store embeddings in Chroma Cloud

**Important**: After changing embedding models, you MUST re-ingest:
```bash
python ingest.py --fresh
```

### 4. Run the API Server

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

**Important**: 
- Use **`api:app`** (not `main:app`) - the FastAPI app is in `api.py`
- `--host 0.0.0.0` is for server binding (allows external connections)
- Always use `http://localhost:8000` in your browser

**Windows Quick Start**: Run `start_server.bat` or see [START_SERVER.md](START_SERVER.md) for details.

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Usage

### Query Endpoint

```bash
POST /query
Content-Type: application/json

{
  "query": "What is Oracle Financial Services revenue for FY2023?"
}
```

**Response Types:**

1. **RAG** - Answer from documents:
```json
{
  "answer": "Oracle Financial Services revenue for FY2023 was...",
  "answer_type": "RAG",
  "sources": ["azure_blob/document.pdf (page 5) (FY: FY2023)"]
}
```

2. **RAG_NO_ANSWER** - Documents retrieved but don't match requirements:
```json
{
  "answer": "The requested FY2024 data is not available in the documents.",
  "answer_type": "RAG_NO_ANSWER",
  "sources": ["azure_blob/document.pdf (page 5) (FY: FY2023)"]
}
```

3. **LLM** - No documents retrieved, fallback to LLM:
```json
{
  "answer": "Based on general knowledge...",
  "answer_type": "LLM",
  "sources": []
}
```

### Node.js Example

```javascript
const response = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ 
    query: "What is Oracle Financial Services revenue for FY2023?" 
  })
});

const data = await response.json();
console.log(data.answer);
console.log(data.answer_type); // "RAG", "RAG_NO_ANSWER", or "LLM"
console.log(data.sources);
```

### Health Check

```bash
GET /health
```

Returns service status, ChromaDB connection, and document count.

## RAG Decision Logic

The system follows OpenAI's approach to answerability validation:

1. **ALWAYS retrieves documents first** (no exceptions)
2. **Validates answerability**:
   - Entity match (if entity specified in query)
   - Fiscal year match (if year specified in query)
   - Metric match (if metric specified in query)
3. **Routes based on validation**:
   - If answerable → **RAG** (generate answer from context)
   - If not answerable → **RAG_NO_ANSWER** (no LLM generation, informative message)
   - If no documents → **LLM** (fallback to general knowledge)

**Key Rule**: `sources` is NEVER null - it's always a list (empty for LLM answers).

## Deployment

### Render.com

This service is configured for Render.com deployment via `render.yaml`.

1. **Connect GitHub repository** to Render
2. **Render will automatically detect** `render.yaml`
3. **Set environment variables** in Render dashboard (from `.env.example`)
4. **Deploy!**

The service will:
- Start with `uvicorn api:app --host 0.0.0.0 --port $PORT`
- Run startup safety checks
- Log ChromaDB document count
- Fail loudly if vector store is empty

### Other Platforms

The service can be deployed to any platform that supports Python:
- **Heroku**: Use `Procfile` with `web: uvicorn api:app --host 0.0.0.0 --port $PORT`
- **AWS Elastic Beanstalk**: Standard Python deployment
- **Google Cloud Run**: Container or direct Python
- **Azure App Service**: Python runtime
- **Docker**: Build your own Dockerfile

## Project Structure

```
.
├── api.py                      # FastAPI application entry point
├── ingest.py                   # Document ingestion script
├── config/                     # Configuration management
│   └── settings.py            # Environment variable loading
├── rag/                        # RAG pipeline logic
│   ├── langchain_orchestrator.py  # Main orchestration with answerability validation
│   ├── retriever.py           # Document retrieval utilities
│   └── report_generator.py    # Long-format report generation
├── ingestion/                  # Document ingestion
│   ├── azure_blob_loader.py   # Azure Blob Storage loader
│   ├── chunking.py            # Text chunking with LangChain
│   └── embed_and_store.py     # Embedding and Chroma storage
├── vectorstore/                # Chroma Cloud integration
│   └── chroma_client.py       # Chroma Cloud client
├── requirements.txt            # Python dependencies
├── env.example                # Environment template
├── .gitignore                 # Git ignore rules
├── render.yaml                # Render deployment config
├── Procfile                   # Heroku deployment config
├── Dockerfile                 # Docker deployment config
└── DEPLOYMENT.md              # Deployment guide
```

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Ingest documents
python ingest.py --fresh

# Run API (use --host 0.0.0.0 for binding, but access via localhost in browser)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test query endpoint
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Oracle revenue?"}'
```

### Logging

The service uses structured logging with the following levels:
- `INFO`: Normal operation (queries, retrieval, routing decisions)
- `WARNING`: Non-critical issues (empty retrieval, answerability failures)
- `ERROR`: Critical errors (configuration failures, ChromaDB connection issues)

Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging.

## Startup Safety Checks

On startup, the service performs:

1. **Configuration Validation**: Verifies all required environment variables
2. **Model Logging**: Logs embedding and chat model names
3. **ChromaDB Verification**: 
   - Checks connection
   - Logs document count
   - **Fails loudly** if collection is empty (logs error, continues serving)

## Troubleshooting

### "ChromaDB collection is EMPTY"

**Solution**: Run ingestion:
```bash
python ingest.py --fresh
```

### "Embeddings generated: 0"

**Possible causes**:
1. Embedding API error - check Azure OpenAI credentials
2. Documents filtered out - check if documents have text > 10 characters
3. Model deployment issue - verify `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME` exists

**Solution**: Check logs for `[ERROR]` messages during ingestion.

### "RAG_NO_ANSWER" for queries that should work

**Possible causes**:
1. Documents don't match fiscal year requirement
2. Documents don't match entity requirement
3. Documents don't contain requested metric

**Solution**: Check logs for `[VALIDATE]` messages showing match counts.

### Changing Embedding Models

If you change `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME`:

1. **MUST re-ingest** all documents:
   ```bash
   python ingest.py --fresh
   ```
2. Code automatically uses the new model from config
3. Old embeddings won't work with new model (different vector spaces)

## License

See [LICENSE](LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions to Render, Heroku, Docker, AWS, GCP, and Azure.
#   s a g e a l p h a _ r a g _ c o m p l i a n c e 
 
 #   s a g e a l p h a _ r a g _ c o m p l i a n c e 
 
 #   s a g e a l p h a _ r a g _ c o m p l i a n c e 
 
 