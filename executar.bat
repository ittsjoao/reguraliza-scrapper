@echo off
cd /d "%~dp0"

:: NÃO eleva o processo principal: Chrome/Selenium quebra ("chrome not
:: reachable") quando o processo que o lança está rodando como Admin. A
:: gravação da policy em HKLM (fluxo.py) pede UAC só pro próprio momento da
:: escrita, num processo separado — o robô continua sem elevação aqui.

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
python -m src.main

pause
