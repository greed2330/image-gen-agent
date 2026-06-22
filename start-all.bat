@echo off
REM ============================================================
REM  image-gen-agent launcher
REM  Starts ollama + ComfyUI + backend + frontend, each in its
REM  own window so you can watch the logs live.
REM  VRAM swap order (LLM unload -> ComfyUI) is handled by the
REM  backend at generation time, so running both servers is safe.
REM ============================================================

echo [1/4] Checking ollama...
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://localhost:11434/api/version -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo     ollama not running - starting in new window
    start "ollama" cmd /k ollama serve
) else (
    echo     ollama already running - skip
)

echo [2/4] Starting ComfyUI (port 8188)...
start "ComfyUI" cmd /k "cd /d E:\ComfyUI && venv\Scripts\python.exe main.py"

echo [3/4] Starting backend (port 8000)...
start "backend" cmd /k "cd /d E:\image-gen-agent\backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [4/4] Starting frontend (port 3000)...
start "frontend" cmd /k "cd /d E:\image-gen-agent\frontend && npm run dev"

echo.
echo ============================================================
echo  All launch requests sent. Check each window for logs.
echo     ComfyUI  : http://localhost:8188
echo     backend  : http://localhost:8000/health
echo     frontend : http://localhost:3000
echo.
echo  After ComfyUI finishes loading, open http://localhost:3000
echo ============================================================
echo.
pause
