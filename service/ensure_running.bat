@echo off
:: PAKE Auto-Start Backup Script
:: Runs at user login as registry startup backup

:: Wait a moment for system to stabilize
timeout /t 10 /nobreak >nul

:: Check if service is running
sc query PAKEKnowledgeService | find "RUNNING" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    :: Service is running, we're good
    exit /b 0
)

:: Service not running, try to start it
echo [%date% %time%] Registry backup: Service not running, attempting start... >> "D:\Projects\PAKE_SYSTEM\logs\registry_backup.log"

net start PAKEKnowledgeService >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [%date% %time%] Registry backup: Service started successfully >> "D:\Projects\PAKE_SYSTEM\logs\registry_backup.log"
    exit /b 0
)

:: Service failed to start, try manual approach
echo [%date% %time%] Registry backup: Service failed, starting manual process... >> "D:\Projects\PAKE_SYSTEM\logs\registry_backup.log"

:: Check if manual process is already running
tasklist /fi "imagename eq python.exe" /fi "windowtitle eq *automated_vault_watcher*" 2>nul | find /i "python.exe" >nul
if %ERRORLEVEL% equ 0 (
    echo [%date% %time%] Registry backup: Manual process already running >> "D:\Projects\PAKE_SYSTEM\logs\registry_backup.log"
    exit /b 0
)

:: Start manual vault watcher
cd /d "D:\Projects\PAKE_SYSTEM"
start /b "PAKE Vault Monitor" python "scripts\automated_vault_watcher.py"

echo [%date% %time%] Registry backup: Manual process started >> "D:\Projects\PAKE_SYSTEM\logs\registry_backup.log"
exit /b 0