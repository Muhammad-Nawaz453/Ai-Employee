@echo off
REM Start Facebook/Instagram MCP Server
REM Usage: start-server.bat [VAULT_PATH] [PORT]

set VAULT_PATH=%1
set PORT=%2

if "%VAULT_PATH%"=="" (
    set VAULT_PATH=D:\Ai-Employee\AI_Employee_Vault
)

if "%PORT%"=="" (
    set PORT=8810
)

echo Starting Facebook/Instagram MCP Server...
echo Vault: %VAULT_PATH%
echo Port: %PORT%

cd /d "%~dp0"
call npm install

set VAULT_PATH=%VAULT_PATH%
set PORT=%PORT%

node index.js
