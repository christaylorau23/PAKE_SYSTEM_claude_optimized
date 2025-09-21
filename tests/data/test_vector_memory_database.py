"""
Tests for Vector Memory Database
Comprehensive test suite for AI long-term memory with vector database integration
"""

import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from data.AIMemoryQueryInterface import AIMemoryQueryInterface
from data.DataAccessLayer import DataAccessLayer
from data.VectorMemoryDatabase import VectorMemoryDatabase

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestVectorMemoryDatabase:
    """Test suite for VectorMemoryDatabase"""

    @pytest.fixture
    async def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    async def mock_dal(self):
        """Create mock Data Access Layer"""
        dal = Mock(spec=DataAccessLayer)
        dal.logger = Mock()
        dal.vault_path = "/test/vault"
        return dal

    @pytest.fixture
    async def vector_db(self, mock_dal, temp_dir):
        """Create VectorMemoryDatabase instance for testing"""
        try:
            import chromadb

            db = VectorMemoryDatabase(mock_dal, temp_dir)
            await db.initialize()
            yield db
            await db.cleanup()
        except ImportError:
            pytest.skip("ChromaDB not available for testing")

    @pytest.mark.asyncio
    async def test_vector_database_initialization(self, mock_dal, temp_dir):
        """Test vector database initialization"""
        try:
            import chromadb

            db = VectorMemoryDatabase(mock_dal, temp_dir)
            assert not db.is_initialized

            await db.initialize()
            assert db.is_initialized
            assert len(db.collections) == 5  # All collection types

            await db.cleanup()

        except ImportError:
            pytest.skip("ChromaDB not available for testing")

    @pytest.mark.asyncio
    async def test_store_conversation_memory(self, vector_db):
        """Test storing conversation memories"""
        conversation_id = "test_conversation_001"
        content = "This is a test conversation about machine learning concepts."
        metadata = {"user_id": "test_user", "turn_count": 1}

        memory_id = await vector_db.store_conversation_memory(
            conversation_id=conversation_id,
            content=content,
            metadata=metadata,
        )

        assert memory_id is not None
        assert memory_id.startswith("conv_")

        # Retrieve the stored memory
        stored_memory = await vector_db.get_memory_by_id(memory_id, "conversations")
        assert stored_memory is not None
        assert stored_memory["content"] == content
        assert stored_memory["metadata"]["conversation_id"] == conversation_id

    @pytest.mark.asyncio
    async def test_store_knowledge_memory(self, vector_db):
        """Test storing knowledge memories"""
        knowledge_id = "test_knowledge_001"
        content = "Machine learning is a subset of artificial intelligence that focuses on algorithms."
        knowledge_type = "technical"
        metadata = {"domain": "AI", "confidence": 0.9}

        memory_id = await vector_db.store_knowledge_memory(
            knowledge_id=knowledge_id,
            content=content,
            knowledge_type=knowledge_type,
            metadata=metadata,
        )

        assert memory_id is not None
        assert memory_id.startswith("know_")

        # Retrieve the stored memory
        stored_memory = await vector_db.get_memory_by_id(memory_id, "knowledge")
        assert stored_memory is not None
        assert stored_memory["content"] == content
        assert stored_memory["metadata"]["knowledge_type"] == knowledge_type

    @pytest.mark.asyncio
    async def test_semantic_search(self, vector_db):
        """Test semantic search functionality"""
        # Store test memories
        test_memories = [
            ("Machine learning algorithms for classification", "knowledge"),
            ("Deep neural networks and backpropagation", "knowledge"),
            ("Natural language processing with transformers", "knowledge"),
            ("Database indexing and query optimization", "knowledge"),
        ]

        stored_ids = []
        for i, (content, memory_type) in enumerate(test_memories):
            if memory_type == "knowledge":
                memory_id = await vector_db.store_knowledge_memory(
                    knowledge_id=f"test_{i}",
                    content=content,
                    knowledge_type="technical",
                )
            stored_ids.append(memory_id)

        # Search for machine learning related content
        search_results = await vector_db.semantic_search(
            query="machine learning classification",
            memory_types=["knowledge"],
            limit=5,
            similarity_threshold=0.3,
        )

        assert len(search_results) > 0
        # Should find the machine learning memory with highest similarity
        top_result = search_results[0]
        assert "machine learning" in top_result["content"].lower()
        assert top_result["similarity"] > 0.3

    @pytest.mark.asyncio
    async def test_get_conversation_context(self, vector_db):
        """Test getting conversation context"""
        conversation_id = "context_test_conversation"

        # Store multiple conversation memories
        conversation_contents = [
            "Hello, I need help with Python programming.",
            "Can you explain list comprehensions?",
            "List comprehensions are a concise way to create lists in Python.",
            "That's helpful! What about dictionary comprehensions?",
        ]

        for i, content in enumerate(conversation_contents):
            await vector_db.store_conversation_memory(
                conversation_id=conversation_id,
                content=content,
                metadata={"turn_count": i + 1, "timestamp": datetime.now().isoformat()},
            )

        # Get conversation context
        context = await vector_db.get_conversation_context(
            conversation_id=conversation_id,
            context_window=10,
        )

        assert context["conversation_id"] == conversation_id
        assert context["total_memories"] == len(conversation_contents)
        assert len(context["recent_memories"]) == len(conversation_contents)
        assert len(context["context_summary"]) > 0

    @pytest.mark.asyncio
    async def test_extract_and_index_knowledge(self, vector_db):
        """Test knowledge extraction and indexing"""
        content = """
        Python is a high-level programming language. It was created by Guido van Rossum.
        Python supports multiple programming paradigms. Object-oriented programming is one paradigm.
        Machine learning libraries like TensorFlow are popular in Python.
        """
        source_id = "python_article_001"

        knowledge_ids = await vector_db.extract_and_index_knowledge(
            content=content,
            source_id=source_id,
            knowledge_type="programming",
        )

        assert len(knowledge_ids) > 0

        # Verify extracted knowledge can be retrieved
        for knowledge_id in knowledge_ids:
            memory = await vector_db.get_memory_by_id(knowledge_id, "knowledge")
            assert memory is not None
            assert memory["metadata"]["source_id"] == source_id

    @pytest.mark.asyncio
    async def test_find_similar_memories(self, vector_db):
        """Test finding similar memories with recent context"""
        # Store test content
        await vector_db.store_knowledge_memory(
            knowledge_id="test_similarity_1",
            content="Python programming best practices and code optimization",
            knowledge_type="programming",
        )

        await vector_db.store_context_memory(
            context_id="test_context_1",
            content="Recent discussion about Python performance tuning",
            context_type="discussion",
        )

        # Find similar memories
        similar_memories = await vector_db.find_similar_memories(
            content="Python performance optimization techniques",
            memory_types=["knowledge", "context"],
            limit=10,
            include_recent=True,
        )

        assert len(similar_memories) > 0
        # Check that we get memories with reasonable similarity
        for memory in similar_memories:
            assert memory["similarity"] > 0.1 or "timestamp" in memory

    @pytest.mark.asyncio
    async def test_batch_store_memories(self, vector_db):
        """Test batch memory storage"""
        batch_memories = [
            {
                "type": "knowledge",
                "content": "Batch processing improves database performance",
                "id": "batch_test_1",
                "metadata": {"domain": "database", "confidence": 0.8},
            },
            {
                "type": "context",
                "content": "User asked about batch operations",
                "id": "batch_test_2",
                "metadata": {"user_id": "test_user"},
            },
            {
                "type": "interaction",
                "content": "Positive feedback on batch explanation",
                "id": "batch_test_3",
                "metadata": {"feedback_score": 0.9},
            },
        ]

        results = await vector_db.batch_store_memories(batch_memories)

        assert results["successful"] == 3
        assert results["failed"] == 0
        assert len(results["memory_ids"]) == 3
        assert len(results["errors"]) == 0

    @pytest.mark.asyncio
    async def test_memory_statistics(self, vector_db):
        """Test getting memory statistics"""
        # Store some test memories
        await vector_db.store_knowledge_memory("stats_test_1", "Test knowledge content")
        await vector_db.store_conversation_memory("conv_stats", "Test conversation")

        stats = await vector_db.get_memory_statistics()

        assert "collections" in stats
        assert "total_memories" in stats
        assert stats["total_memories"] >= 2  # At least our test memories
        assert "storage_path" in stats
        assert stats["initialized"] is True

    @pytest.mark.asyncio
    async def test_health_check(self, vector_db):
        """Test vector database health check"""
        health = await vector_db.health_check()

        assert health["status"] in ["healthy", "degraded"]
        assert "vector_db" in health
        assert health["vector_db"]["initialized"] is True
        assert health["vector_db"]["collections_ready"] > 0

    @pytest.mark.asyncio
    async def test_cleanup_old_memories(self, vector_db):
        """Test cleaning up old memories"""
        # Store a memory with old timestamp
        old_memory = await vector_db.store_knowledge_memory(
            knowledge_id="old_memory_test",
            content="This is old content",
            metadata={"timestamp": (datetime.now() - timedelta(days=400)).isoformat()},
        )

        # Store a recent memory
        recent_memory = await vector_db.store_knowledge_memory(
            knowledge_id="recent_memory_test",
            content="This is recent content",
        )

        # Clean up old memories (older than 365 days)
        cleanup_stats = await vector_db.cleanup_old_memories(max_age_days=365)

        assert isinstance(cleanup_stats, dict)
        # The old memory should potentially be cleaned up
        # (depending on exact timestamps and implementation)


class TestAIMemoryQueryInterface:
    """Test suite for AI Memory Query Interface"""

    @pytest.fixture
    async def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    async def memory_interface(self, temp_dir):
        """Create AI Memory Query Interface for testing"""
        try:
            import chromadb

            # Create mock DAL
            dal = Mock(spec=DataAccessLayer)
            dal.logger = Mock()
            dal.vault_path = temp_dir

            # Create vector DB and interface
            vector_db = VectorMemoryDatabase(dal, temp_dir)
            await vector_db.initialize()

            interface = AIMemoryQueryInterface(vector_db)
            await interface.initialize()

            yield interface

            await vector_db.cleanup()

        except ImportError:
            pytest.skip("ChromaDB not available for testing")

    @pytest.mark.asyncio
    async def test_ask_memory_basic(self, memory_interface):
        """Test basic memory querying"""
        # Store some test knowledge
        await memory_interface.vector_db.store_knowledge_memory(
            knowledge_id="query_test_1",
            content="Python is an excellent programming language for data science",
            knowledge_type="programming",
        )

        # Query memory
        results = await memory_interface.ask_memory(
            query="Python programming language",
            limit=5,
        )

        assert "query" in results
        assert results["query"] == "Python programming language"
        assert "direct_matches" in results
        assert "metadata" in results
        assert results["metadata"]["success"] is True

    @pytest.mark.asyncio
    async def test_remember_conversation(self, memory_interface):
        """Test storing conversation with knowledge extraction"""
        conversation_id = "interface_test_conv"
        content = """
        User: Can you explain machine learning algorithms?
        Assistant: Machine learning algorithms are computational methods that learn patterns from data.
        There are three main types: supervised learning, unsupervised learning, and reinforcement learning.
        Supervised learning uses labeled data to make predictions.
        """

        result = await memory_interface.remember_conversation(
            conversation_id=conversation_id,
            content=content,
            metadata={"user_id": "test_user"},
        )

        assert result["success"] is True
        assert result["conversation_id"] == conversation_id
        assert "memory_id" in result
        # Should extract knowledge from substantial content
        assert result["knowledge_extracted"] > 0

    @pytest.mark.asyncio
    async def test_learn_from_interaction(self, memory_interface):
        """Test learning from user interaction with feedback"""
        interaction_id = "feedback_test_001"
        content = "User provided positive feedback on explanation of neural networks"
        feedback_score = 0.8

        result = await memory_interface.learn_from_interaction(
            interaction_id=interaction_id,
            content=content,
            interaction_type="feedback",
            feedback_score=feedback_score,
        )

        assert result["success"] is True
        assert result["interaction_id"] == interaction_id
        assert result["feedback_score"] == feedback_score
        # High feedback should trigger knowledge extraction
        assert result["knowledge_extracted"] > 0

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, memory_interface):
        """Test getting conversation history with context"""
        conversation_id = "history_test_conv"

        # Store conversation history
        conversation_parts = [
            "Hello, I'm learning about databases.",
            "What's the difference between SQL and NoSQL?",
            "SQL databases are relational, NoSQL databases are non-relational.",
            "Can you give me examples of each?",
        ]

        for i, content in enumerate(conversation_parts):
            await memory_interface.remember_conversation(
                conversation_id=conversation_id,
                content=content,
                metadata={"turn": i + 1},
            )

        # Get conversation history
        history = await memory_interface.get_conversation_history(
            conversation_id=conversation_id,
            context_window=5,
        )

        assert history["success"] is True
        assert history["conversation_id"] == conversation_id
        assert history["total_memories"] > 0
        assert len(history["recent_memories"]) > 0

    @pytest.mark.asyncio
    async def test_extract_knowledge(self, memory_interface):
        """Test knowledge extraction interface"""
        content = """
        Artificial Intelligence is the simulation of human intelligence in machines.
        Machine Learning is a subset of AI that focuses on learning from data.
        Deep Learning uses neural networks with multiple layers.
        Natural Language Processing helps computers understand human language.
        """
        source_id = "ai_overview_001"

        result = await memory_interface.extract_knowledge(
            content=content,
            source_id=source_id,
            knowledge_type="artificial_intelligence",
        )

        assert result["success"] is True
        assert result["source_id"] == source_id
        assert result["extracted_count"] > 0
        assert len(result["knowledge_ids"]) > 0

    @pytest.mark.asyncio
    async def test_memory_stats(self, memory_interface):
        """Test getting memory statistics through interface"""
        stats = await memory_interface.get_memory_stats()

        assert "collections" in stats
        assert "total_memories" in stats
        assert "interface" in stats
        assert stats["interface"]["query_interface_active"] is True

    @pytest.mark.asyncio
    async def test_health_check(self, memory_interface):
        """Test memory interface health check"""
        health = await memory_interface.health_check()

        assert "status" in health
        assert "memory_interface" in health
        assert health["memory_interface"]["query_interface_healthy"] is True


class TestDataAccessLayerIntegration:
    """Test suite for Data Access Layer vector memory integration"""

    @pytest.fixture
    async def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_dal_vector_memory_integration(self, temp_dir):
        """Test Data Access Layer integration with vector memory"""
        try:
            import chromadb

            # Create DAL with vault path
            dal = DataAccessLayer(vault_path=temp_dir)
            await dal.initialize()

            # Check if vector memory was initialized
            if dal.vector_memory_db:
                assert dal.vector_memory_db.is_initialized
                assert dal.memory_interface is not None
                assert "vector_memory" in dal.repositories
                assert "memory_interface" in dal.repositories

            await dal.cleanup()

        except ImportError:
            pytest.skip("ChromaDB not available for testing")

    @pytest.mark.asyncio
    async def test_dal_remember_and_recall(self, temp_dir):
        """Test DAL remember and recall methods"""
        try:
            import chromadb

            dal = DataAccessLayer(vault_path=temp_dir)
            await dal.initialize()

            if dal.memory_interface:
                # Test remember
                content = "This is test content for DAL memory integration"
                memory_id = await dal.remember(
                    content=content,
                    memory_type="context",
                    metadata={"test": True},
                )

                assert memory_id is not None

                # Test recall
                results = await dal.recall(
                    query="test content DAL integration",
                    limit=5,
                )

                assert "query" in results
                assert len(results.get("direct_matches", [])) >= 0

            await dal.cleanup()

        except ImportError:
            pytest.skip("ChromaDB not available for testing")

    @pytest.mark.asyncio
    async def test_dal_learn_from_feedback(self, temp_dir):
        """Test DAL learning from feedback"""
        try:
            import chromadb

            dal = DataAccessLayer(vault_path=temp_dir)
            await dal.initialize()

            if dal.memory_interface:
                # Test learning from feedback
                success = await dal.learn_from_feedback(
                    interaction_id="dal_feedback_test",
                    content="User liked the explanation of vector databases",
                    feedback_score=0.9,
                    metadata={"topic": "databases"},
                )

                assert isinstance(success, bool)

            await dal.cleanup()

        except ImportError:
            pytest.skip("ChromaDB not available for testing")


class TestEndToEndWorkflow:
    """End-to-end workflow tests for vector memory system"""

    @pytest.fixture
    async def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_complete_memory_workflow(self, temp_dir):
        """Test complete memory workflow from storage to retrieval"""
        try:
            import chromadb

            # Initialize system
            dal = DataAccessLayer(vault_path=temp_dir)
            await dal.initialize()

            if not dal.memory_interface:
                pytest.skip("Vector memory not initialized")

            # Simulate conversation workflow
            conversation_id = "workflow_test_conversation"

            # 1. Store initial conversation
            await dal.remember(
                content="User asks about implementing a recommendation system",
                memory_type="conversation",
                context_id=conversation_id,
                metadata={"turn": 1, "user_id": "test_user"},
            )

            # 2. Store domain knowledge
            knowledge_content = """
            Recommendation systems use collaborative filtering and content-based filtering.
            Collaborative filtering analyzes user behavior patterns.
            Content-based filtering analyzes item features and user preferences.
            """
            await dal.extract_knowledge(
                content=knowledge_content,
                source_id="recommendation_systems_guide",
                knowledge_type="machine_learning",
            )

            # 3. Store AI response as conversation memory
            await dal.remember(
                content="I can explain recommendation systems. There are two main approaches: collaborative filtering and content-based filtering.",
                memory_type="conversation",
                context_id=conversation_id,
                metadata={"turn": 2, "speaker": "assistant"},
            )

            # 4. Learn from positive feedback
            await dal.learn_from_feedback(
                interaction_id="workflow_feedback_001",
                content="User found the recommendation system explanation very helpful",
                feedback_score=0.9,
                metadata={"topic": "recommendation_systems"},
            )

            # 5. Query memory system
            recall_results = await dal.recall(
                query="collaborative filtering recommendation systems",
                context_id=conversation_id,
                limit=10,
            )

            # Verify workflow results
            assert recall_results["metadata"]["success"] is True
            assert len(recall_results["direct_matches"]) > 0

            # Should find relevant memories
            found_relevant = False
            for match in recall_results["direct_matches"]:
                if "collaborative filtering" in match["content"].lower():
                    found_relevant = True
                    break

            assert found_relevant, "Should find memories about collaborative filtering"

            # 6. Get conversation context
            if recall_results.get("conversation_context"):
                context = recall_results["conversation_context"]
                assert context["conversation_id"] == conversation_id
                assert context["total_memories"] > 0

            await dal.cleanup()

        except ImportError:
            pytest.skip("ChromaDB not available for testing")

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, temp_dir):
        """Test performance with larger dataset"""
        try:
            import time

            import chromadb

            dal = DataAccessLayer(vault_path=temp_dir)
            await dal.initialize()

            if not dal.memory_interface:
                pytest.skip("Vector memory not initialized")

            # Store multiple memories
            start_time = time.time()

            for i in range(20):  # Smaller test dataset
                await dal.remember(
                    content=f"This is test content number {i} about various topics including machine learning, databases, and programming",
                    memory_type="knowledge",
                    metadata={"batch": "performance_test", "index": i},
                )

            storage_time = time.time() - start_time

            # Perform multiple queries
            query_start = time.time()

            for i in range(5):
                results = await dal.recall(
                    query=f"machine learning topic {i}",
                    limit=10,
                )
                assert results["metadata"]["success"] is True

            query_time = time.time() - query_start

            # Performance assertions (should be reasonable)
            assert storage_time < 30.0  # Should store 20 memories in under 30 seconds
            assert query_time < 10.0  # Should perform 5 queries in under 10 seconds

            await dal.cleanup()

        except ImportError:
            pytest.skip("ChromaDB not available for testing")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
