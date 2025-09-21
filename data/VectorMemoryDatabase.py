"""
Vector Memory Database Integration for AI Long-Term Memory
Uses Chroma as the vector database backend for semantic memory storage and retrieval
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from uuid import uuid4

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from .DataAccessLayer import DataAccessLayer


class VectorMemoryDatabase:
    """
    Vector-based memory database for AI long-term memory
    Provides semantic search, conversation storage, and knowledge retrieval
    """
    
    def __init__(self, dal: DataAccessLayer, persist_directory: str = None):
        self.dal = dal
        self.logger = logging.getLogger("vector-memory-db")
        
        # Configure Chroma client
        self.persist_directory = persist_directory or os.path.join(os.path.dirname(__file__), "chroma_db")
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize Chroma client with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding function
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Collection names for different memory types
        self.collections = {
            'conversations': None,
            'knowledge': None,
            'context': None,
            'interactions': None,
            'documents': None
        }
        
        # Memory configuration
        self.config = {
            'max_memory_age_days': 365,  # Keep memories for 1 year
            'similarity_threshold': 0.7,  # Minimum similarity for relevant memories
            'max_results': 10,  # Maximum results per search
            'batch_size': 100,  # Batch size for bulk operations
        }
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the vector memory database"""
        try:
            self.logger.info("Initializing Vector Memory Database", persist_dir=self.persist_directory)
            
            # Create or get collections for different memory types
            await self._setup_collections()
            
            # Migrate existing vector data if present
            await self._migrate_existing_data()
            
            self.is_initialized = True
            self.logger.info("Vector Memory Database initialized successfully")
            
        except Exception as error:
            self.logger.error("Failed to initialize Vector Memory Database", error=str(error))
            raise
    
    async def _setup_collections(self) -> None:
        """Set up Chroma collections for different memory types"""
        collection_configs = {
            'conversations': {
                'name': 'ai_conversations',
                'metadata': {"hnsw:space": "cosine"},
                'description': 'AI conversation history and context'
            },
            'knowledge': {
                'name': 'ai_knowledge',
                'metadata': {"hnsw:space": "cosine"},
                'description': 'Extracted knowledge and insights'
            },
            'context': {
                'name': 'ai_context',
                'metadata': {"hnsw:space": "cosine"},
                'description': 'Contextual information and environment state'
            },
            'interactions': {
                'name': 'ai_interactions',
                'metadata': {"hnsw:space": "cosine"},
                'description': 'User interactions and feedback'
            },
            'documents': {
                'name': 'ai_documents',
                'metadata': {"hnsw:space": "cosine"},
                'description': 'Document content and metadata'
            }
        }
        
        for collection_type, config in collection_configs.items():
            try:
                collection = self.client.get_or_create_collection(
                    name=config['name'],
                    embedding_function=self.embedding_function,
                    metadata=config['metadata']
                )
                self.collections[collection_type] = collection
                self.logger.info(f"Collection '{config['name']}' ready", type=collection_type)
                
            except Exception as error:
                self.logger.error(f"Failed to setup collection '{config['name']}'", error=str(error))
                raise
    
    async def _migrate_existing_data(self) -> None:
        """Migrate existing vector data from JSON files to Chroma"""
        vectors_dir = os.path.join(os.path.dirname(__file__), "vectors")
        
        if not os.path.exists(vectors_dir):
            self.logger.info("No existing vector data to migrate")
            return
        
        migrated_count = 0
        
        for filename in os.listdir(vectors_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(vectors_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Determine collection type based on data structure
                    collection_type = self._determine_collection_type(data)
                    collection = self.collections.get(collection_type)
                    
                    if collection and data.get('pake_id') and data.get('embedding'):
                        # Check if already exists
                        existing = collection.get(ids=[data['pake_id']], include=['metadatas'])
                        
                        if not existing['ids']:
                            # Add to appropriate collection
                            await self._add_memory_to_collection(
                                collection=collection,
                                memory_id=data['pake_id'],
                                content=data.get('content', ''),
                                embedding=data['embedding'],
                                metadata={
                                    'created_at': data.get('created_at', datetime.now().isoformat()),
                                    'file_path': data.get('file_path', ''),
                                    'source': 'migration',
                                    'original_file': filename
                                }
                            )
                            migrated_count += 1
                
                except Exception as error:
                    self.logger.error(f"Failed to migrate {filename}", error=str(error))
        
        self.logger.info(f"Migration completed", migrated_count=migrated_count)
    
    def _determine_collection_type(self, data: Dict[str, Any]) -> str:
        """Determine the appropriate collection for migrated data"""
        file_path = data.get('file_path', '').lower()
        
        if 'conversation' in file_path or 'chat' in file_path:
            return 'conversations'
        elif 'knowledge' in file_path or 'note' in file_path:
            return 'knowledge'
        elif 'document' in file_path or '.md' in file_path:
            return 'documents'
        else:
            return 'context'
    
    async def _add_memory_to_collection(self, collection, memory_id: str, content: str, 
                                      embedding: List[float] = None, metadata: Dict[str, Any] = None) -> str:
        """Add memory to a specific collection"""
        try:
            if embedding is None:
                # Generate embedding if not provided
                embedding = await self._generate_embedding(content)
            
            # Prepare metadata
            memory_metadata = {
                'content': content[:500],  # Store truncated content in metadata
                'timestamp': datetime.now().isoformat(),
                'content_length': len(content),
                'content_hash': hashlib.sha256(content.encode()).hexdigest(),
                **(metadata or {})
            }
            
            # Add to collection
            collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[memory_metadata]
            )
            
            return memory_id
            
        except Exception as error:
            self.logger.error("Failed to add memory to collection", error=str(error))
            raise
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text content"""
        try:
            # Use Chroma's default embedding function
            embeddings = self.embedding_function([text])
            return embeddings[0]
        
        except Exception as error:
            self.logger.error("Failed to generate embedding", error=str(error))
            raise
    
    async def store_conversation_memory(self, conversation_id: str, content: str, 
                                     metadata: Dict[str, Any] = None) -> str:
        """Store conversation memory"""
        memory_id = f"conv_{conversation_id}_{uuid4().hex[:8]}"
        
        conversation_metadata = {
            'type': 'conversation',
            'conversation_id': conversation_id,
            'turn_count': metadata.get('turn_count', 0),
            'user_id': metadata.get('user_id', ''),
            'session_id': metadata.get('session_id', ''),
            **(metadata or {})
        }
        
        return await self._add_memory_to_collection(
            collection=self.collections['conversations'],
            memory_id=memory_id,
            content=content,
            metadata=conversation_metadata
        )
    
    async def store_knowledge_memory(self, knowledge_id: str, content: str, 
                                   knowledge_type: str = 'general', metadata: Dict[str, Any] = None) -> str:
        """Store knowledge memory"""
        memory_id = f"know_{knowledge_id}_{uuid4().hex[:8]}"
        
        knowledge_metadata = {
            'type': 'knowledge',
            'knowledge_type': knowledge_type,
            'domain': metadata.get('domain', 'general'),
            'confidence': metadata.get('confidence', 0.8),
            'source': metadata.get('source', 'ai_extraction'),
            **(metadata or {})
        }
        
        return await self._add_memory_to_collection(
            collection=self.collections['knowledge'],
            memory_id=memory_id,
            content=content,
            metadata=knowledge_metadata
        )
    
    async def store_context_memory(self, context_id: str, content: str, 
                                 context_type: str = 'general', metadata: Dict[str, Any] = None) -> str:
        """Store contextual memory"""
        memory_id = f"ctx_{context_id}_{uuid4().hex[:8]}"
        
        context_metadata = {
            'type': 'context',
            'context_type': context_type,
            'environment': metadata.get('environment', 'unknown'),
            'session_id': metadata.get('session_id', ''),
            'relevance_score': metadata.get('relevance_score', 0.7),
            **(metadata or {})
        }
        
        return await self._add_memory_to_collection(
            collection=self.collections['context'],
            memory_id=memory_id,
            content=content,
            metadata=context_metadata
        )
    
    async def store_interaction_memory(self, interaction_id: str, content: str, 
                                     interaction_type: str = 'general', metadata: Dict[str, Any] = None) -> str:
        """Store interaction memory"""
        memory_id = f"int_{interaction_id}_{uuid4().hex[:8]}"
        
        interaction_metadata = {
            'type': 'interaction',
            'interaction_type': interaction_type,
            'user_id': metadata.get('user_id', ''),
            'feedback_score': metadata.get('feedback_score', 0),
            'outcome': metadata.get('outcome', 'unknown'),
            **(metadata or {})
        }
        
        return await self._add_memory_to_collection(
            collection=self.collections['interactions'],
            memory_id=memory_id,
            content=content,
            metadata=interaction_metadata
        )
    
    async def semantic_search(self, query: str, memory_types: List[str] = None, 
                            limit: int = None, similarity_threshold: float = None) -> List[Dict[str, Any]]:
        """Perform semantic search across memory collections"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        memory_types = memory_types or list(self.collections.keys())
        limit = limit or self.config['max_results']
        similarity_threshold = similarity_threshold or self.config['similarity_threshold']
        
        all_results = []
        
        for memory_type in memory_types:
            collection = self.collections.get(memory_type)
            if not collection:
                continue
            
            try:
                # Search in collection
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    include=['documents', 'metadatas', 'distances']
                )
                
                # Process results
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i]
                    similarity = 1 - distance  # Convert distance to similarity
                    
                    if similarity >= similarity_threshold:
                        result = {
                            'memory_id': results['ids'][0][i],
                            'content': doc,
                            'metadata': results['metadatas'][0][i],
                            'similarity': similarity,
                            'memory_type': memory_type,
                            'timestamp': results['metadatas'][0][i].get('timestamp', ''),
                        }
                        all_results.append(result)
                
            except Exception as error:
                self.logger.error(f"Search failed for {memory_type}", error=str(error))
        
        # Sort by similarity and return top results
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        return all_results[:limit]
    
    async def get_recent_memories(self, memory_types: List[str] = None, 
                                hours: int = 24, limit: int = None) -> List[Dict[str, Any]]:
        """Get recent memories within specified time window"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        memory_types = memory_types or list(self.collections.keys())
        limit = limit or self.config['max_results']
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        all_results = []
        
        for memory_type in memory_types:
            collection = self.collections.get(memory_type)
            if not collection:
                continue
            
            try:
                # Get all items (Chroma doesn't support time-based filtering directly)
                results = collection.get(
                    include=['documents', 'metadatas']
                )
                
                # Filter by timestamp
                for i, metadata in enumerate(results['metadatas']):
                    timestamp_str = metadata.get('timestamp', '')
                    try:
                        memory_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if memory_time.replace(tzinfo=None) >= cutoff_time:
                            result = {
                                'memory_id': results['ids'][i],
                                'content': results['documents'][i],
                                'metadata': metadata,
                                'memory_type': memory_type,
                                'timestamp': timestamp_str,
                            }
                            all_results.append(result)
                    except (ValueError, TypeError):
                        continue
                
            except Exception as error:
                self.logger.error(f"Recent search failed for {memory_type}", error=str(error))
        
        # Sort by timestamp (newest first) and return top results
        all_results.sort(key=lambda x: x['timestamp'], reverse=True)
        return all_results[:limit]
    
    async def get_memory_by_id(self, memory_id: str, memory_type: str = None) -> Optional[Dict[str, Any]]:
        """Retrieve specific memory by ID"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        collections_to_search = [memory_type] if memory_type else list(self.collections.keys())
        
        for collection_type in collections_to_search:
            collection = self.collections.get(collection_type)
            if not collection:
                continue
            
            try:
                results = collection.get(
                    ids=[memory_id],
                    include=['documents', 'metadatas']
                )
                
                if results['ids']:
                    return {
                        'memory_id': results['ids'][0],
                        'content': results['documents'][0],
                        'metadata': results['metadatas'][0],
                        'memory_type': collection_type,
                        'timestamp': results['metadatas'][0].get('timestamp', ''),
                    }
                    
            except Exception as error:
                self.logger.error(f"Get memory failed for {collection_type}", error=str(error))
        
        return None
    
    async def update_memory(self, memory_id: str, content: str = None, 
                          metadata: Dict[str, Any] = None, memory_type: str = None) -> bool:
        """Update existing memory"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        # Find the memory first
        existing_memory = await self.get_memory_by_id(memory_id, memory_type)
        if not existing_memory:
            return False
        
        collection = self.collections.get(existing_memory['memory_type'])
        if not collection:
            return False
        
        try:
            # Update content and/or metadata
            updated_content = content or existing_memory['content']
            updated_metadata = {**existing_memory['metadata'], **(metadata or {})}
            updated_metadata['updated_at'] = datetime.now().isoformat()
            
            # Generate new embedding if content changed
            embedding = None
            if content and content != existing_memory['content']:
                embedding = await self._generate_embedding(updated_content)
            
            # Update in collection
            collection.update(
                ids=[memory_id],
                documents=[updated_content] if content else None,
                metadatas=[updated_metadata],
                embeddings=[embedding] if embedding else None
            )
            
            return True
            
        except Exception as error:
            self.logger.error("Failed to update memory", memory_id=memory_id, error=str(error))
            return False
    
    async def delete_memory(self, memory_id: str, memory_type: str = None) -> bool:
        """Delete specific memory"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        # Find the memory first
        existing_memory = await self.get_memory_by_id(memory_id, memory_type)
        if not existing_memory:
            return False
        
        collection = self.collections.get(existing_memory['memory_type'])
        if not collection:
            return False
        
        try:
            collection.delete(ids=[memory_id])
            self.logger.info("Memory deleted", memory_id=memory_id)
            return True
            
        except Exception as error:
            self.logger.error("Failed to delete memory", memory_id=memory_id, error=str(error))
            return False
    
    async def cleanup_old_memories(self, max_age_days: int = None) -> Dict[str, int]:
        """Clean up memories older than specified age"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        max_age_days = max_age_days or self.config['max_memory_age_days']
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        
        cleanup_stats = {}
        
        for memory_type, collection in self.collections.items():
            if not collection:
                continue
            
            deleted_count = 0
            
            try:
                # Get all items for this collection
                results = collection.get(include=['metadatas'])
                
                # Find old memories to delete
                ids_to_delete = []
                for i, metadata in enumerate(results['metadatas']):
                    timestamp_str = metadata.get('timestamp', '')
                    try:
                        memory_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if memory_time.replace(tzinfo=None) < cutoff_time:
                            ids_to_delete.append(results['ids'][i])
                    except (ValueError, TypeError):
                        continue
                
                # Delete old memories in batches
                batch_size = self.config['batch_size']
                for i in range(0, len(ids_to_delete), batch_size):
                    batch_ids = ids_to_delete[i:i + batch_size]
                    collection.delete(ids=batch_ids)
                    deleted_count += len(batch_ids)
                
                cleanup_stats[memory_type] = deleted_count
                
            except Exception as error:
                self.logger.error(f"Cleanup failed for {memory_type}", error=str(error))
                cleanup_stats[memory_type] = 0
        
        total_deleted = sum(cleanup_stats.values())
        self.logger.info("Memory cleanup completed", 
                        total_deleted=total_deleted, 
                        max_age_days=max_age_days,
                        details=cleanup_stats)
        
        return cleanup_stats
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored memories"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        stats = {
            'collections': {},
            'total_memories': 0,
            'storage_path': self.persist_directory,
            'initialized': self.is_initialized,
            'config': self.config
        }
        
        for memory_type, collection in self.collections.items():
            if not collection:
                continue
            
            try:
                # Get collection count
                count = collection.count()
                stats['collections'][memory_type] = {
                    'count': count,
                    'collection_name': collection.name
                }
                stats['total_memories'] += count
                
            except Exception as error:
                self.logger.error(f"Stats failed for {memory_type}", error=str(error))
                stats['collections'][memory_type] = {
                    'count': 0,
                    'error': str(error)
                }
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on vector memory database"""
        health = {
            'status': 'healthy',
            'vector_db': {
                'initialized': self.is_initialized,
                'persist_directory': self.persist_directory,
                'collections_ready': 0
            },
            'timestamp': datetime.now().isoformat()
        }
        
        if not self.is_initialized:
            health['status'] = 'unhealthy'
            health['vector_db']['error'] = 'Not initialized'
            return health
        
        # Check collections
        for memory_type, collection in self.collections.items():
            try:
                if collection:
                    count = collection.count()
                    health['vector_db'][f'{memory_type}_count'] = count
                    health['vector_db']['collections_ready'] += 1
                else:
                    health['status'] = 'degraded'
                    health['vector_db'][f'{memory_type}_error'] = 'Collection not available'
            
            except Exception as error:
                health['status'] = 'degraded'
                health['vector_db'][f'{memory_type}_error'] = str(error)
        
        return health
    
    async def find_similar_memories(self, content: str, memory_types: List[str] = None,
                                  limit: int = 5, include_recent: bool = True) -> List[Dict[str, Any]]:
        """Find memories similar to given content with enhanced context"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        # Get semantic search results
        similar_memories = await self.semantic_search(content, memory_types, limit * 2)
        
        # If include_recent, also get recent memories and merge
        if include_recent:
            recent_memories = await self.get_recent_memories(memory_types, hours=24, limit=limit)
            
            # Merge and deduplicate by memory_id
            seen_ids = set()
            merged_memories = []
            
            for memory in similar_memories + recent_memories:
                if memory['memory_id'] not in seen_ids:
                    merged_memories.append(memory)
                    seen_ids.add(memory['memory_id'])
            
            # Re-sort by relevance (similarity if available, then recency)
            merged_memories.sort(key=lambda x: (x.get('similarity', 0), x.get('timestamp', '')), reverse=True)
            return merged_memories[:limit]
        
        return similar_memories[:limit]
    
    async def get_conversation_context(self, conversation_id: str, 
                                     context_window: int = 10) -> Dict[str, Any]:
        """Get comprehensive conversation context"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        conversation_collection = self.collections['conversations']
        
        try:
            # Get conversation memories
            all_memories = conversation_collection.get(
                include=['documents', 'metadatas'],
                where={"conversation_id": conversation_id}
            )
            
            # Sort by timestamp
            memories_with_time = []
            for i, metadata in enumerate(all_memories['metadatas']):
                try:
                    timestamp = datetime.fromisoformat(metadata.get('timestamp', ''))
                    memories_with_time.append({
                        'memory_id': all_memories['ids'][i],
                        'content': all_memories['documents'][i],
                        'metadata': metadata,
                        'timestamp': timestamp
                    })
                except (ValueError, TypeError):
                    continue
            
            memories_with_time.sort(key=lambda x: x['timestamp'])
            
            # Get recent context window
            recent_memories = memories_with_time[-context_window:] if memories_with_time else []
            
            # Get related context from other collections
            context_query = " ".join([m['content'][:200] for m in recent_memories[-3:]])
            related_context = []
            
            if context_query:
                related_context = await self.semantic_search(
                    context_query,
                    memory_types=['context', 'knowledge'],
                    limit=5,
                    similarity_threshold=0.6
                )
            
            return {
                'conversation_id': conversation_id,
                'total_memories': len(memories_with_time),
                'recent_memories': recent_memories,
                'related_context': related_context,
                'context_summary': await self._generate_context_summary(recent_memories)
            }
            
        except Exception as error:
            self.logger.error("Failed to get conversation context", error=str(error))
            return {
                'conversation_id': conversation_id,
                'total_memories': 0,
                'recent_memories': [],
                'related_context': [],
                'context_summary': '',
                'error': str(error)
            }
    
    async def _generate_context_summary(self, memories: List[Dict[str, Any]]) -> str:
        """Generate a summary of conversation context"""
        if not memories:
            return "No conversation history available."
        
        # Simple extractive summary - get key points from recent memories
        key_points = []
        
        for memory in memories[-5:]:  # Last 5 memories
            content = memory.get('content', '')
            metadata = memory.get('metadata', {})
            
            # Extract key information
            if len(content) > 100:
                # Take first and last parts of longer content
                summary_part = content[:50] + "..." + content[-50:]
            else:
                summary_part = content
            
            key_points.append({
                'content': summary_part,
                'type': metadata.get('interaction_type', 'unknown'),
                'timestamp': metadata.get('timestamp', '')
            })
        
        # Create summary
        if len(key_points) == 1:
            return f"Recent context: {key_points[0]['content']}"
        elif len(key_points) <= 3:
            return "Recent context: " + " | ".join([kp['content'] for kp in key_points])
        else:
            return f"Conversation has {len(memories)} total exchanges. Recent topics include: " + \
                   " | ".join([kp['content'] for kp in key_points[-3:]])
    
    async def extract_and_index_knowledge(self, content: str, source_id: str,
                                        knowledge_type: str = 'general',
                                        metadata: Dict[str, Any] = None) -> List[str]:
        """Extract knowledge from content and index it"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        extracted_knowledge_ids = []
        
        try:
            # Extract knowledge chunks from content
            knowledge_chunks = await self._extract_knowledge_chunks(content)
            
            for chunk in knowledge_chunks:
                # Create unique knowledge ID
                knowledge_id = f"{source_id}_{hashlib.sha256(chunk['content'].encode()).hexdigest()[:8]}"
                
                # Prepare metadata
                chunk_metadata = {
                    'source_id': source_id,
                    'extraction_method': chunk['method'],
                    'confidence': chunk['confidence'],
                    'chunk_type': chunk['type'],
                    'domain': knowledge_type,
                    **(metadata or {})
                }
                
                # Store knowledge
                memory_id = await self.store_knowledge_memory(
                    knowledge_id=knowledge_id,
                    content=chunk['content'],
                    knowledge_type=knowledge_type,
                    metadata=chunk_metadata
                )
                
                extracted_knowledge_ids.append(memory_id)
            
            self.logger.info("Knowledge extraction completed", 
                           source_id=source_id,
                           chunks_extracted=len(extracted_knowledge_ids))
            
            return extracted_knowledge_ids
            
        except Exception as error:
            self.logger.error("Knowledge extraction failed", 
                            source_id=source_id, error=str(error))
            return []
    
    async def _extract_knowledge_chunks(self, content: str) -> List[Dict[str, Any]]:
        """Extract meaningful knowledge chunks from content"""
        chunks = []
        
        # Simple heuristic-based knowledge extraction
        # Split content into sentences and paragraphs
        sentences = content.split('.')
        paragraphs = content.split('\n\n')
        
        # Extract factual statements (simple heuristics)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 500:
                continue
            
            # Look for factual patterns
            factual_indicators = ['is', 'are', 'was', 'were', 'means', 'refers to', 'defined as']
            confidence = 0.5
            
            if any(indicator in sentence.lower() for indicator in factual_indicators):
                confidence = 0.7
            
            # Look for technical or specific terms
            if any(char.isupper() for char in sentence) and len([w for w in sentence.split() if w.isupper()]) > 0:
                confidence = 0.8
            
            chunks.append({
                'content': sentence,
                'type': 'factual_statement',
                'method': 'heuristic_extraction',
                'confidence': confidence
            })
        
        # Extract concept definitions (paragraphs with definitions)
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if len(paragraph) < 50 or len(paragraph) > 1000:
                continue
            
            # Look for definition patterns
            definition_patterns = ['definition:', 'means that', 'is defined as', 'refers to']
            if any(pattern in paragraph.lower() for pattern in definition_patterns):
                chunks.append({
                    'content': paragraph,
                    'type': 'concept_definition',
                    'method': 'pattern_matching',
                    'confidence': 0.9
                })
        
        # Remove duplicates and low-quality chunks
        unique_chunks = []
        seen_content = set()
        
        for chunk in chunks:
            content_hash = hashlib.sha256(chunk['content'].encode()).hexdigest()
            if content_hash not in seen_content and chunk['confidence'] >= 0.6:
                unique_chunks.append(chunk)
                seen_content.add(content_hash)
        
        return unique_chunks[:20]  # Limit to top 20 chunks
    
    async def query_memory_with_context(self, query: str, context_id: str = None,
                                      memory_types: List[str] = None,
                                      limit: int = 10) -> Dict[str, Any]:
        """Advanced memory query with contextual understanding"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        results = {
            'query': query,
            'context_id': context_id,
            'direct_matches': [],
            'contextual_matches': [],
            'related_memories': [],
            'conversation_context': None
        }
        
        try:
            # Direct semantic search
            direct_matches = await self.semantic_search(
                query=query,
                memory_types=memory_types,
                limit=limit,
                similarity_threshold=0.7
            )
            results['direct_matches'] = direct_matches
            
            # If context_id provided, get conversation context
            if context_id:
                conv_context = await self.get_conversation_context(context_id)
                results['conversation_context'] = conv_context
                
                # Use conversation context to enhance query
                if conv_context.get('context_summary'):
                    enhanced_query = f"{query} {conv_context['context_summary']}"
                    contextual_matches = await self.semantic_search(
                        query=enhanced_query,
                        memory_types=['knowledge', 'context'],
                        limit=limit//2,
                        similarity_threshold=0.6
                    )
                    results['contextual_matches'] = contextual_matches
            
            # Find related memories based on direct matches
            if direct_matches:
                # Use content from top matches to find related memories
                related_content = " ".join([m['content'][:100] for m in direct_matches[:3]])
                related_memories = await self.semantic_search(
                    query=related_content,
                    memory_types=['interactions', 'documents'],
                    limit=limit//2,
                    similarity_threshold=0.5
                )
                
                # Filter out memories already in direct matches
                direct_ids = {m['memory_id'] for m in direct_matches}
                related_memories = [m for m in related_memories if m['memory_id'] not in direct_ids]
                results['related_memories'] = related_memories
            
            # Calculate overall relevance scores
            all_memories = direct_matches + results['contextual_matches'] + related_memories
            for memory in all_memories:
                # Boost score based on memory type and recency
                base_score = memory.get('similarity', 0)
                type_boost = 0.1 if memory['memory_type'] == 'knowledge' else 0
                
                # Recency boost (memories from last 7 days get boost)
                recency_boost = 0
                try:
                    timestamp = datetime.fromisoformat(memory['timestamp'].replace('Z', '+00:00'))
                    days_old = (datetime.now() - timestamp.replace(tzinfo=None)).days
                    if days_old <= 7:
                        recency_boost = 0.1 * (8 - days_old) / 8
                except:
                    pass
                
                memory['relevance_score'] = base_score + type_boost + recency_boost
            
            return results
            
        except Exception as error:
            self.logger.error("Memory query failed", query=query, error=str(error))
            results['error'] = str(error)
            return results
    
    async def batch_store_memories(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store multiple memories in batch for efficiency"""
        if not self.is_initialized:
            raise RuntimeError("Vector Memory Database not initialized")
        
        results = {
            'total_memories': len(memories),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'memory_ids': []
        }
        
        batch_size = self.config['batch_size']
        
        for i in range(0, len(memories), batch_size):
            batch = memories[i:i + batch_size]
            
            for memory in batch:
                try:
                    memory_type = memory.get('type', 'context')
                    content = memory.get('content', '')
                    metadata = memory.get('metadata', {})
                    
                    # Route to appropriate storage method
                    if memory_type == 'conversation':
                        memory_id = await self.store_conversation_memory(
                            conversation_id=memory.get('id', str(uuid4())),
                            content=content,
                            metadata=metadata
                        )
                    elif memory_type == 'knowledge':
                        memory_id = await self.store_knowledge_memory(
                            knowledge_id=memory.get('id', str(uuid4())),
                            content=content,
                            knowledge_type=metadata.get('knowledge_type', 'general'),
                            metadata=metadata
                        )
                    elif memory_type == 'interaction':
                        memory_id = await self.store_interaction_memory(
                            interaction_id=memory.get('id', str(uuid4())),
                            content=content,
                            interaction_type=metadata.get('interaction_type', 'general'),
                            metadata=metadata
                        )
                    else:  # context or default
                        memory_id = await self.store_context_memory(
                            context_id=memory.get('id', str(uuid4())),
                            content=content,
                            context_type=metadata.get('context_type', 'general'),
                            metadata=metadata
                        )
                    
                    results['memory_ids'].append(memory_id)
                    results['successful'] += 1
                    
                except Exception as error:
                    results['failed'] += 1
                    results['errors'].append({
                        'memory': memory.get('id', 'unknown'),
                        'error': str(error)
                    })
        
        self.logger.info("Batch memory storage completed",
                        total=results['total_memories'],
                        successful=results['successful'],
                        failed=results['failed'])
        
        return results
    
    async def cleanup(self) -> None:
        """Cleanup vector memory database resources"""
        try:
            self.logger.info("Starting Vector Memory Database cleanup")
            
            # Clear collections
            self.collections.clear()
            
            # Reset client (Chroma will persist data)
            self.client = None
            
            self.is_initialized = False
            self.logger.info("Vector Memory Database cleanup completed")
            
        except Exception as error:
            self.logger.error("Error during Vector Memory Database cleanup", error=str(error))
            raise