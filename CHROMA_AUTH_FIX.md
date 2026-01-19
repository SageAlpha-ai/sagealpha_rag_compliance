# Chroma Cloud Authentication Fix

## Problem
Chroma Cloud ingestion was failing with `401 Unauthorized` error:
```
ValueError: {"error":"ChromaError","message":"Permission denied."}
```

This occurred because the API key was not being properly passed to ChromaDB for authentication.

## Solution

### Changes Made

1. **Updated `vectorstore/chroma_client.py`**:
   - Added API key validation before creating client
   - Set environment variables (`CHROMA_API_KEY`, `CHROMA_TENANT`, `CHROMA_DATABASE`) before client creation
   - Try `CloudClient` first (recommended for Chroma Cloud)
   - Fall back to `HttpClient` if CloudClient fails or doesn't exist
   - Added comprehensive error messages with troubleshooting steps

### Key Features

- **API Key Validation**: Checks that `CHROMA_API_KEY` is set before attempting connection
- **Dual Client Support**: Tries CloudClient first, falls back to HttpClient if needed
- **Better Error Messages**: Provides specific guidance when authentication fails
- **Environment Variable Setup**: Automatically sets required env vars for ChromaDB to read

## Setup Instructions

### 1. Get Your Chroma Cloud API Key

1. Sign up or log in at https://trychroma.com
2. Navigate to your dashboard
3. Copy your API key

### 2. Set Environment Variables

Add to your `.env` file:
```bash
CHROMA_API_KEY=your_api_key_here
CHROMA_HOST=api.trychroma.com
CHROMA_TENANT=78953c37-b2e5-425f-a3b1-87b55fa592ea
CHROMA_DATABASE=SEBI-Comp
CHROMA_COLLECTION_NAME=documents_collection
```

**Important**: Replace `your_api_key_here` with your actual API key from Chroma Cloud.

### 3. Verify Configuration

Run the test script:
```bash
python test_chroma_connection.py
```

This will:
- Validate your configuration
- Test the connection to Chroma Cloud
- Verify authentication works
- Check collection access

### 4. Run Ingestion

Once the connection test passes:
```bash
python ingest.py --fresh
```

## Troubleshooting

### Error: "CHROMA_API_KEY environment variable is not set"

**Solution**: 
- Check your `.env` file exists and contains `CHROMA_API_KEY=...`
- Verify the variable name is exactly `CHROMA_API_KEY` (case-sensitive)
- Make sure you're running from the project root directory

### Error: "Authentication failed: Permission denied (401 Unauthorized)"

**Possible causes**:
1. API key is incorrect or expired
2. API key doesn't have access to the specified tenant/database
3. API key format is wrong (should not include "Bearer " prefix)

**Solution**:
1. Verify your API key at https://trychroma.com
2. Check that tenant and database match your Chroma Cloud dashboard
3. Ensure API key is set correctly in `.env` file (no quotes, no extra spaces)

### Error: "KeyError '_type'"

**Solution**: 
- This suggests ChromaDB version issue
- Verify you have ChromaDB 0.4.24: `pip show chromadb`
- If not, install it: `pip install chromadb==0.4.24`

### Error: "CloudClient not available"

**Solution**:
- This is normal if using ChromaDB 0.4.24
- The code will automatically fall back to HttpClient
- HttpClient should work fine with proper environment variables set

## How It Works

1. **Configuration Loading**: Reads `CHROMA_API_KEY` from `.env` file via `config.settings`
2. **Validation**: Checks API key is present and not empty
3. **Environment Setup**: Sets `CHROMA_API_KEY`, `CHROMA_TENANT`, `CHROMA_DATABASE` in environment
4. **Client Creation**: 
   - First tries `CloudClient` (if available) with explicit `api_key` parameter
   - Falls back to `HttpClient` if CloudClient fails or doesn't exist
   - HttpClient reads authentication from environment variables
5. **Verification**: Tests connection with `heartbeat()` or `get_user_identity()`

## Testing

After applying the fix, test with:

```bash
# Test connection
python test_chroma_connection.py

# Test full ingestion
python ingest.py --fresh

# Test RAG query (after ingestion)
python -c "from rag.langchain_orchestrator import answer_query_simple; print(answer_query_simple('test query'))"
```

## Expected Output

When working correctly, you should see:
```
============================================================
CONNECTING TO CHROMA CLOUD
============================================================
Host: api.trychroma.com
Tenant: 78953c37-b2e5-425f-a3b1-87b55fa592ea
Database: SEBI-Comp
API Key: ********your_key
Attempting connection with CloudClient (recommended for Chroma Cloud)...
✓ Authenticated to Chroma Cloud (user: ...)
============================================================
```

## Additional Notes

- The fix maintains backward compatibility - existing code continues to work
- Both CloudClient and HttpClient are supported
- Error messages provide specific guidance for common issues
- API key is masked in logs (only last 8 characters shown)

## Support

If issues persist:
1. Verify ChromaDB version: `pip show chromadb` (should be 0.4.24)
2. Check Chroma Cloud dashboard for API key validity
3. Verify network connectivity to `api.trychroma.com`
4. Review full error traceback for specific error messages
