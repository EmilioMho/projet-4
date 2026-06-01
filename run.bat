@echo off
setlocal
cd /d "%~dp0"

echo [%DATE% %TIME%] Generation des fiches en cours...
uv run main.py
if errorlevel 1 (
    echo ERREUR : La generation a echoue.
    exit /b 1
)

echo [%DATE% %TIME%] Envoi du rapport par mail...
uv run mail.py
if errorlevel 1 (
    echo ERREUR : L'envoi du mail a echoue.
    exit /b 1
)

echo [%DATE% %TIME%] Termine avec succes.
endlocal
