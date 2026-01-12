# AI RAG Service

Finance-Grade RAG API powered by Chroma Cloud and Azure OpenAI.

## Overview

This is a FastAPI-based RAG (Retrieval-Augmented Generation) service that provides intelligent query answering over financial documents. It uses:

- **Chroma Cloud** for vector storage and retrieval
- **Azure OpenAI** for embeddings and chat completion
- **Hybrid RAG + LLM fallback** for guaranteed answers

## Features

- 📄 Answers from Azure Blob Storage documents when available
- 🤖 Automatic LLM fallback when documents cannot answer
- 🏢 Finance-grade entity and year attribution
- ✅ Never returns "Not available"
- 🌐 RESTful API for Node.js or any HTTP client

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint
- `AZURE_STORAGE_CONNECTION_STRING` - Azure Blob Storage connection string
- `CHROMA_API_KEY` - Chroma Cloud API key
- `CHROMA_TENANT` - Chroma Cloud tenant ID
- `CHROMA_DATABASE` - Chroma Cloud database name

See `.env.example` for all configuration options.

### 3. Ingest Documents (First Time)

```bash
python ingest.py --fresh
```

This loads documents from Azure Blob Storage and local files, then embeds and stores them in Chroma Cloud.

### 4. Run the API Server

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Usage

### Query Endpoint

```bash
POST /query
Content-Type: application/json

{
  "question": "What is Oracle's revenue in FY2023?"
}
```

**Response:**

```json
{
  "answer": "Oracle's revenue for FY2023 was $50 billion...",
  "answer_type": "RAG",
  "sources": ["document1.pdf", "document2.xlsx"]
}
```

### Node.js Example

```javascript
const response = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ 
    question: "What is Oracle's revenue in FY2023?" 
  })
});

const data = await response.json();
console.log(data.answer);
```

### Health Check

```bash
GET /health
```

## Deployment

### Render.com

This service is configured for Render.com deployment via `render.yaml`.

1. Connect your GitHub repository to Render
2. Render will automatically detect `render.yaml`
3. Set environment variables in Render dashboard
4. Deploy!

### Other Platforms

The service can be deployed to any platform that supports Python:
- Heroku
- AWS Elastic Beanstalk
- Google Cloud Run
- Azure App Service
- Docker (build your own Dockerfile)

## Project Structure

```
.
├── api.py                 # FastAPI application entry point
├── config/                # Configuration management
│   └── settings.py
├── rag/                   # RAG pipeline logic
│   ├── query_engine.py
│   ├── retriever.py
│   ├── router.py
│   └── answer_formatter.py
├── ingestion/             # Document ingestion
│   ├── azure_blob_loader.py
│   ├── chunking.py
│   └── embed_and_store.py
├── vectorstore/           # Chroma Cloud integration
│   └── chroma_client.py
├── ingest.py             # Ingestion script
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
└── render.yaml           # Render deployment config
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

# Run API
uvicorn api:app --reload
```

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test query endpoint
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Oracle revenue?"}'
```

## License

Proprietary - All rights reserved
