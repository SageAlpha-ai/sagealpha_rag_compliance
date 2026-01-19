# ChromaDB KeyError '_type' Fix - Step by Step

## Summary of Changes

This fix addresses the `KeyError: '_type'` bug in ChromaDB that occurs when creating collections in Chroma Cloud. The issue is caused by version incompatibilities in ChromaDB versions >0.4.24 or >1.0.0.

## Changes Made

### 1. ✅ Updated `requirements.txt`
- **Changed**: `chromadb>=0.5.16,<1.0.0` → `chromadb==0.4.24`
- **Reason**: Version 0.4.24 is a stable version that doesn't have the JSON parsing bug

### 2. ✅ Fixed `vectorstore/chroma_client.py`
- **Changed**: Replaced `chromadb.CloudClient` with `chromadb.HttpClient`
- **Added**: Proper `Settings` configuration with `allow_reset=True` and `anonymized_telemetry=False`
- **Added**: Fallback handling for API key authentication (supports both headers parameter and environment variable)
- **Reason**: HttpClient is more stable for Chroma Cloud connections and avoids the KeyError bug

### 3. ✅ Verified `ingestion/embed_and_store.py`
- **Status**: No changes needed - already uses the correct client setup
- The file correctly uses `get_chroma_client()` which now returns the fixed HttpClient

## Next Steps - Testing the Fix

### Step 1: Install the Correct ChromaDB Version

In your virtual environment, run:

```bash
# Activate your virtual environment first
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Then uninstall and reinstall ChromaDB
pip uninstall chromadb -y
pip install chromadb==0.4.24
```

### Step 2: Verify Installation

```bash
pip show chromadb
```

You should see `Version: 0.4.24`

### Step 3: Test Chroma Cloud Connection

Create a simple test script `test_chroma_connection.py`:

```python
"""Test Chroma Cloud connection after fix."""
import sys
sys.path.insert(0, ".")

from vectorstore.chroma_client import get_chroma_client, get_collection

print("Testing Chroma Cloud connection...")
try:
    client = get_chroma_client()
    print("✓ Client created successfully")
    
    # Test heartbeat
    heartbeat = client.heartbeat()
    print(f"✓ Heartbeat: {heartbeat}")
    
    # Test collection access
    collection = get_collection(create_if_missing=False)
    print(f"✓ Collection accessed: {collection.name}")
    print(f"✓ Document count: {collection.count()}")
    
    print("\n" + "=" * 60)
    print("SUCCESS: Chroma Cloud connection working!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

Run it:
```bash
python test_chroma_connection.py
```

### Step 4: Test Full Ingestion Pipeline

If the connection test passes, try running your ingestion:

```bash
python ingest.py --fresh
```

This will:
1. Load documents from Azure Blob Storage
2. Load local documents
3. Chunk all documents
4. Embed using Azure OpenAI
5. Store in Chroma Cloud

### Step 5: Verify Documents Were Stored

After ingestion completes, check the collection:

```python
from vectorstore.chroma_client import get_collection

collection = get_collection(create_if_missing=False)
print(f"Total documents: {collection.count()}")

# Get a sample document
results = collection.get(limit=1)
if results['documents']:
    print(f"\nSample document:")
    print(f"  Text: {results['documents'][0][:200]}...")
    print(f"  Metadata: {results['metadatas'][0]}")
```

## Troubleshooting

### If you still see KeyError '_type':

1. **Verify ChromaDB version**:
   ```bash
   pip show chromadb
   ```
   Must be exactly `0.4.24`

2. **Clear Python cache**:
   ```bash
   # Delete __pycache__ directories
   Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
   ```

3. **Check environment variables**:
   Make sure all Chroma Cloud env vars are set:
   - `CHROMA_HOST`
   - `CHROMA_API_KEY`
   - `CHROMA_TENANT`
   - `CHROMA_DATABASE`

4. **Try alternative version**:
   If 0.4.24 doesn't work, try 1.0.0:
   ```bash
   pip install chromadb==1.0.0
   ```

### If connection fails:

1. **Check API key**: Verify your `CHROMA_API_KEY` is correct
2. **Check host**: Should be `api.trychroma.com` (no https:// prefix)
3. **Check tenant/database**: Verify these match your Chroma Cloud dashboard

### If LangChain compatibility issues:

The current requirements specify `langchain>=0.1.0,<1.0.0` which should be compatible. If you encounter issues:

```bash
pip install langchain==0.1.0 langchain-openai==0.0.5 langchain-community==0.0.10
```

## Expected Behavior After Fix

✅ **Before Fix**: `KeyError: '_type'` when calling `get_or_create_collection()`

✅ **After Fix**: 
- Collection creation succeeds
- Documents can be stored
- No JSON parsing errors
- RAG queries work correctly

## Additional Notes

- The fix uses `HttpClient` instead of `CloudClient` for better compatibility
- Settings are explicitly configured to avoid telemetry errors
- API key authentication is handled with fallback for different ChromaDB versions
- All existing code continues to work - no breaking changes to your API

## Support

If issues persist after following these steps:
1. Check ChromaDB GitHub issues: https://github.com/chroma-core/chroma/issues
2. Verify your Chroma Cloud account status at https://trychroma.com
3. Review the full error traceback for specific error messages
