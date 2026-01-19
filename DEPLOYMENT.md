# Deployment Guide

This guide covers deploying the RAG API service to various platforms.

## Prerequisites

Before deploying, ensure you have:

1. ✅ All environment variables configured (see `.env.example`)
2. ✅ Documents ingested into Chroma Cloud (`python ingest.py --fresh`)
3. ✅ ChromaDB collection contains documents (check via Chroma Cloud UI)

## Platform-Specific Deployment

### Render.com (Recommended)

Render automatically detects `render.yaml` for configuration.

#### Steps:

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Deploy to Render"
   git push origin main
   ```

2. **Connect Repository:**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

3. **Set Environment Variables:**
   - In Render dashboard, go to your service → Environment
   - Add all variables from `.env.example`
   - Mark sensitive variables as "Secret"

4. **Deploy:**
   - Render will automatically deploy on push
   - Or click "Manual Deploy" → "Deploy latest commit"

5. **Verify:**
   - Check logs for startup messages
   - Visit `https://your-service.onrender.com/health`
   - Visit `https://your-service.onrender.com/docs` for Swagger UI

#### Render Configuration:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT --workers 1`
- **Python Version**: 3.11.0 (set in `render.yaml`)

---

### Heroku

#### Steps:

1. **Install Heroku CLI:**
   ```bash
   # Windows: Download from https://devcenter.heroku.com/articles/heroku-cli
   # Or use: npm install -g heroku
   ```

2. **Login and Create App:**
   ```bash
   heroku login
   heroku create your-app-name
   ```

3. **Set Environment Variables:**
   ```bash
   heroku config:set AZURE_OPENAI_API_KEY=your_key
   heroku config:set AZURE_OPENAI_ENDPOINT=https://...
   # ... (set all variables from .env.example)
   ```

4. **Deploy:**
   ```bash
   git push heroku main
   ```

5. **Run Ingestion (One-time):**
   ```bash
   heroku run python ingest.py --fresh
   ```

6. **Verify:**
   ```bash
   heroku open
   # Visit /health endpoint
   ```

#### Heroku Configuration:

- Uses `Procfile` for start command
- Automatically detects Python from `requirements.txt`
- Uses `runtime.txt` for Python version

---

### AWS Elastic Beanstalk

#### Steps:

1. **Install EB CLI:**
   ```bash
   pip install awsebcli
   ```

2. **Initialize:**
   ```bash
   eb init -p python-3.11 rag-api
   ```

3. **Create Environment:**
   ```bash
   eb create rag-api-env
   ```

4. **Set Environment Variables:**
   ```bash
   eb setenv AZURE_OPENAI_API_KEY=your_key ...
   ```

5. **Deploy:**
   ```bash
   eb deploy
   ```

6. **Open:**
   ```bash
   eb open
   ```

---

---

### Azure App Service

#### Steps:

1. **Create App Service:**
   ```bash
   az webapp create \
     --resource-group your-resource-group \
     --plan your-app-service-plan \
     --name your-app-name \
     --runtime "PYTHON:3.11"
   ```

2. **Configure:**
   ```bash
   az webapp config appsettings set \
     --resource-group your-resource-group \
     --name your-app-name \
     --settings AZURE_OPENAI_API_KEY=your_key ...
   ```

3. **Deploy:**
   ```bash
   # Using Git
   az webapp deployment source config-local-git \
     --resource-group your-resource-group \
     --name your-app-name
   
   git remote add azure https://your-app-name.scm.azurewebsites.net/your-app-name.git
   git push azure main
   ```

---

## Post-Deployment Checklist

After deploying, verify:

- [ ] **Health Check**: `GET /health` returns `200 OK`
- [ ] **ChromaDB Connection**: Health check shows `chroma_connected: true`
- [ ] **Document Count**: Health check shows `document_count > 0`
- [ ] **API Endpoints**: `GET /docs` shows Swagger UI
- [ ] **Query Endpoint**: `POST /query` returns responses
- [ ] **Logs**: Check application logs for errors

## Running Ingestion in Production

After deployment, you need to ingest documents:

### Option 1: One-time Script Run

```bash
# Render
render.com → Shell → Run: python ingest.py --fresh

# Heroku
heroku run python ingest.py --fresh
```

### Option 2: Scheduled Job (Recommended)

Set up a cron job or scheduled task:

```bash
# Run ingestion daily at 2 AM
0 2 * * * cd /app && python ingest.py --fresh
```

Or use platform-specific schedulers:
- **Render**: Cron Jobs
- **Heroku**: Heroku Scheduler addon
- **AWS**: EventBridge + Lambda
- **GCP**: Cloud Scheduler

## Environment Variables Reference

See `.env.example` for complete list. Required variables:

### Azure OpenAI
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`
- `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME`

### Azure Blob Storage
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_BLOB_CONTAINER_NAME`

### Chroma Cloud
- `CHROMA_HOST` (default: `api.trychroma.com`)
- `CHROMA_API_KEY`
- `CHROMA_TENANT`
- `CHROMA_DATABASE`
- `CHROMA_COLLECTION_NAME` (default: `compliance`)

### Optional
- `RAG_API_KEY` - API authentication (leave empty to disable)
- `CORS_ORIGINS` - CORS configuration (default: `*`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Troubleshooting Deployment

### "ChromaDB collection is EMPTY"

**Solution**: Run ingestion:
```bash
python ingest.py --fresh
```

### "ModuleNotFoundError"

**Solution**: Ensure `requirements.txt` is up to date and all dependencies are installed.

### "Port already in use"

**Solution**: Use `$PORT` environment variable (set by platform) or change port in start command.

### "Environment variable not set"

**Solution**: Verify all required variables are set in platform dashboard.

### "ChromaDB v1 API deprecated"

**Solution**: Ensure ChromaDB version >= 1.4.0 in `requirements.txt`.

## Monitoring

### Health Endpoint

Monitor `/health` endpoint:
- Returns `200 OK` if healthy
- Returns `503` if degraded (ChromaDB disconnected)
- Includes document count

### Logs

Check application logs for:
- Startup messages
- Query processing
- Error messages
- ChromaDB connection status

### Metrics to Monitor

- Response time for `/query` endpoint
- ChromaDB document count
- Error rate
- API usage/rate limiting

## Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Use secrets management** - Use platform secrets managers
3. **Enable API authentication** - Set `RAG_API_KEY` in production
4. **Restrict CORS** - Set `CORS_ORIGINS` to specific domains
5. **Use HTTPS** - All platforms provide HTTPS by default
6. **Regular updates** - Keep dependencies updated

## Scaling

### Horizontal Scaling

- **Render**: Auto-scaling available in paid plans
- **Heroku**: Use multiple dynos
- **Azure App Service**: Auto-scales based on traffic

### Vertical Scaling

- Increase worker count: `--workers 4` (adjust based on CPU)
- Increase memory allocation
- Use faster CPU instances

### Database Scaling

- Chroma Cloud handles scaling automatically
- Monitor usage in Chroma Cloud dashboard

## Backup and Recovery

### Chroma Cloud

- Chroma Cloud provides automatic backups
- Check Chroma Cloud dashboard for backup settings

### Application Code

- Use Git for version control
- Tag releases: `git tag v1.0.0`
- Keep deployment history

### Environment Variables

- Export environment variables to secure storage
- Document all required variables
- Use secrets management tools

## Support

For deployment issues:
1. Check application logs
2. Verify environment variables
3. Test health endpoint
4. Review ChromaDB connection status
5. Check platform-specific documentation
