#!/bin/bash
echo "========================================"
echo "  SuperCompare - DIA vs COTO"
echo "========================================"
echo ""

echo "▶ Iniciando Backend (FastAPI)..."
cd backend
pip install -r requirements.txt
uvicorn main:app --reload &
BACKEND_PID=$!
cd ..

echo "▶ Iniciando Frontend (Angular)..."
cd frontend-angular
npm install
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ App corriendo en:  http://localhost:4200"
echo "   Backend API en:    http://localhost:8000"
echo ""
echo "Presioná Ctrl+C para detener ambos servidores"

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
