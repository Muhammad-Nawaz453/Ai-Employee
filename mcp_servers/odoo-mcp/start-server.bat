@echo off
REM Start Odoo MCP Server
REM Usage: start-server.bat [VAULT_PATH] [PORT]

set VAULT_PATH=%1
set PORT=%2

if "%VAULT_PATH%"=="" (
    set VAULT_PATH=D:\Ai-Employee\AI_Employee_Vault
)

if "%PORT%"=="" (
    set PORT=8811
)

echo Starting Odoo MCP Server...
echo Vault: %VAULT_PATH%
echo Port: %PORT%
echo.

cd /d "%~dp0"

set VAULT_PATH=%VAULT_PATH%
set PORT=%PORT%
set ODOO_URL=http://localhost:8069
set ODOO_DB=odoo
set ODOO_USERNAME=admin
set ODOO_PASSWORD=admin

python server.py
