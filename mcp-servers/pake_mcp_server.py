#!/usr/bin/env python3
"""
PAKE MCP Server
Official MCP (Model Context Protocol) server for Knowledge Vault integration
Uses the official Python MCP SDK and follows the JSON-RPC 2.0 protocol
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import aiofiles

# Custom security exception
class SecurityError(Exception):
    """Raised when a security violation is detected"""
    pass

# MCP SDK imports
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Load unified configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'configs'))
from service_config import get_config

# Initialize configuration
config = get_config()

# Setup structured JSON logging
import json
import sys

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'pathname', 'filename',
                          'module', 'lineno', 'funcName', 'created', 'msecs',
                          'relativeCreated', 'thread', 'threadName', 'processName',
                          'process', 'levelname', 'levelno', 'exc_info', 'exc_text',
                          'stack_info', 'message']:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)

# Configure JSON logging using configuration
json_handler = logging.StreamHandler(sys.stderr)
if config.logging.json_formatting:
    json_handler.setFormatter(JsonFormatter())

logger = logging.getLogger("pake-mcp-server")
logger.setLevel(getattr(logging, config.get_log_level()))
logger.addHandler(json_handler)

# Disable default basicConfig to avoid duplicate logs
logging.getLogger().handlers.clear()

class VaultManager:
    """File-based vault manager for Knowledge Vault operations"""

    def __init__(self, vault_path: Path = None):
        # Use configuration system for vault path
        self.vault_path = vault_path or config.get_vault_path()
        self.vault_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized vault manager for: {self.vault_path}")

    def _contains_path_traversal(self, title: str) -> bool:
        """Detect path traversal attempts in title"""
        import re
        import urllib.parse

        # Special case: allow standalone dots and double dots (check first)
        if title.strip() in ('.', '..', '...'):
            return False  # These will be handled by filename sanitization

        # Normalize the title for analysis
        normalized = title.lower()

        # Check for direct path traversal patterns
        dangerous_patterns = [
            # Classic path traversal
            '../',
            '..\\',
            './',
            '.\\',
            # Encoded path traversal
            '%2e%2e',  # URL encoded ..
            '%2f',     # URL encoded /
            '%5c',     # URL encoded \
            # Double encoding
            '%252e',
            '%252f',
            '%255c',
            # Unicode encoding
            '\u002e\u002e',
            '\u002f',
            '\u005c',
            # Null bytes
            '\x00',
            '\0'
        ]

        # Check for any dangerous patterns
        for pattern in dangerous_patterns:
            if pattern in normalized:
                return True

        # Check for suspicious sequences after URL decoding
        try:
            decoded = urllib.parse.unquote(title)
            decoded_lower = decoded.lower()
            # Only check for path separators with dots, not standalone dots
            for pattern in ['../', '..\\', './', '.\\']:
                if pattern in decoded_lower:
                    return True
        except:
            # If URL decoding fails, be safe and assume potential attack
            pass

        # Check for absolute path indicators (but allow single characters)
        if (title.startswith('/') and len(title) > 1) or (title.startswith('\\') and len(title) > 1):
            return True

        # Windows absolute path (C:, D:, etc.)
        if re.match(r'^[A-Za-z]:', title):
            return True

        # UNC paths (\\server\share)
        if title.startswith('\\\\'):
            return True

        return False

    async def parse_frontmatter(self, file_path: Path) -> Dict[str, Any]:
        """Parse frontmatter from a markdown file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            if content.startswith('---'):
                # Extract frontmatter
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter_text = parts[1].strip()
                    body_content = parts[2].strip()

                    # Parse YAML-like frontmatter
                    metadata = {}
                    for line in frontmatter_text.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()

                            # Handle lists
                            if value.startswith('[') and value.endswith(']'):
                                value = [item.strip().strip('"\'') for item in value[1:-1].split(',') if item.strip()]
                            # Handle numbers
                            elif value.replace('.', '').isdigit():
                                value = float(value) if '.' in value else int(value)
                            # Handle booleans
                            elif value.lower() in ['true', 'false']:
                                value = value.lower() == 'true'
                            # Remove quotes
                            elif value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]

                            metadata[key] = value

                    return {
                        'metadata': metadata,
                        'content': body_content,
                        'has_frontmatter': True
                    }

            return {
                'metadata': {},
                'content': content,
                'has_frontmatter': False
            }

        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"File access error parsing frontmatter for {file_path}: {e}")
            return {'metadata': {}, 'content': '', 'has_frontmatter': False}
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error parsing frontmatter for {file_path}: {e}")
            return {'metadata': {}, 'content': '', 'has_frontmatter': False}
        except (OSError, IOError) as e:
            logger.error(f"I/O error parsing frontmatter for {file_path}: {e}")
            return {'metadata': {}, 'content': '', 'has_frontmatter': False}

    async def search_notes(self, filters: Dict[str, Any], limit: int = None) -> List[Dict[str, Any]]:
        """Search notes based on filters"""
        results = []

        # Use configuration for default limit
        if limit is None:
            limit = config.search.default_search_limit

        # Enforce maximum limit
        limit = min(limit, config.search.max_search_limit)

        try:
            # Find all markdown files
            for md_file in self.vault_path.rglob("*.md"):
                try:
                    parsed = await self.parse_frontmatter(md_file)
                    metadata = parsed['metadata']

                    # Apply filters
                    matches = True
                    for key, value in filters.items():
                        if key == 'pake_type' and metadata.get('type', '') != value:
                            matches = False
                            break
                        elif key == 'status' and metadata.get('status', '') != value:
                            matches = False
                            break
                        elif key == 'tags':
                            note_tags = metadata.get('tags', [])
                            if isinstance(value, str):
                                if value not in note_tags:
                                    matches = False
                                    break
                            elif isinstance(value, list):
                                if not any(tag in note_tags for tag in value):
                                    matches = False
                                    break
                        elif key == 'min_confidence':
                            if metadata.get('confidence_score', 0.0) < value:
                                matches = False
                                break

                    if matches:
                        results.append({
                            'pake_id': metadata.get('pake_id', str(uuid.uuid4())),
                            'title': metadata.get('title', md_file.stem),
                            'file_path': str(md_file),
                            'summary': metadata.get('summary', parsed['content'][:config.vault.summary_truncate_length] + '...' if len(parsed['content']) > config.vault.summary_truncate_length else parsed['content']),
                            'metadata': metadata
                        })

                        if len(results) >= limit:
                            break

                except (FileNotFoundError, PermissionError):
                    logger.warning(f"File access denied or not found: {md_file}")
                    continue
                except UnicodeDecodeError:
                    logger.warning(f"Unicode decode error for file: {md_file}")
                    continue
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Data parsing error for file {md_file}: {e}")
                    continue

        except (OSError, IOError) as e:
            logger.error(f"File system error searching notes: {e}")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid search parameters: {e}")

        return results

    async def get_note_by_id(self, pake_id: str) -> Optional[Dict[str, Any]]:
        """Get a note by its PAKE ID"""
        try:
            for md_file in self.vault_path.rglob("*.md"):
                parsed = await self.parse_frontmatter(md_file)
                if parsed['metadata'].get('pake_id') == pake_id:
                    return {
                        'pake_id': pake_id,
                        'title': parsed['metadata'].get('title', md_file.stem),
                        'content': parsed['content'],
                        'metadata': parsed['metadata'],
                        'file_path': str(md_file)
                    }
        except (OSError, IOError) as e:
            logger.error(f"File system error getting note by ID {pake_id}: {e}")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid pake_id parameter: {pake_id}: {e}")

        return None

    async def create_note(self, title: str, content: str, note_type: str = "SourceNote",
                   source_uri: Optional[str] = None, tags: List[str] = None,
                   summary: Optional[str] = None) -> Dict[str, Any]:
        """Create a new note in the vault"""
        try:
            # Generate PAKE ID
            pake_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            # Determine file location based on type using configuration
            folder = config.get_folder_for_note_type(note_type)

            # SECURITY: Comprehensive path traversal protection
            # Step 1: Detect path traversal patterns BEFORE sanitization
            if self._contains_path_traversal(title):
                raise SecurityError(f"Path traversal attempt detected: {title}")

            # Step 2: Character whitelist sanitization using configuration
            allowed_chars = config.security.allowed_filename_chars
            safe_title = "".join(c for c in title if c.isalnum() or c in allowed_chars).rstrip()
            safe_title = safe_title.replace(' ', config.security.filename_replacement_char)[:config.vault.max_filename_length]

            # Step 3: Strip directory components to prevent path traversal
            safe_title = os.path.basename(safe_title)

            # Step 4: Ensure filename is not empty after sanitization
            if not safe_title or safe_title in ('.', '..'):
                safe_title = f"note_{pake_id[:8]}"

            filename = f"{safe_title}{config.vault.default_file_extension}"

            # Step 5: Construct final path inside configured vault root
            target_folder = self.vault_path / folder
            file_path = target_folder / filename

            # Step 6: CRITICAL - Verify path stays within vault directory
            try:
                # Resolve all symbolic links and relative path components
                resolved_path = file_path.resolve()
                resolved_vault = self.vault_path.resolve()

                # Check if the resolved path is within the vault directory
                if not str(resolved_path).startswith(str(resolved_vault)):
                    raise SecurityError(f"Path traversal attempt detected: {title}")

            except (OSError, ValueError) as e:
                raise SecurityError(f"Invalid path detected: {title}") from e

            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create frontmatter
            frontmatter = {
                'pake_id': pake_id,
                'title': title,
                'type': note_type,
                'status': config.vault.default_note_status,
                'confidence_score': config.vault.default_confidence_score,
                'verification_status': config.vault.default_verification_status,
                'created_at': timestamp,
                'modified_at': timestamp,
                'tags': tags or [],
                'source_uri': source_uri or 'local://mcp',
                'summary': summary or '',
                'human_notes': ''
            }

            # Write file
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write('---\n')
                for key, value in frontmatter.items():
                    if isinstance(value, list):
                        await f.write(f'{key}: {json.dumps(value)}\n')
                    elif isinstance(value, str):
                        await f.write(f'{key}: "{value}"\n')
                    else:
                        await f.write(f'{key}: {value}\n')
                await f.write('---\n\n')
                await f.write(content)

            logger.info(f"Created note: {file_path}")

            return {
                'pake_id': pake_id,
                'title': title,
                'file_path': str(file_path),
                'status': 'created',
                'metadata': frontmatter
            }

        except SecurityError:
            # Re-raise security errors without wrapping
            raise
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"File access error creating note: {e}")
            raise OSError(f"Cannot create note: insufficient permissions or path not found") from e
        except (OSError, IOError) as e:
            logger.error(f"File system error creating note: {e}")
            raise OSError(f"Cannot create note: file system error") from e
        except UnicodeEncodeError as e:
            logger.error(f"Unicode encoding error creating note: {e}")
            raise ValueError(f"Cannot create note: invalid characters in content") from e
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid parameter creating note: {e}")
            raise ValueError(f"Cannot create note: invalid parameters") from e

# Initialize vault manager with configuration
vault_manager = VaultManager()

# Create MCP server instance
server = Server(config.server.server_name)

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for the MCP server"""
    return [
        types.Tool(
            name="search_notes",
            description="Search the Knowledge Vault for notes that match specific filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Filter criteria for searching notes",
                        "properties": {
                            "pake_type": {"type": "string", "description": "Note type (SourceNote, InsightNote, ProjectNote, DailyNote)"},
                            "status": {"type": "string", "description": "Processing status (Raw, Refined, Quarantined)"},
                            "tags": {"type": ["string", "array"], "description": "Tags to search for"},
                            "min_confidence": {"type": "number", "description": "Minimum confidence score (0.0-1.0)"}
                        }
                    },
                    "limit": {"type": "integer", "default": config.search.default_search_limit, "description": "Maximum number of results"}
                },
                "required": ["filters"]
            }
        ),
        types.Tool(
            name="get_note_by_id",
            description="Retrieve a specific note by its PAKE ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "pake_id": {"type": "string", "description": "The unique PAKE ID of the note"}
                },
                "required": ["pake_id"]
            }
        ),
        types.Tool(
            name="notes_from_schema",
            description="Create a new structured note in the Knowledge Vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Note content in Markdown format"},
                    "type": {"type": "string", "default": "SourceNote", "description": "Note type"},
                    "source_uri": {"type": "string", "description": "Source URI for the information"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                    "summary": {"type": "string", "description": "Brief summary of the note"}
                },
                "required": ["title", "content"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool execution requests"""
    try:
        if name == "search_notes":
            filters = arguments.get("filters", {})
            limit = arguments.get("limit", config.search.default_search_limit)
            results = await vault_manager.search_notes(filters, limit)

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "results": results,
                    "count": len(results),
                    "filters_applied": filters
                }, indent=2)
            )]

        elif name == "get_note_by_id":
            pake_id = arguments.get("pake_id")
            if not pake_id:
                raise ValueError("pake_id is required")

            note = await vault_manager.get_note_by_id(pake_id)
            if note:
                return [types.TextContent(
                    type="text",
                    text=json.dumps(note, indent=2)
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": "Note not found", "pake_id": pake_id})
                )]

        elif name == "notes_from_schema":
            title = arguments.get("title")
            content = arguments.get("content")
            note_type = arguments.get("type", "SourceNote")
            source_uri = arguments.get("source_uri")
            tags = arguments.get("tags", [])
            summary = arguments.get("summary")

            if not title or not content:
                raise ValueError("Both title and content are required")

            result = await vault_manager.create_note(
                title=title,
                content=content,
                note_type=note_type,
                source_uri=source_uri,
                tags=tags,
                summary=summary
            )

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except SecurityError as e:
        logger.error(f"Security error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": "Security violation detected", "tool": name})
        )]
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid parameters for tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": "Invalid parameters provided", "tool": name})
        )]
    except (OSError, IOError) as e:
        logger.error(f"File system error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": "File system operation failed", "tool": name})
        )]
    except (json.JSONDecodeError, UnicodeEncodeError) as e:
        logger.error(f"Encoding error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": "Data encoding error", "tool": name})
        )]

async def main():
    # Run the server using stdin/stdout streams for JSON-RPC
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info(f"Starting PAKE MCP Server")
        logger.info(f"Vault path: {vault_manager.vault_path}")
        logger.info(f"Total notes: {len(list(vault_manager.vault_path.rglob('*.md')))}")

        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=config.server.server_name,
                server_version=config.server.server_version,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())