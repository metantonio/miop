@echo off
title Miop - Asistente de Vision
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual en .venv.
    echo Creando entorno e instalando dependencias...
    python -m venv .venv
    .\.venv\Scripts\pip.exe install mss opencv-python scipy pillow numpy pywin32
)

echo Iniciando Miop...
start "" ".\.venv\Scripts\pythonw.exe" main.py
