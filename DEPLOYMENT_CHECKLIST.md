# Deployment Checklist

Use this checklist before deploying to Render.com.

## ✅ Pre-Deployment

### Code Ready
- [ ] All code committed to Git
- [ ] `.env` file is in `.gitignore` (never commit secrets)
- [ ] No API keys or secrets in code
- [ ] `env.example` has placeholder values only

### Files Verified
- [ ] `render.yaml` exists and is correct
- [ ] `Procfile` exists and is correct
- [ ] `requirements.txt` has all dependencies
- [ ] `runtime.txt` specifies Python version
- [ ] `.gitignore` excludes sensitive files

### Local Testing
- [ ] App runs locally: `python api.py`
- [ ] Health endpoint works: `GET /health`
- [ ] Query endpoint works: `POST /query`
- [ ] Swagger UI accessible: `/docs`
- [ ] No errors in startup logs

## ✅ GitHub Setup

- [ ] Repository created on GitHub
- [ ] Code pushed to GitHub: `git push origin main`
- [ ] Repository is private (recommended for proprietary code)
- [ ] Branch protection enabled (optional)

## ✅ Render Setup

### Service Configuration
- [ ] Render account created
- [ ] GitHub repository connected to Render
- [ ] Service type: Web Service
- [ ] Auto-deploy enabled (deploys on push to main)

### Environment Variables Set

#### Required (must be set):
- [ ] `AZURE_OPENAI_API_KEY`
- [ ] `AZURE_OPENAI_ENDPOINT`
- [ ] `AZURE_OPENAI_API_VERSION`
- [ ] `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`
- [ ] `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME`
- [ ] `AZURE_STORAGE_CONNECTION_STRING`
- [ ] `AZURE_BLOB_CONTAINER_NAME`
- [ ] `CHROMA_HOST`
- [ ] `CHROMA_API_KEY`
- [ ] `CHROMA_TENANT`
- [ ] `CHROMA_DATABASE`

#### Optional (recommended):
- [ ] `CHROMA_COLLECTION_NAME` (default: compliance)
- [ ] `RAG_API_KEY` (for API authentication)
- [ ] `CORS_ORIGINS` (default: *)
- [ ] `LOG_LEVEL` (default: INFO)

## ✅ Post-Deployment Verification

### Service Status
- [ ] Service is running (green status in Render dashboard)
- [ ] No build errors in Render logs
- [ ] No runtime errors in Render logs

### Endpoints
- [ ] Root endpoint: `GET /` returns 200
- [ ] Health check: `GET /health` returns 200
- [ ] Swagger UI: `GET /docs` accessible
- [ ] Query endpoint: `POST /query` works

### Startup Logs
- [ ] Configuration loaded successfully
- [ ] No missing environment variable errors
- [ ] ChromaDB connection successful (or graceful failure logged)
- [ ] Server started on correct port

### Functionality
- [ ] Test query returns response
- [ ] RAG functionality works (if config complete)
- [ ] API authentication works (if enabled)
- [ ] CORS works (if configured)

## 🐛 Troubleshooting

If deployment fails:

1. **Check Build Logs**:
   - Go to Render dashboard → Logs
   - Look for `pip install` errors
   - Check Python version compatibility

2. **Check Runtime Logs**:
   - Look for startup errors
   - Check for missing environment variables
   - Verify ChromaDB connection

3. **Check Environment Variables**:
   - Verify all required variables are set
   - Check for typos in variable names
   - Ensure values are correct (no extra spaces)

4. **Check Health Endpoint**:
   - `GET /health` should return 200
   - If degraded, check ChromaDB connection

## 📝 Notes

- Render automatically sets `PORT` environment variable
- App uses `PORT` or defaults to 8000 for local dev
- All secrets should be in Render dashboard, never in code
- `.env` file is for local development only

## 🎉 Success Criteria

Your deployment is successful when:
- ✅ Service shows "Live" status in Render
- ✅ All endpoints return 200 (or appropriate status codes)
- ✅ Startup logs show no critical errors
- ✅ Test query returns valid response
- ✅ Swagger UI is accessible

## 📚 Resources

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete deployment guide
- [README.md](README.md) - Project documentation
- [GITHUB_SETUP.md](GITHUB_SETUP.md) - GitHub setup guide
