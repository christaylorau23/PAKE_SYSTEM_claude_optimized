"""
AI Memory Query Interface and API Endpoints
Provides high-level interface for AI memory operations and REST API endpoints
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .VectorMemoryDatabase import VectorMemoryDatabase
from .DataAccessLayer import get_dal


# Pydantic models for API requests/responses
class MemoryQuery(BaseModel):
    query: str = Field(..., description="Search query for memory retrieval")
    context_id: Optional[str] = Field(None, description="Conversation or context ID")
    memory_types: Optional[List[str]] = Field(None, description="Types of memories to search")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class MemoryCreate(BaseModel):
    content: str = Field(..., description="Memory content")
    memory_type: str = Field("context", description="Type of memory")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MemoryBatch(BaseModel):
    memories: List[MemoryCreate] = Field(..., description="List of memories to create")


class ConversationMemory(BaseModel):
    conversation_id: str = Field(..., description="Conversation identifier")
    content: str = Field(..., description="Conversation content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class KnowledgeExtraction(BaseModel):
    content: str = Field(..., description="Content to extract knowledge from")
    source_id: str = Field(..., description="Source identifier")
    knowledge_type: str = Field("general", description="Type of knowledge")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AIMemoryQueryInterface:
    """
    High-level interface for AI memory operations
    Provides unified access to vector memory database functionality
    """
    
    def __init__(self, vector_db: VectorMemoryDatabase):
        self.vector_db = vector_db
        self.logger = logging.getLogger("ai-memory-interface")
        self.query_cache = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
        
    async def initialize(self) -> None:
        """Initialize the memory interface"""
        if not self.vector_db.is_initialized:
            await self.vector_db.initialize()
        
        self.logger.info("AI Memory Query Interface initialized")
    
    async def ask_memory(self, query: str, context_id: str = None, 
                        memory_types: List[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Primary interface for querying AI memory
        Returns comprehensive results with context and relevance scoring
        """
        try:
            # Check cache first
            cache_key = f"{query}:{context_id}:{':'.join(memory_types or [])}:{limit}"
            if cache_key in self.query_cache:
                cached_result, timestamp = self.query_cache[cache_key]
                if (datetime.now().timestamp() - timestamp) < self.cache_ttl:
                    self.logger.info("Returning cached memory query result")
                    return cached_result
            
            # Perform comprehensive memory query
            results = await self.vector_db.query_memory_with_context(
                query=query,
                context_id=context_id,
                memory_types=memory_types,
                limit=limit
            )
            
            # Enhance results with additional context
            enhanced_results = await self._enhance_query_results(results, query)
            
            # Cache the result
            self.query_cache[cache_key] = (enhanced_results, datetime.now().timestamp())
            
            # Clean old cache entries
            await self._cleanup_cache()
            
            return enhanced_results
            
        except Exception as error:
            self.logger.error("Memory query failed", query=query, error=str(error))
            return {
                'query': query,
                'error': str(error),
                'direct_matches': [],
                'contextual_matches': [],
                'related_memories': [],
                'suggestions': [],
                'metadata': {
                    'query_time': datetime.now().isoformat(),
                    'success': False
                }
            }
    
    async def _enhance_query_results(self, results: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """Enhance query results with additional context and suggestions"""
        
        # Add query metadata
        results['metadata'] = {
            'query_time': datetime.now().isoformat(),
            'original_query': original_query,
            'total_matches': len(results.get('direct_matches', [])) + 
                           len(results.get('contextual_matches', [])) + 
                           len(results.get('related_memories', [])),
            'success': True,
            'response_type': 'enhanced_query'
        }
        
        # Generate query suggestions based on results
        results['suggestions'] = await self._generate_query_suggestions(results, original_query)
        
        # Add summary if we have good matches
        if results.get('direct_matches'):
            results['summary'] = await self._generate_result_summary(results['direct_matches'])
        
        return results
    
    async def _generate_query_suggestions(self, results: Dict[str, Any], 
                                        original_query: str) -> List[Dict[str, str]]:
        """Generate suggested follow-up queries based on results"""
        suggestions = []
        
        # Extract key terms from successful matches
        all_matches = (results.get('direct_matches', []) + 
                      results.get('contextual_matches', []) + 
                      results.get('related_memories', []))
        
        if not all_matches:
            return [
                {"query": f"What do you know about {original_query}?", "type": "exploratory"},
                {"query": f"Recent information about {original_query}", "type": "temporal"},
                {"query": f"Related topics to {original_query}", "type": "associative"}
            ]
        
        # Extract common terms and concepts
        memory_types = set()
        key_terms = set()
        
        for match in all_matches[:5]:  # Top 5 matches
            memory_types.add(match.get('memory_type', 'unknown'))
            
            # Extract key terms from content (simple approach)
            content = match.get('content', '').lower()
            words = content.split()
            key_terms.update([word for word in words if len(word) > 4])
        
        # Generate suggestions based on memory types found
        if 'knowledge' in memory_types:
            suggestions.append({
                "query": f"Definitions and concepts related to {original_query}",
                "type": "knowledge"
            })
        
        if 'conversations' in memory_types:
            suggestions.append({
                "query": f"Previous discussions about {original_query}",
                "type": "conversational"
            })
        
        # Add temporal suggestions
        suggestions.extend([
            {"query": f"Recent updates about {original_query}", "type": "temporal"},
            {"query": f"Historical context for {original_query}", "type": "historical"}
        ])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    async def _generate_result_summary(self, matches: List[Dict[str, Any]]) -> str:
        """Generate a summary of the top search results"""
        if not matches:
            return "No relevant memories found."
        
        top_match = matches[0]
        content = top_match.get('content', '')
        similarity = top_match.get('similarity', 0)
        memory_type = top_match.get('memory_type', 'unknown')
        
        # Create summary based on top match
        if len(content) > 200:
            summary_content = content[:100] + "..." + content[-100:]
        else:
            summary_content = content
        
        summary = f"Found {len(matches)} relevant memories. "
        summary += f"Best match ({similarity:.1%} similarity) from {memory_type}: {summary_content}"
        
        if len(matches) > 1:
            summary += f" Plus {len(matches) - 1} additional related memories."
        
        return summary
    
    async def _cleanup_cache(self) -> None:
        """Clean up old cache entries"""
        current_time = datetime.now().timestamp()
        expired_keys = [
            key for key, (_, timestamp) in self.query_cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.query_cache[key]
    
    async def remember_conversation(self, conversation_id: str, content: str,
                                  metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Store conversation memory with automatic knowledge extraction"""
        try:
            # Store conversation memory
            memory_id = await self.vector_db.store_conversation_memory(
                conversation_id=conversation_id,
                content=content,
                metadata=metadata
            )
            
            # Extract and store knowledge if content is substantial
            knowledge_ids = []
            if len(content) > 100:  # Only extract knowledge from substantial content
                knowledge_ids = await self.vector_db.extract_and_index_knowledge(
                    content=content,
                    source_id=f"conv_{conversation_id}",
                    knowledge_type="conversational",
                    metadata={
                        **metadata or {},
                        'source_type': 'conversation',
                        'conversation_id': conversation_id
                    }
                )
            
            self.logger.info("Conversation memory stored", 
                           memory_id=memory_id,
                           knowledge_extracted=len(knowledge_ids))
            
            return {
                'success': True,
                'memory_id': memory_id,
                'conversation_id': conversation_id,
                'knowledge_extracted': len(knowledge_ids),
                'knowledge_ids': knowledge_ids,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as error:
            self.logger.error("Failed to store conversation memory", 
                            conversation_id=conversation_id, error=str(error))
            return {
                'success': False,
                'error': str(error),
                'conversation_id': conversation_id,
                'timestamp': datetime.now().isoformat()
            }
    
    async def learn_from_interaction(self, interaction_id: str, content: str,
                                   interaction_type: str = "general",
                                   feedback_score: float = 0,
                                   metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Store interaction memory with feedback learning"""
        try:
            interaction_metadata = {
                'feedback_score': feedback_score,
                'interaction_type': interaction_type,
                'learning_weight': min(1.0, abs(feedback_score)),  # Higher weight for strong feedback
                **metadata or {}
            }
            
            # Store interaction memory
            memory_id = await self.vector_db.store_interaction_memory(
                interaction_id=interaction_id,
                content=content,
                interaction_type=interaction_type,
                metadata=interaction_metadata
            )
            
            # If high-value interaction, also store as knowledge
            knowledge_ids = []
            if abs(feedback_score) > 0.7:  # High positive or negative feedback
                knowledge_ids = await self.vector_db.extract_and_index_knowledge(
                    content=content,
                    source_id=f"interaction_{interaction_id}",
                    knowledge_type="experiential",
                    metadata={
                        **interaction_metadata,
                        'source_type': 'interaction',
                        'feedback_based': True
                    }
                )
            
            self.logger.info("Interaction memory stored", 
                           memory_id=memory_id,
                           feedback_score=feedback_score,
                           knowledge_extracted=len(knowledge_ids))
            
            return {
                'success': True,
                'memory_id': memory_id,
                'interaction_id': interaction_id,
                'feedback_score': feedback_score,
                'knowledge_extracted': len(knowledge_ids),
                'knowledge_ids': knowledge_ids,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as error:
            self.logger.error("Failed to store interaction memory", 
                            interaction_id=interaction_id, error=str(error))
            return {
                'success': False,
                'error': str(error),
                'interaction_id': interaction_id,
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_conversation_history(self, conversation_id: str, 
                                     context_window: int = 10) -> Dict[str, Any]:
        """Get comprehensive conversation history with context"""
        try:
            context = await self.vector_db.get_conversation_context(
                conversation_id=conversation_id,
                context_window=context_window
            )
            
            # Enhance with related knowledge
            if context.get('context_summary'):
                related_knowledge = await self.vector_db.semantic_search(
                    query=context['context_summary'],
                    memory_types=['knowledge'],
                    limit=5,
                    similarity_threshold=0.6
                )
                context['related_knowledge'] = related_knowledge
            
            context['success'] = True
            context['timestamp'] = datetime.now().isoformat()
            
            return context
            
        except Exception as error:
            self.logger.error("Failed to get conversation history", 
                            conversation_id=conversation_id, error=str(error))
            return {
                'success': False,
                'error': str(error),
                'conversation_id': conversation_id,
                'timestamp': datetime.now().isoformat()
            }
    
    async def extract_knowledge(self, content: str, source_id: str,
                              knowledge_type: str = "general",
                              metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract and index knowledge from content"""
        try:
            knowledge_ids = await self.vector_db.extract_and_index_knowledge(
                content=content,
                source_id=source_id,
                knowledge_type=knowledge_type,
                metadata=metadata
            )
            
            return {
                'success': True,
                'source_id': source_id,
                'knowledge_type': knowledge_type,
                'extracted_count': len(knowledge_ids),
                'knowledge_ids': knowledge_ids,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as error:
            self.logger.error("Knowledge extraction failed", 
                            source_id=source_id, error=str(error))
            return {
                'success': False,
                'error': str(error),
                'source_id': source_id,
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            stats = await self.vector_db.get_memory_statistics()
            
            # Add interface-level statistics
            stats['interface'] = {
                'cache_entries': len(self.query_cache),
                'cache_hit_potential': len(self.query_cache) > 0,
                'query_interface_active': True
            }
            
            return stats
            
        except Exception as error:
            self.logger.error("Failed to get memory stats", error=str(error))
            return {
                'error': str(error),
                'timestamp': datetime.now().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            health = await self.vector_db.health_check()
            
            # Add interface health
            health['memory_interface'] = {
                'initialized': self.vector_db.is_initialized,
                'cache_size': len(self.query_cache),
                'query_interface_healthy': True
            }
            
            return health
            
        except Exception as error:
            self.logger.error("Health check failed", error=str(error))
            return {
                'status': 'unhealthy',
                'error': str(error),
                'timestamp': datetime.now().isoformat()
            }


def create_memory_api(memory_interface: AIMemoryQueryInterface) -> FastAPI:
    """Create FastAPI application with memory endpoints"""
    
    app = FastAPI(
        title="AI Long-Term Memory API",
        description="API for AI semantic memory storage and retrieval",
        version="1.0.0"
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        health = await memory_interface.health_check()
        return JSONResponse(content=health)
    
    @app.get("/stats")
    async def get_stats():
        """Get memory statistics"""
        stats = await memory_interface.get_memory_stats()
        return JSONResponse(content=stats)
    
    @app.post("/query")
    async def query_memory(query_request: MemoryQuery):
        """Query memory with semantic search"""
        result = await memory_interface.ask_memory(
            query=query_request.query,
            context_id=query_request.context_id,
            memory_types=query_request.memory_types,
            limit=query_request.limit
        )
        return JSONResponse(content=result)
    
    @app.post("/conversation")
    async def store_conversation(conversation: ConversationMemory):
        """Store conversation memory"""
        result = await memory_interface.remember_conversation(
            conversation_id=conversation.conversation_id,
            content=conversation.content,
            metadata=conversation.metadata
        )
        return JSONResponse(content=result)
    
    @app.get("/conversation/{conversation_id}")
    async def get_conversation(conversation_id: str, context_window: int = Query(10, ge=1, le=50)):
        """Get conversation history and context"""
        result = await memory_interface.get_conversation_history(
            conversation_id=conversation_id,
            context_window=context_window
        )
        return JSONResponse(content=result)
    
    @app.post("/interaction")
    async def store_interaction(
        interaction_id: str = Body(...),
        content: str = Body(...),
        interaction_type: str = Body("general"),
        feedback_score: float = Body(0, ge=-1, le=1),
        metadata: Optional[Dict[str, Any]] = Body(None)
    ):
        """Store interaction memory with feedback"""
        result = await memory_interface.learn_from_interaction(
            interaction_id=interaction_id,
            content=content,
            interaction_type=interaction_type,
            feedback_score=feedback_score,
            metadata=metadata
        )
        return JSONResponse(content=result)
    
    @app.post("/extract")
    async def extract_knowledge(extraction: KnowledgeExtraction):
        """Extract and index knowledge from content"""
        result = await memory_interface.extract_knowledge(
            content=extraction.content,
            source_id=extraction.source_id,
            knowledge_type=extraction.knowledge_type,
            metadata=extraction.metadata
        )
        return JSONResponse(content=result)
    
    @app.post("/batch")
    async def batch_store_memories(batch: MemoryBatch):
        """Store multiple memories in batch"""
        # Convert Pydantic models to dicts for batch processing
        memory_dicts = []
        for memory in batch.memories:
            memory_dict = {
                'type': memory.memory_type,
                'content': memory.content,
                'metadata': memory.metadata or {},
                'id': str(uuid4())
            }
            memory_dicts.append(memory_dict)
        
        result = await memory_interface.vector_db.batch_store_memories(memory_dicts)
        return JSONResponse(content=result)
    
    @app.get("/search")
    async def search_memories(
        query: str = Query(..., description="Search query"),
        memory_types: str = Query(None, description="Comma-separated memory types"),
        limit: int = Query(10, ge=1, le=50),
        similarity_threshold: float = Query(0.7, ge=0.0, le=1.0)
    ):
        """Simple memory search endpoint"""
        memory_types_list = memory_types.split(',') if memory_types else None
        
        results = await memory_interface.vector_db.semantic_search(
            query=query,
            memory_types=memory_types_list,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        return JSONResponse(content={
            'query': query,
            'results': results,
            'count': len(results),
            'timestamp': datetime.now().isoformat()
        })
    
    @app.delete("/cleanup")
    async def cleanup_old_memories(max_age_days: int = Query(365, ge=1)):
        """Clean up old memories"""
        try:
            cleanup_stats = await memory_interface.vector_db.cleanup_old_memories(max_age_days)
            return JSONResponse(content={
                'success': True,
                'cleanup_stats': cleanup_stats,
                'max_age_days': max_age_days,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as error:
            return JSONResponse(
                status_code=500,
                content={
                    'success': False,
                    'error': str(error),
                    'timestamp': datetime.now().isoformat()
                }
            )
    
    return app


# Factory function to create initialized memory interface
async def create_memory_interface(persist_directory: str = None) -> AIMemoryQueryInterface:
    """Create and initialize AI Memory Query Interface"""
    try:
        # Get Data Access Layer
        dal = get_dal()
        await dal.initialize()
        
        # Create Vector Memory Database
        vector_db = VectorMemoryDatabase(dal, persist_directory)
        await vector_db.initialize()
        
        # Create and initialize interface
        interface = AIMemoryQueryInterface(vector_db)
        await interface.initialize()
        
        return interface
        
    except Exception as error:
        logging.error(f"Failed to create memory interface: {error}")
        raise