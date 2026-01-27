# Deployment Guide: GitHub + Render

Complete guide to deploy your RAG API to Render.com using GitHub.

## 📋 Prerequisites

- GitHub account
- Render.com account (free tier available)
- All required API keys and credentials (Azure OpenAI, Chroma Cloud, etc.)

## 🚀 Quick Deployment Steps

### 1. Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: RAG API ready for deployment"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 2. Connect to Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account (if not already connected)
4. Select your repository
5. Render will auto-detect `render.yaml` configuration

### 3. Set Environment Variables

In Render dashboard, go to your service → **Environment** → Add these variables:

#### Required Variables (set these manually):

```
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME=text-embedding-3-large
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_BLOB_CONTAINER_NAME=your_container_name
CHROMA_API_KEY=your_chroma_api_key
CHROMA_TENANT=your_tenant_id
CHROMA_DATABASE=your_database_name
```

#### Optional Variables:

```
RAG_API_KEY=your_api_key_for_auth  # Leave empty to disable
CORS_ORIGINS=*  # Or specific origins: https://example.com,https://app.example.com
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

**Note**: Variables marked as `sync: false` in `render.yaml` must be set manually in Render dashboard.

### 4. Deploy

1. Click **"Create Web Service"** in Render
2. Render will:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Start the service using the command in `Procfile` or `render.yaml`
3. Wait for deployment to complete (usually 2-5 minutes)

### 5. Verify Deployment

Once deployed, you'll get a URL like: `https://your-app.onrender.com`

- **API Root**: `https://your-app.onrender.com/`
- **Swagger UI**: `https://your-app.onrender.com/docs`
- **Health Check**: `https://your-app.onrender.com/health`

## 📁 Deployment Files Explained

### `render.yaml`
- Render configuration file
- Defines service type, build commands, and environment variables
- Auto-detected by Render

### `Procfile`
- Simple process file
- Used by Render if `render.yaml` is not present
- Format: `web: command`

### `requirements.txt`
- Python dependencies
- Installed during build: `pip install -r requirements.txt`

### `runtime.txt`
- Python version specification
- Format: `python-3.11.0`

### `.gitignore`
- Excludes sensitive files from Git
- Includes: `.env`, `venv/`, `__pycache__/`, etc.

## 🔧 Configuration Details

### Port Configuration

The app automatically uses Render's `PORT` environment variable:
- **Render**: Uses `$PORT` (set automatically by Render)
- **Local Dev**: Defaults to `8000` if `PORT` not set

### Environment Detection

The app detects production environment:
- Checks for `RENDER` environment variable
- In production, skips loading `.env` file
- All config comes from Render environment variables

### Startup Behavior

On startup, the app:
1. ✅ Checks for missing environment variables
2. ✅ Logs clear error messages if config is missing
3. ✅ Continues running even if RAG initialization fails
4. ✅ Provides health check endpoint for Render

## 🐛 Troubleshooting

### Deployment Fails

**Check logs in Render dashboard:**
- Build logs: Check if `pip install` succeeded
- Runtime logs: Check for startup errors

**Common issues:**
- Missing environment variables → Check startup logs
- Python version mismatch → Verify `runtime.txt`
- Dependency conflicts → Check `requirements.txt`

### App Starts But RAG Doesn't Work

1. Check startup logs for missing environment variables
2. Verify all required variables are set in Render dashboard
3. Check ChromaDB connection status in logs
4. Ensure documents are ingested (run `ingest.py` locally first)

### Health Check Fails

- Check `/health` endpoint: `https://your-app.onrender.com/health`
- Should return `{"status": "healthy"}` or `{"status": "degraded"}`
- `degraded` means ChromaDB connection failed, but app is running

## 🔄 Updating Deployment

### Automatic Updates

Render automatically deploys when you push to your main branch:
```bash
git add .
git commit -m "Update code"
git push origin main
```

### Manual Deploy

1. Go to Render dashboard
2. Click **"Manual Deploy"** → **"Deploy latest commit"**

### Rollback

1. Go to Render dashboard
2. Click **"Events"** tab
3. Find previous successful deployment
4. Click **"Redeploy"**

## 📊 Monitoring

### Logs

View logs in Render dashboard:
- **Logs** tab shows real-time application logs
- **Events** tab shows deployment history

### Health Monitoring

Render automatically monitors:
- HTTP health checks (uses `/health` endpoint)
- Service availability
- Automatic restarts on failure

## 🔒 Security Best Practices

1. **Never commit secrets**:
   - ✅ Use `.gitignore` to exclude `.env`
   - ✅ Set all secrets in Render dashboard
   - ✅ Use `env.example` for documentation

2. **API Authentication**:
   - Set `RAG_API_KEY` in Render to enable authentication
   - All `/query` requests require `x-api-key` header

3. **CORS Configuration**:
   - Set `CORS_ORIGINS` to specific domains in production
   - Don't use `*` in production (only for development)

## 📝 Post-Deployment Checklist

- [ ] Service is running (check Render dashboard)
- [ ] Health endpoint returns 200: `/health`
- [ ] Swagger UI is accessible: `/docs`
- [ ] All environment variables are set
- [ ] Startup logs show no errors
- [ ] ChromaDB connection successful (check logs)
- [ ] Test query endpoint: `POST /query`
- [ ] API authentication works (if enabled)

## 🆘 Support

If you encounter issues:

1. Check Render logs first
2. Verify all environment variables are set
3. Check startup logs for missing config
4. Review [DEPLOYMENT.md](DEPLOYMENT.md) for detailed info
5. Check [README.md](README.md) for general setup

## 🎉 Success!

Once deployed, your RAG API is:
- ✅ Accessible via HTTPS
- ✅ Auto-scaling (Render free tier)
- ✅ Monitored and auto-restarts on failure
- ✅ Ready for production use

Your API URL: `https://your-app.onrender.com`
