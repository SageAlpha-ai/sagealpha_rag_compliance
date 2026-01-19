# How to Start the API Server

## Quick Start

### Windows (PowerShell)
```powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

Or use the batch file:
```powershell
.\start_server.bat
```

### Linux/Mac
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

Or use the shell script:
```bash
chmod +x start_server.sh
./start_server.sh
```

## Important Notes

### ✅ Correct Command
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```
- **`api:app`** - The FastAPI app is in `api.py`, not `main.py`
- **`--host 0.0.0.0`** - Allows external connections (required for server binding)
- **`--port 8000`** - Port number

### ❌ Wrong Command
```bash
uvicorn main:app --host 0.0.0.0 --port 8000  # ❌ WRONG - main.py doesn't exist
```

## Port Already in Use Error

If you see:
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000): 
only one usage of each socket address (protocol/network address/port) is normally permitted
```

**Solution**: Kill the process using port 8000

### Windows
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Linux/Mac
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

Or use a different port:
```bash
uvicorn api:app --host 0.0.0.0 --port 8001
```

## Access the API

Once started, access:
- **API Root**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Development Mode (Auto-reload)

For development with auto-reload on code changes:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

## Production Mode

For production (no auto-reload, multiple workers):
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```
