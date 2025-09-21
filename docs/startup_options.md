# PAKE System Auto-Startup Options

## Option 1: Simple Batch Scripts (Recommended for Testing)

### Quick Start
Double-click: `start_pake_automation.bat`

### Manual Control
- **Start**: `start_pake_automation.bat`
- **Stop**: `stop_pake_automation.bat`

### Features:
- ✅ Easy to use and modify
- ✅ Shows status in console window
- ✅ Detailed logging
- ✅ Graceful process management
- ❌ Requires manual starting after reboot

---

## Option 2: Windows Startup (User Login)

### Setup Instructions:
1. Press `Win + R`, type `shell:startup`, press Enter
2. Copy `start_pake_automation.bat` to the Startup folder
3. Rename the copy to `PAKE_Auto_Start.bat`

### Features:
- ✅ Starts automatically when you log in
- ✅ Easy to disable (just delete from startup folder)
- ✅ Runs with your user permissions
- ❌ Only starts when you log in

---

## Option 3: Windows Service (Recommended for Always-On)

### Setup Instructions:
1. Right-click `install_windows_service.bat`
2. Select "Run as administrator"
3. Follow the installation prompts

### Features:
- ✅ Starts automatically with Windows (before login)
- ✅ Runs in background (no console windows)
- ✅ Automatic restart if process crashes
- ✅ Proper Windows service management
- ❌ Requires administrator rights to install

### Service Management:
```batch
# Start service
python pake_service.py start

# Stop service  
python pake_service.py stop

# Remove service
python pake_service.py remove

# Check service status
sc query PAKEAutomationService
```

---

## Option 4: Task Scheduler (Advanced)

### Setup Instructions:
1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task
3. Configure these settings:
   - **Name**: PAKE Automation
   - **Trigger**: At startup
   - **Action**: Start a program
   - **Program**: `D:\Projects\PAKE_SYSTEM\start_pake_automation.bat`
   - **Start in**: `D:\Projects\PAKE_SYSTEM`

### Features:
- ✅ Fine-grained control over startup conditions
- ✅ Can run with highest privileges
- ✅ Detailed scheduling options
- ✅ Built-in logging and monitoring
- ❌ More complex to set up

---

## Recommended Setup Process

### For Development/Testing:
1. Use **Option 1** (Batch Scripts) first to test functionality
2. Run `start_pake_automation.bat` to verify everything works
3. Check logs in `logs/` directory

### For Production/Always-On:
1. Test with Option 1 first
2. Install as **Option 3** (Windows Service) for best reliability
3. Monitor service logs at `logs/service.log`

---

## Status Monitoring

### Check if PAKE is running:
```batch
# Check processes
tasklist | find "python"
tasklist | find "node"

# Check specific PAKE processes
tasklist /fi "windowtitle eq PAKE Vault Watcher"
tasklist /fi "windowtitle eq PAKE API Bridge"
```

### Monitor logs:
```batch
# View latest automation logs
type logs\vault_automation.log

# View service logs (if using service option)
type logs\service.log

# Monitor logs in real-time (PowerShell)
Get-Content logs\vault_automation.log -Wait -Tail 10
```

---

## Troubleshooting

### Common Issues:

**Python not found:**
- Ensure Python is installed and in PATH
- Try: `python --version` in command prompt

**Node.js not found:**
- API bridge will be skipped automatically
- Install Node.js if you need the API bridge

**Permission errors:**
- Run as administrator for service installation
- Check file permissions in PAKE_SYSTEM directory

**Processes not starting:**
- Check logs in `logs/` directory
- Verify vault path exists
- Ensure no antivirus blocking

### Emergency Stop:
If automation gets stuck:
```batch
# Force stop all PAKE processes
taskkill /f /im python.exe
taskkill /f /im node.exe

# Or use the stop script
stop_pake_automation.bat
```

---

## Configuration

### Environment Variables (Optional):
```batch
# Set custom vault path
set VAULT_PATH=D:\MyCustomVault\vault

# Set custom API bridge port  
set BRIDGE_PORT=3001

# Set custom MCP server URL
set MCP_SERVER_URL=http://localhost:8001
```

### Startup Script Customization:
Edit `start_pake_automation.bat` to:
- Change log file locations
- Add custom startup checks
- Modify service startup order
- Add email notifications

---

**Choose the option that best fits your needs and technical comfort level!**