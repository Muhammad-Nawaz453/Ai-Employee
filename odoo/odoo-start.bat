@echo off
REM Odoo Docker Compose Management Script
REM Usage: odoo-start.bat [start^|stop^|restart^|status^|logs]

set COMMAND=%1

if "%COMMAND%"=="" (
    set COMMAND=start
)

cd /d "%~dp0"

if "%COMMAND%"=="start" (
    echo Starting Odoo services...
    docker-compose up -d
    echo.
    echo Odoo is starting up. This may take a minute...
    echo Access Odoo at: http://localhost:8069
    echo PgAdmin at: http://localhost:5050
    echo.
    echo To view logs: docker-compose logs -f odoo
    exit /b 0
)

if "%COMMAND%"=="stop" (
    echo Stopping Odoo services...
    docker-compose down
    echo Services stopped.
    exit /b 0
)

if "%COMMAND%"=="restart" (
    echo Restarting Odoo services...
    docker-compose restart
    echo Services restarted.
    exit /b 0
)

if "%COMMAND%"=="status" (
    echo Odoo services status:
    docker-compose ps
    exit /b 0
)

if "%COMMAND%"=="logs" (
    docker-compose logs -f %2
    exit /b 0
)

if "%COMMAND%"=="backup" (
    echo Creating backup...
    set BACKUP_FILE=backup_%date:~-4%%date:~4,2%%date:~7,2%.sql
    docker-compose exec odoo-db pg_dump -U odoo postgres > %BACKUP_FILE%
    echo Backup created: %BACKUP_FILE%
    exit /b 0
)

echo Usage: odoo-start.bat [start^|stop^|restart^|status^|logs^|backup]
echo.
echo Commands:
echo   start    - Start all Odoo services (default)
echo   stop     - Stop all services
echo   restart  - Restart all services
echo   status   - Show service status
echo   logs     - Show logs for a service
echo   backup   - Create database backup
echo.
echo Examples:
echo   odoo-start.bat
echo   odoo-start.bat stop
echo   odoo-start.bat logs odoo
echo   odoo-start.bat backup
