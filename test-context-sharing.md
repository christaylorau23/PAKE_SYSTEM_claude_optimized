# Testing MCP Context Sharing Between Claude Code and Cursor

## Verification Steps

### Step 1: Start in Claude Code
1. Run: `./check-mcp-status.sh` (should show ✅ healthy)
2. Ask Claude Code to remember something specific:
   ```
   "Remember that I'm working on adding a new authentication feature
   to the PAKE system using JWT tokens. The main file is
   src/services/authentication/jwt_auth_service.py"
   ```
3. Have Claude Code create or modify a file
4. Ask Claude Code to store this context in the knowledge graph

### Step 2: Switch to Cursor IDE
1. Open Cursor IDE in the same project directory
2. Verify Cursor can access the MCP server:
   - Check if Cursor shows MCP connection in status bar
   - Look for "Graphiti" or "MCP" indicators
3. Ask Cursor something that requires the context from Step 1:
   ```
   "What authentication feature was I working on?
   What file should I continue editing?"
   ```

### Step 3: Verify Bidirectional Sharing
1. In Cursor, make changes and ask it to remember new context
2. Switch back to Claude Code
3. Ask Claude Code about the changes made in Cursor

## What to Look For

### ✅ Signs It's Working:
- Both tools can recall previous conversations
- Context about your project persists across switches
- File changes and decisions are remembered
- Both tools reference the same project knowledge

### ❌ Signs It's Not Working:
- Tools act like they've never seen the project before
- No memory of previous conversations
- Can't reference work done in the other tool
- Each tool starts fresh every time

## Quick Tests

### Test 1: Memory Persistence
```bash
# In Claude Code terminal:
echo "Testing context from Claude Code at $(date)" > test-context.txt

# Then in Cursor, ask:
# "What test file did I just create from Claude Code?"
```

### Test 2: Project Knowledge
```bash
# Ask both tools:
# "What is the PAKE system architecture?"
# "What APIs are currently integrated?"
# "What was the last feature I worked on?"
```

### Test 3: Code Context
```bash
# In Claude Code, ask:
# "Add a comment to jwt_auth_service.py explaining the token validation"

# Then in Cursor, ask:
# "What comment did I just add to the auth service?"
```

## Monitoring Commands

```bash
# Check MCP server is running
./check-mcp-status.sh

# View MCP server logs
docker-compose -f graphiti-standalone.yml logs -f graphiti-mcp

# Check Neo4j knowledge graph data
# Open: http://localhost:7474
# Run: MATCH (n) RETURN n LIMIT 25
```

## Troubleshooting

### If Context Isn't Sharing:
1. Verify MCP server health: `./check-mcp-status.sh`
2. Check client configurations are loaded
3. Restart MCP server: `docker-compose -f graphiti-standalone.yml restart`
4. Check logs for connection errors

### If Performance is Slow:
1. Check Neo4j memory settings in docker-compose
2. Monitor Neo4j query performance in browser
3. Consider pruning old knowledge graph data