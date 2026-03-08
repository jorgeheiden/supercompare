@echo off
echo ========================================
echo   SuperCompare - Iniciando Backend
echo ========================================

echo Liberando puerto 8001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do (
    echo Matando proceso %%a
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

echo Iniciando backend...
python -c "import asyncio; asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy()); import uvicorn; uvicorn.run('main:app', host='127.0.0.1', port=8001, reload=False)"
