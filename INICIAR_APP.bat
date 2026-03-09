@echo off
REM ─────────────────────────────────────────────────────────
REM  Monitor de Caja Chica — Arranque rápido local
REM  Doble clic en este archivo para abrir la app en el navegador
REM ─────────────────────────────────────────────────────────
title Monitor de Caja Chica

set PYTHON=C:\Users\GRIZZLY\AppData\Local\Programs\Python\Python313\python.exe
set STREAMLIT=C:\Users\GRIZZLY\AppData\Local\Programs\Python\Python313\Scripts\streamlit.exe
set APP_DIR=%~dp0

cd /d "%APP_DIR%"

echo.
echo  ============================================
echo   Monitor de Caja Chica - Iniciando...
echo  ============================================
echo.
echo  URL local: http://localhost:8501
echo  Cierra esta ventana para detener el servidor.
echo.

"%STREAMLIT%" run app.py --server.port 8501

pause
