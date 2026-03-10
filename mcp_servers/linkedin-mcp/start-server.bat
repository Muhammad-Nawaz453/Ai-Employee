@echo off
REM Start LinkedIn MCP Server
REM Usage: start-linkedin-mcp.bat [vault-path]

set VAULT_PATH=%~1
if "%VAULT_PATH%"=="" set VAULT_PATH=%CD%\AI_Employee_Vault

echo =============================================
echo LinkedIn MCP Server - Silver Tier
echo =============================================
echo Vault Path: %VAULT_PATH%
echo Session Path: %CD%\mcp_servers\linkedin-mcp\session
echo =============================================
echo.
echo Starting LinkedIn MCP Server...
echo Press Ctrl+C to stop
echo.

cd /d "%~dp0linkedin-mcp"

REM Set environment variables
set VAULT_PATH=%VAULT_PATH%
set LINKEDIN_SESSION_PATH=%CD%\session
set HEADLESS=true

REM Install dependencies if needed
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

REM Start the server
node index.js
