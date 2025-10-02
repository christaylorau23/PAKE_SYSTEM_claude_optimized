@echo off
:: PAKE Service Watchdog - Ensures service is always running
:: Runs every 5 minutes via Task Scheduler

setlocal enabledelayedexpansion

:: Check if service is running
sc query PAKEKnowledgeService | find "RUNNING" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    :: Service is running, check health
    if exist "D:\Projects\PAKE_SYSTEM\logs\service_health.json" (
        :: Read health status (simplified check)
        findstr "service_running.*true" "D:\Projects\PAKE_SYSTEM\logs\service_health.json" >nul 2>&1
        if %ERRORLEVEL% neq 0 (
            echo [%date% %time%] Service health check failed, restarting... >> "D:\Projects\PAKE_SYSTEM\logs\watchdog.log"
            goto RESTART_SERVICE
        )
    )
    goto END
)

:RESTART_SERVICE
echo [%date% %time%] PAKE Service not running, attempting restart... >> "D:\Projects\PAKE_SYSTEM\logs\watchdog.log"

:: Try to start service
net start PAKEKnowledgeService >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [%date% %time%] Service restarted successfully >> "D:\Projects\PAKE_SYSTEM\logs\watchdog.log"
    goto END
)

:: Service start failed, try alternative
echo [%date% %time%] Service start failed, trying alternative method... >> "D:\Projects\PAKE_SYSTEM\logs\watchdog.log"
sc start PAKEKnowledgeService >nul 2>&1

timeout /t 5 /nobreak >nul

:: Final check
sc query PAKEKnowledgeService | find "RUNNING" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [%date% %time%] Service started successfully via alternative method >> "D:\Projects\PAKE_SYSTEM\logs\watchdog.log"
) else (
    echo [%date% %time%] WARNING: Service failed to start, will retry next cycle >> "D:\Projects\PAKE_SYSTEM\logs\watchdog.log"

    :: Emergency fallback - start manual process
    tasklist /fi "imagename eq python.exe" /fi "windowtitle eq *automated_vault_watcher*" 2>nul | find /i "python.exe" >nul
    if %ERRORLEVEL% neq 0 (
        echo [%date% %time%] Starting emergency backup process >> "D:\Projects\PAKE_SYSTEM\logs\watchdog.log"
        start /b "" python "D:\Projects\PAKE_SYSTEM\scripts\automated_vault_watcher.py"
    )
)

:END
exit /b 0