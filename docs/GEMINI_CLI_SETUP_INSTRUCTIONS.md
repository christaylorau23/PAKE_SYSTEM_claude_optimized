# Gemini CLI Setup & Authentication Instructions

## ✅ Installation Complete

The Google Gemini CLI has been successfully installed:
- **Version**: 0.1.22
- **Location**: Globally installed via npm
- **Configuration**: `C:\Users\Christopher Taylor\.gemini\settings.json`

---

## 🔐 Authentication Setup (Interactive Steps Required)

### Step 1: Start Interactive Authentication
Open a **new command prompt or terminal** and run:

```bash
gemini
```

This will start the interactive Gemini CLI setup process.

### Step 2: Choose Authentication Method
When prompted, you'll see authentication options:

**Option 1: Google OAuth (Recommended)**
- Select "Login with Google" 
- This provides **60 requests/min** and **1,000 requests/day** for free
- Best for personal use with your Google account

**Option 2: API Key**
- If you prefer API key authentication, you can get one from [Google AI Studio](https://aistudio.google.com/app/apikey)
- Set the environment variable: `set GEMINI_API_KEY=your_api_key_here`

### Step 3: Complete Google OAuth Flow
If you choose Google OAuth:
1. The CLI will open your default web browser
2. Sign in with your Google account
3. Authorize the Gemini CLI application
4. Return to the terminal - authentication will be complete

### Step 4: Verify Authentication
Test that authentication is working:

```bash
gemini --prompt "Hello! Can you confirm that authentication is working?"
```

---

## 🛠 PAKE System Integration

### Step 5: Add PAKE MCP Server
Once authentication is working, add your PAKE MCP server:

```bash
gemini mcp add pake-obsidian http://localhost:3000
gemini mcp add pake-server http://localhost:8000
```

### Step 6: Verify MCP Integration
Check that MCP servers are configured:

```bash
gemini mcp list
```

### Step 7: Test PAKE Tools
Test the integration with a simple search:

```bash
gemini --prompt "Please use the search_notes tool to find any existing notes in my PAKE vault"
```

---

## 🎯 PAKE-Specific Configuration

### Project-Level Settings
I've created a project-specific configuration that will be automatically applied when you run Gemini from your PAKE directory.

**Location**: `D:\Projects\PAKE_SYSTEM\.gemini\settings.json`

This configuration includes:
- PAKE MCP server endpoints
- Optimized settings for knowledge management workflows
- Agent prompt configurations

---

## 📋 Quick Start Commands

### Basic Gemini Usage
```bash
# Interactive mode
gemini

# Single prompt
gemini --prompt "Your question here"

# Debug mode
gemini --debug --prompt "Your question here"
```

### PAKE Integration Commands
```bash
# Search vault
gemini --prompt "Search for notes about 'AI development' in my PAKE vault"

# Get specific note
gemini --prompt "Retrieve the full content of note with PAKE ID: [id]"

# Create new note
gemini --prompt "Create a new SourceNote about [topic] with proper metadata"
```

### Agent Workflows
```bash
# Research workflow
gemini --prompt "Act as a PAKE Ingestion Agent and research the topic: [your topic]"

# Synthesis workflow  
gemini --prompt "Act as a PAKE Synthesis Agent and create insights from existing notes about [topic]"
```

---

## 🚨 Troubleshooting

### Authentication Issues
- **Error: "Please set an Auth method"**: Run `gemini` in interactive mode to complete setup
- **Browser doesn't open**: Copy the authentication URL manually from the terminal
- **Workspace account issues**: You may need to set `GOOGLE_CLOUD_PROJECT` environment variable

### MCP Connection Issues
- **Can't connect to PAKE servers**: Ensure your Obsidian Bridge (port 3000) and MCP Server (port 8000) are running
- **Tools not available**: Verify MCP servers are added with `gemini mcp list`

### Rate Limits
- **Free tier**: 60 requests/minute, 1,000 requests/day with Google login
- **Exceeded limits**: Wait for reset or consider API key with higher limits

---

## 📞 Next Steps

1. **Complete authentication** using the interactive process above
2. **Test basic functionality** with a simple prompt
3. **Add PAKE MCP servers** to enable knowledge management tools
4. **Run a test workflow** using one of the agent prompts
5. **Review the Daily Review Dashboard** to see Gemini-created content

Once setup is complete, you'll have a fully integrated AI assistant that can autonomously manage your knowledge base through the PAKE system!

---

## ⚠️ Important Notes

- **First run must be interactive** - authentication requires browser-based OAuth
- **Keep terminal open** during authentication process
- **MCP servers must be running** for PAKE integration to work
- **Use project directory** - run Gemini commands from `D:\Projects\PAKE_SYSTEM\` for automatic PAKE configuration

Ready to activate your AI-powered knowledge management system! 🚀