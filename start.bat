@echo off
echo ========================================
echo   SuperCompare - DIA vs COTO
echo ========================================
echo.

echo [1/2] Iniciando Backend (FastAPI)...
cd backend
start cmd /k "pip install -r requirements.txt && uvicorn main:app --reload"
cd ..

echo [2/2] Iniciando Frontend (Angular)...
cd frontend-angular
start cmd /k "npm install && npm start"
cd ..

echo.
echo ✅ La app se abrirá en: http://localhost:4200
echo    Backend API en:       http://localhost:8000
echo.
pause
