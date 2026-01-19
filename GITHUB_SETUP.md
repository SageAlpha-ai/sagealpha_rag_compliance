# GitHub Repository Setup Guide

## Quick Start - Push to GitHub

### 1. Initialize Git Repository (if not already done)

```bash
git init
git add .
git commit -m "Initial commit: Production-ready RAG API"
```

### 2. Create GitHub Repository

1. Go to [GitHub](https://github.com/new)
2. Create a new repository (private recommended for proprietary code)
3. Name it: `sagealpha_rag_compilance` (or your preferred name)
4. **DO NOT** initialize with README, .gitignore, or license (we already have these)

### 3. Connect and Push

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/sagealpha_rag_compilance.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Repository Structure

Your repository now includes:

```
sagealpha_rag_compilance/
├── .github/
│   └── workflows/
│       └── deploy.yml          # CI/CD workflow
├── config/                      # Configuration management
├── ingestion/                   # Document ingestion
├── rag/                        # RAG pipeline
├── vectorstore/                # Chroma Cloud client
├── api.py                      # FastAPI application
├── ingest.py                   # Ingestion script
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version
├── Procfile                    # Heroku deployment
├── render.yaml                 # Render.com config
├── .gitignore                 # Git ignore rules
├── env.example                # Environment template
├── README.md                  # Main documentation
├── DEPLOYMENT.md              # Deployment guide
├── DEPLOYMENT_CHECKLIST.md   # Pre-deployment checklist
├── CONTRIBUTING.md            # Contribution guidelines
└── LICENSE                    # License file
```

## Important Files Explained

### Deployment Files

- **`render.yaml`** - Render.com deployment configuration
- **`Procfile`** - Heroku deployment configuration
- **`runtime.txt`** - Python version specification

### Configuration Files

- **`env.example`** - Environment variable template (copy to `.env` locally)
- **`requirements.txt`** - Python package dependencies
- **`.gitignore`** - Files to exclude from Git

### Documentation Files

- **`README.md`** - Main project documentation
- **`DEPLOYMENT.md`** - Detailed deployment instructions
- **`DEPLOYMENT_CHECKLIST.md`** - Pre-deployment verification
- **`CONTRIBUTING.md`** - Development guidelines
- **`LICENSE`** - License information

## Security Checklist

Before pushing to GitHub:

- [x] `.env` is in `.gitignore` (never commit secrets)
- [x] No API keys in code
- [x] No passwords in code
- [x] No connection strings in code
- [x] `env.example` has placeholder values only
- [x] Sensitive files excluded via `.gitignore`

## GitHub Repository Settings

### Recommended Settings:

1. **Repository Visibility**: Private (for proprietary code)
2. **Branch Protection**: Enable for `main` branch
3. **Secrets**: Store environment variables in GitHub Secrets (for CI/CD)
4. **Actions**: Enable GitHub Actions (for CI/CD workflow)

### GitHub Secrets (for CI/CD)

If using GitHub Actions, add these secrets:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `CHROMA_API_KEY`
- `CHROMA_TENANT`
- `CHROMA_DATABASE`
- (and other sensitive variables)

## Next Steps After GitHub Push

1. **Connect to Deployment Platform:**
   - Render.com: Connect GitHub repo
   - Heroku: Connect GitHub repo
   - Other platforms: Follow platform-specific instructions

2. **Set Environment Variables:**
   - Use platform dashboard to set all variables from `env.example`
   - Never commit `.env` file

3. **Deploy:**
   - Render: Auto-deploys on push to `main`
   - Heroku: `git push heroku main`

4. **Run Ingestion:**
   - After deployment, run: `python ingest.py --fresh`
   - Use platform shell/console

## CI/CD Workflow

The `.github/workflows/deploy.yml` file provides:
- Automatic testing on push
- Import verification
- Deployment readiness checks

To enable:
1. Push code to GitHub
2. Go to Actions tab
3. Workflow runs automatically

## Repository Best Practices

### Commit Messages

Use clear, descriptive commit messages:
```bash
git commit -m "Add: Feature description"
git commit -m "Fix: Bug description"
git commit -m "Update: Documentation"
```

### Branching Strategy

- `main` - Production-ready code
- `develop` - Development branch (optional)
- `feature/*` - Feature branches
- `fix/*` - Bug fix branches

### Tags

Tag releases:
```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Troubleshooting

### "Repository not found"

- Check repository name matches
- Verify you have access
- Check remote URL: `git remote -v`

### "Permission denied"

- Check GitHub credentials
- Use SSH keys or Personal Access Token
- Verify repository permissions

### "Large file" errors

- Check `.gitignore` includes large files
- Use Git LFS for large files (if needed)
- Remove large files from history if committed

## Support

For GitHub-specific issues:
- Check GitHub documentation
- Review repository settings
- Verify branch protection rules
- Check Actions logs (if using CI/CD)
