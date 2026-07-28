@echo off
title SABOR - Sistema de Gestion de Restaurante
echo ============================================
echo   SABOR - Iniciando servidor...
echo ============================================
echo.

cd /d %~dp0
call venv\Scripts\activate
echo Servidor iniciado en: http://localhost:5000
echo Presiona Ctrl+C para detener.
echo.
start http://localhost:5000
python run.py
pause
