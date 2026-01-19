@echo off
REM Start the RAG API server
echo Starting RAG API server...
echo.
echo API will be available at:
echo   - http://localhost:8000
echo   - Swagger UI: http://localhost:8000/docs
echo   - Health Check: http://localhost:8000/health
echo.
echo Press Ctrl+C to stop the server
echo.

uvicorn api:app --host 0.0.0.0 --port 8000 --reload
