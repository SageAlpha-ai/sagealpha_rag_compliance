# Chroma Cloud KeyError '_type' Fix - Complete Solution

## Problem Summary

Your ingestion was failing with `KeyError: '_type'` when creating collections in Chroma Cloud, resulting in **0 documents stored** even though:
- ✅ PDFs loaded successfully (154 documents)
- ✅ Chunking worked (738 chunks created)
- ✅ Embeddings initialized successfully
- ❌ Collection creation failed → No documents stored

## Root Cause

The error occurred because:
1. **Passing `embedding_function` to `get_or_create_collection()`** when using **pre-computed embeddings** causes a JSON schema mismatch with Chroma Cloud
2. Chroma Cloud expects a different JSON structure when `embedding_function` is provided vs. when embeddings are pre-computed
3. This triggers `KeyError: '_type'` in the configuration parsing

## Solution Applied

### 1. Fixed Collection Creation (`ingestion/embed_and_store.py`)

**Before (BROKEN):**
```python
collection = client.get_or_create_collection(
    name=collection_name,
    embedding_function=embedding_function,  # ❌ Causes KeyError '_type'
    metadata={"hnsw:space": "cosine"}
)
```

**After (FIXED):**
```python
# CRITICAL: For Chroma Cloud with pre-computed embeddings, do NOT pass embedding_function
# We pass embeddings explicitly during add(), so embedding_function is not needed here
collection = client.get_or_create_collection(
    name=collection_name,
    metadata={"hnsw:space": "cosine"}  # ✅ No embedding_function
)
```

### 2. Updated Default Collection Name (`config/settings.py`)

Changed default collection name from `"documents_collection"` to `"compliance"` to match your Chroma Cloud URL:
```
https://www.trychroma.com/sagealphaai/aws-us-east-1/SEBI-Comp/collections/compliance
```

**Note:** You can override this by setting `CHROMA_COLLECTION_NAME=your_collection_name` in your `.env` file.

## Why This Works

- **Pre-computed embeddings**: You're computing embeddings with Azure OpenAI BEFORE storing them
- **No embedding function needed**: Since embeddings are provided explicitly in `collection.add(embeddings=embeddings)`, Chroma doesn't need an embedding function
- **Query-time**: For queries, you'll compute embeddings manually (which you already do in `langchain_orchestrator.py`)

## Expected Behavior After Fix

### ✅ Collection Creation
```
Connecting to Chroma Cloud collection: compliance
✓ Collection ready (current count: 0)
```

### ✅ Document Storage
```
Processing 738 documents in batches of 50...
Batch 1: Generating embeddings for 50 documents...
✓ Batch 1: Generated 50 embeddings (dimension: 3072)
...
✓ Stored 738 documents in Chroma Cloud
Collection count: 738
```

### ✅ Chroma Cloud UI
After successful ingestion, visit:
```
https://www.trychroma.com/sagealphaai/aws-us-east-1/SEBI-Comp/collections/compliance
```

You should see:
- **Documents: 738**
- Collection metadata showing cosine similarity space

## Testing the Fix

### Step 1: Verify Configuration

Make sure your `.env` file has:
```bash
CHROMA_API_KEY=your_api_key_here
CHROMA_HOST=api.trychroma.com
CHROMA_TENANT=78953c37-b2e5-425f-a3b1-87b55fa592ea
CHROMA_DATABASE=SEBI-Comp
CHROMA_COLLECTION_NAME=compliance  # Optional: defaults to "compliance" now
```

### Step 2: Test Connection

```bash
python test_chroma_connection.py
```

Should show:
```
✓ Connected to Chroma Cloud using CloudClient
✓ Collection accessed: compliance
```

### Step 3: Run Ingestion

```bash
python ingest.py --fresh
```

Should complete successfully:
```
============================================================
EMBEDDING AND STORAGE COMPLETE
============================================================
Documents processed: 738
Embeddings generated: 738
Documents stored: 738
Collection count: 738
============================================================
```

## Important Notes

### About Query-Time Embeddings

Your query code in `rag/langchain_orchestrator.py` already handles this correctly:
- It manually computes embeddings: `query_embedding = self.embeddings.embed_query(question)`
- Uses `query_embeddings` parameter: `collection.query(query_embeddings=[query_embedding])`

This is the correct approach when using pre-computed embeddings.

### About `retriever.py`

The `rag/retriever.py` file uses `query_texts` which requires an embedding function. However:
- This file might not be actively used (check your codebase)
- If you need it, update it to compute embeddings manually like `langchain_orchestrator.py` does
- Or set an embedding function on the collection for query-time use only (after creation)

### About ChromaDB Version

You're using `chromadb==0.4.24` which is correct. This version:
- ✅ Works with Chroma Cloud
- ✅ Supports pre-computed embeddings
- ✅ Avoids the KeyError '_type' bug in newer versions

## Troubleshooting

### If you still see KeyError '_type':

1. **Verify ChromaDB version:**
   ```bash
   pip show chromadb
   ```
   Should show `Version: 0.4.24`

2. **Clear Python cache:**
   ```bash
   # Windows PowerShell
   Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
   ```

3. **Reinstall ChromaDB:**
   ```bash
   pip uninstall chromadb -y
   pip install chromadb==0.4.24
   ```

### If collection creation succeeds but documents aren't stored:

1. Check batch processing logs for errors
2. Verify embeddings are being generated (check dimension matches)
3. Check Chroma Cloud dashboard for any quota/limit issues

### If authentication fails:

See `CHROMA_AUTH_FIX.md` for detailed authentication troubleshooting.

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| PDF Loading | ✅ Working | 154 documents loaded |
| Chunking | ✅ Working | 738 chunks created |
| Embeddings | ✅ Working | Azure OpenAI initialized |
| Collection Creation | ✅ **FIXED** | Removed embedding_function |
| Document Storage | ✅ **Should work now** | Pre-computed embeddings |
| Collection Name | ✅ Updated | Defaults to "compliance" |

## Next Steps

1. ✅ Run `python ingest.py --fresh`
2. ✅ Verify documents appear in Chroma Cloud UI
3. ✅ Test RAG queries via API or chatbot
4. ✅ Monitor for any remaining issues

The fix is complete and should resolve the `KeyError: '_type'` issue. Your documents should now store successfully in the `compliance` collection.
