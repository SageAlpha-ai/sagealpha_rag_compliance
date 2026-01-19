# Deployment Readiness Checklist

Use this checklist before deploying to production.

## Pre-Deployment

### Code Quality
- [ ] All code is committed to Git
- [ ] No sensitive data in code (API keys, passwords)
- [ ] `.env` file is in `.gitignore` (already done)
- [ ] All imports work without errors
- [ ] No hardcoded paths or local-only references

### Configuration
- [ ] `requirements.txt` is up to date
- [ ] `runtime.txt` specifies Python 3.11.0
- [ ] `render.yaml` configured (if using Render)
- [ ] `Procfile` exists (if using Heroku)
- [ ] `.env.example` template created

### Documentation
- [ ] `README.md` updated with deployment info
- [ ] `DEPLOYMENT.md` created with platform instructions
- [ ] `CONTRIBUTING.md` created (if open source)
- [ ] `LICENSE` file added

### Testing
- [ ] Local ingestion works: `python ingest.py --fresh`
- [ ] Local API works: `uvicorn api:app --host 0.0.0.0 --port 8000`
- [ ] Health endpoint returns 200: `GET /health`
- [ ] Query endpoint works: `POST /query`
- [ ] ChromaDB connection verified
- [ ] Documents stored successfully (check count)

## Environment Variables

Verify all required variables are documented:

### Required
- [ ] `AZURE_OPENAI_API_KEY`
- [ ] `AZURE_OPENAI_ENDPOINT`
- [ ] `AZURE_OPENAI_API_VERSION`
- [ ] `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`
- [ ] `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME`
- [ ] `AZURE_STORAGE_CONNECTION_STRING`
- [ ] `AZURE_BLOB_CONTAINER_NAME`
- [ ] `CHROMA_API_KEY`
- [ ] `CHROMA_TENANT`
- [ ] `CHROMA_DATABASE`

### Optional (with defaults)
- [ ] `CHROMA_HOST` (default: `api.trychroma.com`)
- [ ] `CHROMA_COLLECTION_NAME` (default: `compliance`)
- [ ] `RAG_API_KEY` (optional, for API auth)
- [ ] `CORS_ORIGINS` (default: `*`)
- [ ] `LOG_LEVEL` (default: `INFO`)

## Platform-Specific

### Render.com
- [ ] `render.yaml` configured correctly
- [ ] Collection name matches (`compliance`)
- [ ] Start command uses `api:app`
- [ ] Port uses `$PORT` variable

### Heroku
- [ ] `Procfile` exists
- [ ] `runtime.txt` specifies Python version
- [ ] Buildpacks configured (if needed)

### GitHub
- [ ] Repository is private (if proprietary)
- [ ] `.gitignore` excludes sensitive files
- [ ] No `.env` file committed
- [ ] README has setup instructions
- [ ] License file added

## Post-Deployment

### Verification
- [ ] Health endpoint: `GET /health` returns 200
- [ ] Swagger UI: `GET /docs` loads
- [ ] ChromaDB connected: Health shows `chroma_connected: true`
- [ ] Documents exist: Health shows `document_count > 0`
- [ ] Query works: `POST /query` returns response
- [ ] Logs show no errors

### Monitoring
- [ ] Application logs accessible
- [ ] Error tracking set up (if applicable)
- [ ] Health check monitoring configured
- [ ] Uptime monitoring set up

### Security
- [ ] API authentication enabled (if needed)
- [ ] CORS configured correctly
- [ ] HTTPS enabled
- [ ] Secrets stored securely (not in code)
- [ ] No sensitive data in logs

## Quick Deploy Commands

### Render
```bash
git push origin main  # Auto-deploys
```

### Heroku
```bash
git push heroku main
heroku run python ingest.py --fresh
```

## Troubleshooting

If deployment fails:
1. Check platform logs
2. Verify environment variables
3. Test locally first
4. Check ChromaDB connection
5. Verify Python version matches `runtime.txt`
