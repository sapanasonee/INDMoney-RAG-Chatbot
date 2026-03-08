# Emergency Environment Reset — Python 3.12

Python 3.14 causes `pydantic.v1.errors.ConfigError` with ChromaDB. Use Python 3.12 for stability.

---

## 1. Teardown (run from project root or `backend/`)

**PowerShell (Windows):**
```powershell
# Remove virtual environment (use .venv or venv depending on your setup)
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force venv -ErrorAction SilentlyContinue

# Remove all __pycache__ directories in the project
Get-ChildItem -Path . -Filter __pycache__ -Recurse -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
```

**Command Prompt (Windows):**
```cmd
rmdir /s /q .venv 2>nul
rmdir /s /q venv 2>nul
for /d /r . %d in (__pycache__) do @if exist "%d" rmdir /s /q "%d"
```

**Bash (Mac/Linux):**
```bash
rm -rf .venv venv
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
```

---

## 2. Rebuild with Python 3.12

**Windows (Python Launcher):**
```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (if `python3.12` is on PATH):**
```powershell
cd backend
python3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

**If `requirements.txt` is missing**, install core packages:
```powershell
pip install fastapi uvicorn langchain-google-genai chromadb python-dotenv langchain-chroma langchain-core langchain-community sentence-transformers
```

---

## 3. Start backend on port 8001

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8001
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

---

## 4. Verify

- Open http://localhost:8001/docs — Swagger UI should load.
- Open http://localhost:8001/health — should return `{"status":"ok",...}`.
- Frontend (http://localhost:5173) should connect to the backend for chat.
