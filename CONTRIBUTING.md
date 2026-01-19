# Contributing Guide

## Development Setup

1. **Fork and Clone:**
   ```bash
   git clone https://github.com/your-username/sagealpha_rag_compilance.git
   cd sagealpha_rag_compilance
   ```

2. **Create Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run Tests:**
   ```bash
   python test_chroma_connection.py
   python ingest.py --fresh
   ```

## Code Style

- Follow PEP 8 style guide
- Use type hints where possible
- Add docstrings to functions and classes
- Keep functions focused and small

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Test locally
4. Commit: `git commit -m "Add feature: description"`
5. Push: `git push origin feature/your-feature`
6. Create Pull Request on GitHub

## Testing

Before submitting PR:
- [ ] Code runs without errors
- [ ] All imports work
- [ ] Health endpoint returns 200
- [ ] Query endpoint works
- [ ] No sensitive data committed
