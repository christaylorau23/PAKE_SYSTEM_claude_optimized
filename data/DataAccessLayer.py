import asyncio
import threading
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime
from uuid import uuid4
import sys
import os

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.logger import get_logger


class DataAccessLayer:
    """
    Central Data Access Layer for PAKE System
    Provides unified access to filesystem and caching operations
    """

    def __init__(self, vault_path: str = None):
        self.vault_path = vault_path
        self.logger = get_logger("data-access-layer")
        self.repositories = {}
        self.is_initialized = False
        self._lock = threading.RLock()

        # Cache TTL configurations (in seconds)
        self.cache_ttl = {
            'short': 300,    # 5 minutes
            'medium': 1800,  # 30 minutes
            'long': 7200     # 2 hours
        }

        # Vector memory database integration
        self.vector_memory_db = None
        self.memory_interface = None

    async def initialize(self) -> None:
        """Initialize the Data Access Layer"""
        try:
            self.logger.info("Initializing Data Access Layer", vault_path=self.vault_path)

            # Ensure vault directory exists if specified
            if self.vault_path:
                import os
                os.makedirs(self.vault_path, exist_ok=True)

            # Initialize vector memory database if enabled
            await self._initialize_vector_memory()

            self.is_initialized = True
            self.logger.info("Data Access Layer initialized successfully")

        except Exception as error:
            self.logger.error("Failed to initialize Data Access Layer", error=str(error))
            raise

    def register_repository(self, name: str, repository_instance) -> Any:
        """Register a repository with the DAL"""
        if not repository_instance:
            raise ValueError(f"Repository instance is required for {name}")

        with self._lock:
            # Inject DAL dependencies into the repository if it has the method
            if hasattr(repository_instance, 'set_dal'):
                repository_instance.set_dal(self)

            self.repositories[name] = repository_instance

            self.logger.info("Repository registered",
                           name=name,
                           type=repository_instance.__class__.__name__)

            return repository_instance

    def get_repository(self, name: str):
        """Get a registered repository by name"""
        repository = self.repositories.get(name)
        if not repository:
            available = list(self.repositories.keys())
            raise KeyError(f"Repository '{name}' not found. Available repositories: {available}")

        return repository

    def generate_cache_key(self, namespace: str, *parts) -> str:
        """Generate standardized cache keys"""
        sanitized_parts = []
        for part in parts:
            if part is not None:
                # Convert to string and sanitize
                part_str = str(part).replace(':', '_').replace('|', '_')
                sanitized_parts.append(part_str)

        return f"{namespace}:{'|'.join(sanitized_parts)}"

    async def execute_with_retry(self, operation: Callable, max_retries: int = 3,
                               delay: float = 1.0) -> Any:
        """Execute operation with retry logic"""
        last_error = None

        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation()
                else:
                    return operation()

            except Exception as error:
                last_error = error
                if attempt < max_retries - 1:
                    self.logger.warn(f"Operation failed, retrying in {delay}s",
                                   attempt=attempt + 1,
                                   max_retries=max_retries,
                                   error=str(error))
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    break

        self.logger.error("Operation failed after all retries",
                        max_retries=max_retries,
                        error=str(last_error))
        raise last_error

    def validate_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against a schema"""
        validated_data = {}
        errors = []

        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")

        # Type validation
        field_types = schema.get('types', {})
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    errors.append(f"Field '{field}' must be of type {expected_type.__name__}")

        # Length validation
        field_lengths = schema.get('max_lengths', {})
        for field, max_length in field_lengths.items():
            if field in data and isinstance(data[field], str):
                if len(data[field]) > max_length:
                    errors.append(f"Field '{field}' exceeds maximum length of {max_length}")

        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")

        # Copy valid fields
        allowed_fields = schema.get('fields', data.keys())
        for field in allowed_fields:
            if field in data:
                validated_data[field] = data[field]

        return validated_data

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for all registered repositories"""
        health = {
            'status': 'healthy',
            'dal': {
                'initialized': self.is_initialized,
                'repositories_count': len(self.repositories)
            },
            'repositories': {},
            'timestamp': datetime.now().isoformat()
        }

        # Check each repository
        for name, repository in self.repositories.items():
            try:
                if hasattr(repository, 'health_check'):
                    if asyncio.iscoroutinefunction(repository.health_check):
                        repo_health = await repository.health_check()
                    else:
                        repo_health = repository.health_check()

                    health['repositories'][name] = repo_health

                    # Update overall status if any repository is unhealthy
                    if repo_health.get('status') != 'healthy':
                        health['status'] = 'degraded'
                else:
                    health['repositories'][name] = {
                        'status': 'unknown',
                        'message': 'No health check method available'
                    }

            except Exception as error:
                health['repositories'][name] = {
                    'status': 'unhealthy',
                    'error': str(error)
                }
                health['status'] = 'degraded'

        return health

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for the DAL and all repositories"""
        stats = {
            'dal': {
                'initialized': self.is_initialized,
                'repositories': list(self.repositories.keys()),
                'vault_path': self.vault_path
            },
            'repositories': {}
        }

        # Get stats from each repository
        for name, repository in self.repositories.items():
            try:
                if hasattr(repository, 'get_stats'):
                    repo_stats = repository.get_stats()
                    stats['repositories'][name] = repo_stats
                else:
                    stats['repositories'][name] = {
                        'status': 'no_stats_method'
                    }
            except Exception as error:
                stats['repositories'][name] = {
                    'status': 'error',
                    'error': str(error)
                }

        return stats

    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            self.logger.info("Starting DAL cleanup")

            # Cleanup repositories
            for name, repository in self.repositories.items():
                try:
                    if hasattr(repository, 'cleanup'):
                        if asyncio.iscoroutinefunction(repository.cleanup):
                            await repository.cleanup()
                        else:
                            repository.cleanup()
                except Exception as error:
                    self.logger.error(f"Error cleaning up repository {name}", error=str(error))

            self.repositories.clear()
            self.is_initialized = False

            self.logger.info("DAL cleanup completed")

        except Exception as error:
            self.logger.error("Error during DAL cleanup", error=str(error))
            raise

    def batch_operation(self, operations: List[Callable]) -> List[Any]:
        """Execute multiple operations as a batch"""
        results = []
        errors = []

        for i, operation in enumerate(operations):
            try:
                if asyncio.iscoroutinefunction(operation):
                    # For async operations, we'd need to handle differently
                    # For now, assume synchronous operations in batch
                    self.logger.warn("Async operations not supported in batch_operation")
                    result = None
                else:
                    result = operation()

                results.append(result)

            except Exception as error:
                self.logger.error(f"Batch operation {i} failed", error=str(error))
                errors.append({'index': i, 'error': str(error)})
                results.append(None)

        return {
            'results': results,
            'errors': errors,
            'success_count': len(results) - len(errors),
            'total_count': len(operations)
        }

    def create_transaction_context(self):
        """Create a transaction context for coordinated operations"""
        return TransactionContext(self)

    async def _initialize_vector_memory(self) -> None:
        """Initialize vector memory database integration"""
        try:
            # Only initialize if chromadb is available
            try:
                import chromadb
                from .VectorMemoryDatabase import VectorMemoryDatabase
                from .AIMemoryQueryInterface import AIMemoryQueryInterface

                # Create vector memory database
                persist_dir = None
                if self.vault_path:
                    persist_dir = os.path.join(self.vault_path, "vector_memory")

                self.vector_memory_db = VectorMemoryDatabase(self, persist_dir)
                await self.vector_memory_db.initialize()

                # Create memory interface
                self.memory_interface = AIMemoryQueryInterface(self.vector_memory_db)
                await self.memory_interface.initialize()

                # Register as repositories
                self.register_repository('vector_memory', self.vector_memory_db)
                self.register_repository('memory_interface', self.memory_interface)

                self.logger.info("Vector memory database integration initialized successfully")

            except ImportError:
                self.logger.info("ChromaDB not available - vector memory features disabled")

        except Exception as error:
            self.logger.warn("Failed to initialize vector memory integration", error=str(error))
            # Don't fail the entire DAL initialization if vector memory fails

    async def remember(self, content: str, memory_type: str = "context",
                      context_id: str = None, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Store content in long-term memory"""
        if not self.memory_interface:
            self.logger.warn("Vector memory not available")
            return None

        try:
            if memory_type == "conversation" and context_id:
                result = await self.memory_interface.remember_conversation(
                    conversation_id=context_id,
                    content=content,
                    metadata=metadata
                )
                return result.get('memory_id') if result.get('success') else None
            else:
                # Store as context memory
                memory_id = await self.vector_memory_db.store_context_memory(
                    context_id=context_id or str(uuid4()),
                    content=content,
                    context_type=memory_type,
                    metadata=metadata
                )
                return memory_id

        except Exception as error:
            self.logger.error("Failed to store memory", error=str(error))
            return None

    async def recall(self, query: str, context_id: str = None,
                    memory_types: List[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Query long-term memory"""
        if not self.memory_interface:
            return {
                'query': query,
                'results': [],
                'error': 'Vector memory not available'
            }

        try:
            results = await self.memory_interface.ask_memory(
                query=query,
                context_id=context_id,
                memory_types=memory_types,
                limit=limit
            )
            return results

        except Exception as error:
            self.logger.error("Memory recall failed", error=str(error))
            return {
                'query': query,
                'results': [],
                'error': str(error)
            }

    async def learn_from_feedback(self, interaction_id: str, content: str,
                                 feedback_score: float, metadata: Dict[str, Any] = None) -> bool:
        """Learn from interaction feedback"""
        if not self.memory_interface:
            return False

        try:
            result = await self.memory_interface.learn_from_interaction(
                interaction_id=interaction_id,
                content=content,
                feedback_score=feedback_score,
                metadata=metadata
            )
            return result.get('success', False)

        except Exception as error:
            self.logger.error("Failed to learn from feedback", error=str(error))
            return False

    async def extract_knowledge(self, content: str, source_id: str,
                              knowledge_type: str = "general") -> List[str]:
        """Extract and index knowledge from content"""
        if not self.memory_interface:
            return []

        try:
            result = await self.memory_interface.extract_knowledge(
                content=content,
                source_id=source_id,
                knowledge_type=knowledge_type
            )
            return result.get('knowledge_ids', [])

        except Exception as error:
            self.logger.error("Knowledge extraction failed", error=str(error))
            return []


class TransactionContext:
    """Transaction context for coordinated operations across repositories"""

    def __init__(self, dal: DataAccessLayer):
        self.dal = dal
        self.operations = []
        self.rollback_operations = []
        self.completed = False
        self.logger = dal.logger

    def add_operation(self, operation: Callable, rollback: Callable = None):
        """Add operation to transaction"""
        self.operations.append(operation)
        if rollback:
            self.rollback_operations.append(rollback)

    async def execute(self) -> Dict[str, Any]:
        """Execute all operations in transaction"""
        results = []
        executed_count = 0

        try:
            self.logger.info("Starting transaction", operations_count=len(self.operations))

            for i, operation in enumerate(self.operations):
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()

                results.append(result)
                executed_count += 1

            self.completed = True
            self.logger.info("Transaction completed successfully",
                           operations_executed=executed_count)

            return {
                'success': True,
                'results': results,
                'operations_executed': executed_count
            }

        except Exception as error:
            self.logger.error("Transaction failed, starting rollback",
                            executed_count=executed_count,
                            error=str(error))

            # Execute rollback operations in reverse order
            rollback_count = 0
            rollback_errors = []

            for i, rollback_op in enumerate(reversed(self.rollback_operations[:executed_count])):
                try:
                    if asyncio.iscoroutinefunction(rollback_op):
                        await rollback_op()
                    else:
                        rollback_op()

                    rollback_count += 1

                except Exception as rollback_error:
                    rollback_errors.append({
                        'index': i,
                        'error': str(rollback_error)
                    })

            self.logger.info("Rollback completed",
                           rollback_operations=rollback_count,
                           rollback_errors=len(rollback_errors))

            return {
                'success': False,
                'error': str(error),
                'operations_executed': executed_count,
                'rollback_operations': rollback_count,
                'rollback_errors': rollback_errors
            }


# Singleton instance
dal = DataAccessLayer()


def get_dal(vault_path: str = None) -> DataAccessLayer:
    """Get Data Access Layer instance"""
    if vault_path:
        return DataAccessLayer(vault_path)
    return dal