@echo off
setlocal EnableDelayedExpansion
REM Script de execução do SIC para Windows
REM Ativa o ambiente virtual e executa o app.

SET SCRIPT_DIR=%~dp0
SET PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe

IF NOT EXIST "%PYTHON%" (
    echo [ERRO] .venv nao encontrado.
    echo Execute: uv venv --python 3.14 .venv ^&^& uv pip install -r requirements.txt
    pause
    exit /b 1
)

REM Adiciona Tesseract ao PATH se instalado no local padrão
SET TESSERACT_PATH=C:\Program Files\Tesseract-OCR
IF EXIST "%TESSERACT_PATH%\tesseract.exe" (
    SET "PATH=%TESSERACT_PATH%;!PATH!"
)

"%PYTHON%" "%SCRIPT_DIR%main.py" %*
