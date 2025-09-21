import os
import json
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import threading
from functools import wraps

# Import structured logger
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import get_logger

class CacheManager:
    """Simple in-memory cache manager for note operations"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self.cache:
                return None
            
            # Check TTL
            if datetime.now().timestamp() - self.timestamps[key] > self.default_ttl:
                del self.cache[key]
                del self.timestamps[key]
                return None
            
            return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            # Evict oldest entries if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = datetime.now().timestamp()
    
    def delete(self, key: str) -> None:
        with self._lock:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def clear(self) -> None:
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching a pattern"""
        with self._lock:
            keys_to_delete = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self.cache[key]
                del self.timestamps[key]


def with_error_handling(func):
    """Decorator for consistent error handling in repository methods"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as error:
            self.logger.error(f"Error in {func.__name__}", 
                            method=func.__name__,
                            args_count=len(args),
                            error=str(error))
            raise
    return wrapper


class NoteRepository:
    """
    Note Repository for PAKE System
    Handles filesystem-based note operations with caching
    """
    
    def __init__(self, vault_path: str = None, cache_size: int = 1000):
        # Set up paths
        self.vault_path = Path(vault_path or self._get_default_vault_path())
        self.inbox_path = self.vault_path / "00-Inbox"
        self.permanent_path = self.vault_path / "02-Permanent"
        self.projects_path = self.vault_path / "03-Projects"
        self.areas_path = self.vault_path / "04-Areas"
        self.resources_path = self.vault_path / "05-Resources"
        self.archives_path = self.vault_path / "06-Archives"
        
        # Initialize components
        self.logger = get_logger("note-repository")
        self.cache = CacheManager(max_size=cache_size)
        self._lock = threading.RLock()
        
        # Ensure directories exist
        self._ensure_directories()
        
        self.logger.info("NoteRepository initialized", 
                        vault_path=str(self.vault_path),
                        cache_size=cache_size)
    
    def _get_default_vault_path(self) -> str:
        """Get default vault path"""
        current_dir = Path(__file__).parent.parent.parent
        vault_path = current_dir / "vault"
        return str(vault_path)
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        directories = [
            self.vault_path,
            self.inbox_path,
            self.permanent_path,
            self.projects_path,
            self.areas_path,
            self.resources_path,
            self.archives_path
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _generate_cache_key(self, namespace: str, *parts) -> str:
        """Generate standardized cache key"""
        key_parts = [str(part) for part in parts if part is not None]
        return f"{namespace}:{'|'.join(key_parts)}"
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Generate hash for file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return hashlib.sha256(content.encode()).hexdigest()
        except Exception:
            return str(file_path.stat().st_mtime)
    
    def _parse_note_metadata(self, content: str) -> Dict[str, Any]:
        """Parse frontmatter and extract metadata from note content"""
        metadata = {
            'title': 'Untitled',
            'tags': [],
            'created': None,
            'modified': None,
            'type': 'note'
        }
        
        lines = content.split('\n')
        
        # Check for frontmatter (YAML)
        if lines and lines[0].strip() == '---':
            frontmatter_end = -1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    frontmatter_end = i
                    break
            
            if frontmatter_end > 0:
                frontmatter_lines = lines[1:frontmatter_end]
                for line in frontmatter_lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key in ['title', 'type']:
                            metadata[key] = value
                        elif key == 'tags':
                            # Parse tags (could be YAML list or comma-separated)
                            if value.startswith('[') and value.endswith(']'):
                                tags_str = value[1:-1]
                                metadata['tags'] = [tag.strip().strip('"\'') for tag in tags_str.split(',')]
                            else:
                                metadata['tags'] = [tag.strip() for tag in value.split(',')]
        
        # Extract title from first heading if not in frontmatter
        if metadata['title'] == 'Untitled':
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('# '):
                    metadata['title'] = stripped[2:].strip()
                    break
        
        return metadata
    
    @with_error_handling
    def create_note(self, content: str, title: str = None, note_type: str = "note", 
                   location: str = "inbox", metadata: Dict = None) -> Dict[str, Any]:
        """Create a new note"""
        
        # Generate unique ID
        note_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Determine file path based on location
        location_map = {
            'inbox': self.inbox_path,
            'permanent': self.permanent_path,
            'projects': self.projects_path,
            'areas': self.areas_path,
            'resources': self.resources_path
        }
        
        base_path = location_map.get(location, self.inbox_path)
        
        # Generate filename
        if not title:
            title = f"note-{timestamp.strftime('%Y-%m-%d-%H%M%S')}"
        
        # Sanitize title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in ('-', '_', ' ')).strip()
        safe_title = safe_title.replace(' ', '-')
        filename = f"{safe_title}.md"
        file_path = base_path / filename
        
        # Ensure unique filename
        counter = 1
        while file_path.exists():
            filename = f"{safe_title}-{counter}.md"
            file_path = base_path / filename
            counter += 1
        
        # Prepare frontmatter
        frontmatter_data = {
            'id': note_id,
            'title': title,
            'type': note_type,
            'created': timestamp.isoformat(),
            'modified': timestamp.isoformat(),
            **(metadata or {})
        }
        
        # Build content with frontmatter
        frontmatter_lines = ['---']
        for key, value in frontmatter_data.items():
            if isinstance(value, list):
                value_str = '[' + ', '.join(f'"{item}"' for item in value) + ']'
            else:
                value_str = str(value)
            frontmatter_lines.append(f'{key}: {value_str}')
        frontmatter_lines.append('---')
        
        full_content = '\n'.join(frontmatter_lines) + '\n\n' + content
        
        # Write file
        with self._lock:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
        
        # Create note object
        note_data = {
            'id': note_id,
            'title': title,
            'content': content,
            'type': note_type,
            'location': location,
            'file_path': str(file_path),
            'created': timestamp.isoformat(),
            'modified': timestamp.isoformat(),
            'metadata': frontmatter_data
        }
        
        # Cache the note
        cache_key = self._generate_cache_key('note', note_id)
        self.cache.set(cache_key, note_data)
        
        # Invalidate list caches
        self.cache.invalidate_pattern('notes_list')
        
        self.logger.info("Note created", 
                        note_id=note_id,
                        title=title,
                        location=location,
                        file_path=str(file_path))
        
        return note_data
    
    @with_error_handling
    def get_note_by_id(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Get a note by its ID"""
        
        # Try cache first
        cache_key = self._generate_cache_key('note', note_id)
        cached = self.cache.get(cache_key)
        if cached:
            return {**cached, 'from_cache': True}
        
        # Search all note directories
        note_dirs = [
            self.inbox_path,
            self.permanent_path,
            self.projects_path,
            self.areas_path,
            self.resources_path,
            self.archives_path
        ]
        
        for note_dir in note_dirs:
            for file_path in note_dir.glob('*.md'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Quick check for ID in frontmatter
                    if f'id: {note_id}' in content:
                        note_data = self._parse_note_file(file_path, content)
                        if note_data and note_data['id'] == note_id:
                            # Cache the result
                            self.cache.set(cache_key, note_data)
                            return {**note_data, 'from_cache': False}
                
                except Exception as e:
                    self.logger.warn("Error reading note file", 
                                   file_path=str(file_path),
                                   error=str(e))
                    continue
        
        return None
    
    @with_error_handling
    def get_notes_by_location(self, location: str = "inbox", limit: int = 50, 
                            offset: int = 0) -> Dict[str, Any]:
        """Get notes by location with pagination"""
        
        # Try cache first
        cache_key = self._generate_cache_key('notes_list', location, limit, offset)
        cached = self.cache.get(cache_key)
        if cached:
            return {**cached, 'from_cache': True}
        
        location_map = {
            'inbox': self.inbox_path,
            'permanent': self.permanent_path,
            'projects': self.projects_path,
            'areas': self.areas_path,
            'resources': self.resources_path,
            'archives': self.archives_path
        }
        
        target_path = location_map.get(location)
        if not target_path or not target_path.exists():
            return {
                'notes': [],
                'pagination': {'total': 0, 'limit': limit, 'offset': offset, 'has_more': False},
                'from_cache': False
            }
        
        # Get all markdown files
        all_files = list(target_path.glob('*.md'))
        
        # Sort by modification time (newest first)
        all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Paginate
        total_count = len(all_files)
        paginated_files = all_files[offset:offset + limit]
        
        # Parse notes
        notes = []
        for file_path in paginated_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                note_data = self._parse_note_file(file_path, content)
                if note_data:
                    notes.append(note_data)
            
            except Exception as e:
                self.logger.warn("Error parsing note file", 
                               file_path=str(file_path),
                               error=str(e))
                continue
        
        result = {
            'notes': notes,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total_count
            }
        }
        
        # Cache the result
        self.cache.set(cache_key, result, ttl=300)  # 5 minute cache
        
        return {**result, 'from_cache': False}
    
    @with_error_handling
    def update_note(self, note_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing note"""
        
        # First find the note
        existing_note = self.get_note_by_id(note_id)
        if not existing_note:
            return None
        
        file_path = Path(existing_note['file_path'])
        
        # Read current content
        with open(file_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        # Parse frontmatter and content
        lines = current_content.split('\n')
        frontmatter_end = -1
        
        if lines and lines[0].strip() == '---':
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    frontmatter_end = i
                    break
        
        # Update frontmatter
        frontmatter_data = existing_note.get('metadata', {})
        frontmatter_data.update({
            'modified': datetime.now().isoformat(),
            **{k: v for k, v in updates.items() if k in ['title', 'type', 'tags']}
        })
        
        # Update content if provided
        content_start_line = frontmatter_end + 1 if frontmatter_end > 0 else 0
        original_content = '\n'.join(lines[content_start_line:]).strip()
        new_content = updates.get('content', original_content)
        
        # Build new file content
        frontmatter_lines = ['---']
        for key, value in frontmatter_data.items():
            if isinstance(value, list):
                value_str = '[' + ', '.join(f'"{item}"' for item in value) + ']'
            else:
                value_str = str(value)
            frontmatter_lines.append(f'{key}: {value_str}')
        frontmatter_lines.append('---')
        
        full_content = '\n'.join(frontmatter_lines) + '\n\n' + new_content
        
        # Write updated content
        with self._lock:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
        
        # Update note data
        updated_note = {
            **existing_note,
            'content': new_content,
            'modified': frontmatter_data['modified'],
            'metadata': frontmatter_data,
            **{k: v for k, v in updates.items() if k in ['title', 'type']}
        }
        
        # Update cache
        cache_key = self._generate_cache_key('note', note_id)
        self.cache.set(cache_key, updated_note)
        
        # Invalidate list caches
        self.cache.invalidate_pattern('notes_list')
        
        self.logger.info("Note updated", note_id=note_id, updates_count=len(updates))
        
        return updated_note
    
    @with_error_handling
    def delete_note(self, note_id: str) -> bool:
        """Delete a note"""
        
        # Find the note first
        existing_note = self.get_note_by_id(note_id)
        if not existing_note:
            return False
        
        file_path = Path(existing_note['file_path'])
        
        # Delete the file
        with self._lock:
            try:
                file_path.unlink()
                
                # Remove from cache
                cache_key = self._generate_cache_key('note', note_id)
                self.cache.delete(cache_key)
                
                # Invalidate list caches
                self.cache.invalidate_pattern('notes_list')
                
                self.logger.info("Note deleted", note_id=note_id, file_path=str(file_path))
                
                return True
                
            except Exception as e:
                self.logger.error("Failed to delete note file", 
                                note_id=note_id,
                                file_path=str(file_path),
                                error=str(e))
                return False
    
    @with_error_handling
    def search_notes(self, query: str, location: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search notes by content and title"""
        
        # Try cache first
        cache_key = self._generate_cache_key('search', query, location, limit)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        search_dirs = []
        if location:
            location_map = {
                'inbox': self.inbox_path,
                'permanent': self.permanent_path,
                'projects': self.projects_path,
                'areas': self.areas_path,
                'resources': self.resources_path,
                'archives': self.archives_path
            }
            target_path = location_map.get(location)
            if target_path and target_path.exists():
                search_dirs = [target_path]
        else:
            search_dirs = [
                self.inbox_path,
                self.permanent_path,
                self.projects_path,
                self.areas_path,
                self.resources_path
            ]
        
        results = []
        query_lower = query.lower()
        
        for search_dir in search_dirs:
            for file_path in search_dir.glob('*.md'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Simple text search
                    if query_lower in content.lower():
                        note_data = self._parse_note_file(file_path, content)
                        if note_data:
                            results.append(note_data)
                            
                            if len(results) >= limit:
                                break
                
                except Exception as e:
                    self.logger.warn("Error searching note file", 
                                   file_path=str(file_path),
                                   error=str(e))
                    continue
            
            if len(results) >= limit:
                break
        
        # Cache search results for short time
        self.cache.set(cache_key, results, ttl=300)
        
        return results
    
    def _parse_note_file(self, file_path: Path, content: str) -> Optional[Dict[str, Any]]:
        """Parse a note file and return note data"""
        try:
            metadata = self._parse_note_metadata(content)
            
            # Extract content without frontmatter
            lines = content.split('\n')
            content_start = 0
            
            if lines and lines[0].strip() == '---':
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == '---':
                        content_start = i + 1
                        break
            
            note_content = '\n'.join(lines[content_start:]).strip()
            
            # Get file stats
            stat = file_path.stat()
            
            # Determine location based on path
            location = 'unknown'
            if self.inbox_path in file_path.parents:
                location = 'inbox'
            elif self.permanent_path in file_path.parents:
                location = 'permanent'
            elif self.projects_path in file_path.parents:
                location = 'projects'
            elif self.areas_path in file_path.parents:
                location = 'areas'
            elif self.resources_path in file_path.parents:
                location = 'resources'
            elif self.archives_path in file_path.parents:
                location = 'archives'
            
            return {
                'id': metadata.get('id', str(uuid.uuid4())),
                'title': metadata.get('title', file_path.stem),
                'content': note_content,
                'type': metadata.get('type', 'note'),
                'location': location,
                'file_path': str(file_path),
                'created': metadata.get('created') or datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': metadata.get('modified') or datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'size': stat.st_size,
                'metadata': metadata
            }
        
        except Exception as e:
            self.logger.error("Error parsing note file", 
                            file_path=str(file_path),
                            error=str(e))
            return None
    
    @with_error_handling
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        
        stats = {
            'total_notes': 0,
            'by_location': {},
            'by_type': {},
            'cache_info': {
                'size': len(self.cache.cache),
                'max_size': self.cache.max_size
            }
        }
        
        locations = {
            'inbox': self.inbox_path,
            'permanent': self.permanent_path,
            'projects': self.projects_path,
            'areas': self.areas_path,
            'resources': self.resources_path,
            'archives': self.archives_path
        }
        
        for location_name, location_path in locations.items():
            if location_path.exists():
                files = list(location_path.glob('*.md'))
                count = len(files)
                stats['by_location'][location_name] = count
                stats['total_notes'] += count
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        self.cache.clear()
        self.logger.info("Note repository cache cleared")
    
    def health_check(self) -> Dict[str, Any]:
        """Repository health check"""
        try:
            # Check if vault directory is accessible
            if not self.vault_path.exists():
                return {
                    'status': 'unhealthy',
                    'error': 'Vault path does not exist',
                    'vault_path': str(self.vault_path)
                }
            
            # Check if we can write to inbox
            test_file = self.inbox_path / '.health_check'
            test_file.write_text('health_check')
            test_file.unlink()
            
            stats = self.get_stats()
            
            return {
                'status': 'healthy',
                'vault_path': str(self.vault_path),
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Create default instance
default_repository = NoteRepository()


def get_note_repository(vault_path: str = None) -> NoteRepository:
    """Get note repository instance"""
    if vault_path:
        return NoteRepository(vault_path)
    return default_repository