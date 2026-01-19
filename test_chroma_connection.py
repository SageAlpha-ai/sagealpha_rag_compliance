#!/usr/bin/env python3
"""
Test Chroma Cloud connection after fix.

Run this script to verify that the ChromaDB KeyError '_type' fix is working.
"""

import sys
sys.path.insert(0, ".")

print("=" * 60)
print("TESTING CHROMA CLOUD CONNECTION")
print("=" * 60)
print()

try:
    from vectorstore.chroma_client import get_chroma_client, get_collection
    from config.settings import get_config, validate_config
    
    # Step 1: Load and validate config
    print("[1/4] Loading configuration...")
    try:
        config = get_config()
        validate_config(config)
        print("✓ Configuration loaded")
        
        # Check API key is set
        if not config.chroma_cloud.api_key or not config.chroma_cloud.api_key.strip():
            print("\n✗ ERROR: CHROMA_API_KEY is not set or is empty!")
            print("Please set it in your .env file or environment variables.")
            print("Get your API key from https://trychroma.com")
            sys.exit(1)
        else:
            api_key_display = '*' * (len(config.chroma_cloud.api_key) - 8) + config.chroma_cloud.api_key[-8:] if len(config.chroma_cloud.api_key) > 8 else '***'
            print(f"✓ API Key: {api_key_display}")
    except ValueError as e:
        print(f"\n✗ Configuration error: {e}")
        sys.exit(1)
    print()
    
    # Step 2: Create client
    print("[2/4] Creating Chroma Cloud client...")
    client = get_chroma_client()
    print("✓ Client created successfully")
    print()
    
    # Step 3: Test heartbeat
    print("[3/4] Testing connection (heartbeat)...")
    try:
        heartbeat = client.heartbeat()
        print(f"✓ Heartbeat successful: {heartbeat}")
    except Exception as e:
        print(f"⚠ Heartbeat check failed (non-critical): {e}")
        print("  Continuing anyway...")
    print()
    
    # Step 4: Test collection access/creation
    print("[4/4] Testing collection access...")
    try:
        # Try to get existing collection first
        collection = get_collection(create_if_missing=False)
        print(f"✓ Collection accessed: {collection.name}")
        doc_count = collection.count()
        print(f"✓ Document count: {doc_count}")
        
        if doc_count > 0:
            # Get a sample document
            results = collection.get(limit=1)
            if results.get('documents'):
                print(f"\n  Sample document preview:")
                sample_text = results['documents'][0]
                print(f"    Text: {sample_text[:100]}...")
                if results.get('metadatas'):
                    print(f"    Metadata keys: {list(results['metadatas'][0].keys())}")
        else:
            print("\n  ⚠ Collection is empty. Run 'python ingest.py --fresh' to populate it.")
            
    except Exception as e:
        # If collection doesn't exist, try creating it
        print(f"  Collection not found, testing creation...")
        try:
            collection = get_collection(create_if_missing=True)
            print(f"✓ Collection created successfully: {collection.name}")
            print(f"✓ Document count: {collection.count()}")
        except Exception as create_error:
            print(f"✗ Failed to create collection: {create_error}")
            raise
    
    print()
    print("=" * 60)
    print("SUCCESS: Chroma Cloud connection is working!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. If collection is empty, run: python ingest.py --fresh")
    print("  2. Test RAG queries via: python -c \"from rag.langchain_orchestrator import answer_query_simple; print(answer_query_simple('test query'))\"")
    print("  3. Or start the API server: uvicorn api:app --host 0.0.0.0 --port 8000")
    print()
    
except Exception as e:
    print()
    print("=" * 60)
    print("ERROR: Connection test failed")
    print("=" * 60)
    print(f"Error: {e}")
    print()
    print("Full traceback:")
    import traceback
    traceback.print_exc()
    print()
    print("Troubleshooting:")
    print("  1. Verify ChromaDB version: pip show chromadb (should be 0.4.24)")
    print("  2. Check environment variables are set correctly")
    print("  3. Verify Chroma Cloud credentials at https://trychroma.com")
    print()
    sys.exit(1)
