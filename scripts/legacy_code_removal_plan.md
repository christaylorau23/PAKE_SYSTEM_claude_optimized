# Legacy Code Removal Plan

## Current Architecture Analysis

Based on the analysis of the codebase, the **current main server** is:
- **`mcp_server_standalone.py`** (70KB, latest version, used in production Dockerfile)

## Redundant/Legacy Server Files to Remove

### Root Directory Server Files
1. **`mcp_server.py`** (15KB) - Basic MCP server, superseded by standalone
2. **`mcp_server_database.py`** (19KB) - Database-specific server, functionality merged into standalone
3. **`mcp_server_auth.py`** (18KB) - Auth-specific server, functionality merged into standalone
4. **`mcp_server_realtime.py`** (35KB) - Realtime server, functionality merged into standalone
5. **`mcp_server_multitenant.py`** (12KB) - Multitenant server, functionality merged into standalone
6. **`mock_api_server.py`** (6KB) - Mock server for testing, outdated

### mcp-servers Directory (Multiple Implementations)
7. **`mcp-servers/base_server.py`** - Legacy base implementation
8. **`mcp-servers/enhanced_base_server.py`** - Enhanced base, superseded
9. **`mcp-servers/minimal_server.py`** - Minimal implementation, outdated
10. **`mcp-servers/pake_mcp_server.py`** - Legacy MCP server
11. **`mcp-servers/pake_fastmcp_server.py`** - FastMCP implementation, outdated

### Legacy Directories to Remove Completely
12. **`archive/`** (192KB) - Old batch scripts and legacy automation
13. **`security_backups/`** (15MB) - Backup copies of old implementations

### Additional Legacy Files
14. **`mcp-servers/confidence_engine.py`** - Standalone confidence engine, integrated elsewhere
15. **`mcp-servers/pake_node_mcp_server.js`** - Node.js implementation, replaced by Python
16. **Legacy requirement files**: `mcp-servers/requirements*.txt` (multiple variants)
17. **Legacy Dockerfiles**: `mcp-servers/Dockerfile*` (multiple variants)

## Files to Keep

### Current Production Server
- **`mcp_server_standalone.py`** - Current main server (production)

### Supporting Infrastructure
- **`Dockerfile`** - Production container configuration
- **`deploy/`** directory - Standardized deployment configurations
- **`src/`** directory - Core service implementations

## Estimated Space Savings
- Archive directory: 192KB
- Security backups: 15MB
- Legacy server files: ~200KB
- **Total estimated savings: ~15.4MB**

## Removal Execution Plan

### Phase 1: Remove Archive and Backup Directories
```bash
rm -rf archive/
rm -rf security_backups/
```

### Phase 2: Remove Redundant Root Server Files
```bash
rm mcp_server.py
rm mcp_server_database.py
rm mcp_server_auth.py
rm mcp_server_realtime.py
rm mcp_server_multitenant.py
rm mock_api_server.py
```

### Phase 3: Clean Up mcp-servers Directory
```bash
rm mcp-servers/base_server.py
rm mcp-servers/enhanced_base_server.py
rm mcp-servers/minimal_server.py
rm mcp-servers/pake_mcp_server.py
rm mcp-servers/pake_fastmcp_server.py
rm mcp-servers/confidence_engine.py
rm mcp-servers/pake_node_mcp_server.js
rm mcp-servers/requirements*.txt
rm mcp-servers/Dockerfile*
```

### Phase 4: Update Dependencies
- Review any test files that reference removed servers
- Update import statements in remaining code
- Clean up any configuration references

## Risk Assessment
- **Low Risk**: Archive and security_backups are clearly legacy
- **Medium Risk**: Root server files - need to verify no active references
- **Low Risk**: mcp-servers directory - redundant implementations

## Verification Steps
1. Search for imports of removed files
2. Check test files for references
3. Verify deployment scripts don't reference removed files
4. Run test suite after removal to ensure no broken dependencies