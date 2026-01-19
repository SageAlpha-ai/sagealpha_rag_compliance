# Quick Start Guide

Get your RAG API up and running in 5 minutes.

## Step 1: Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/sagealpha_rag_compilance.git
cd sagealpha_rag_compilance
```

## Step 2: Set Up Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Configure Environment Variables

```bash
# Copy template
cp env.example .env

# Edit .env with your credentials
# Use your favorite editor to fill in:
# - Azure OpenAI keys
# - Azure Blob Storage connection
# - Chroma Cloud credentials
```

## Step 4: Ingest Documents

```bash
python ingest.py --fresh
```

This will:
- Load PDFs from Azure Blob Storage
- Chunk documents
- Generate embeddings
- Store in Chroma Cloud

**Wait for**: `Documents stored: 738` (or your document count)

## Step 5: Start API Server

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

## Step 6: Test API

Open browser:
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

Test query:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Oracle revenue?"}'
```

## Troubleshooting

### "ChromaDB collection is EMPTY"
Run: `python ingest.py --fresh`

### "Module not found"
Run: `pip install -r requirements.txt`

### "Environment variable not set"
Check `.env` file exists and has all required variables

### "Port already in use"
Change port: `uvicorn api:app --host 0.0.0.0 --port 8001`

## Next Steps

- **Deploy**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Develop**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **GitHub**: See [GITHUB_SETUP.md](GITHUB_SETUP.md)
