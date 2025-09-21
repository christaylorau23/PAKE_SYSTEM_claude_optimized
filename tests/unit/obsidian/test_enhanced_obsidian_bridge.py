"""
TDD Tests for Enhanced Obsidian Bridge
Following Test-Driven Development principles
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Note: These tests are written FIRST following TDD principles
# Implementation should follow to make these tests pass


@pytest.mark.obsidian
@pytest.mark.unit
class TestEnhancedObsidianBridge:
    """Test suite for Enhanced Obsidian Bridge v3.0"""

    @pytest.fixture
    def bridge_config(self):
        """Configuration for bridge testing."""
        return {
            "vault_path": "/tmp/test_vault",
            "bridge_port": 3001,
            "mcp_server_url": "http://localhost:8000",
            "auto_tag_enabled": True,
            "knowledge_graph_enabled": True,
        }

    @pytest.fixture
    def mock_file_watcher(self):
        """Mock file watcher for testing."""
        watcher = MagicMock()
        watcher.watch = MagicMock()
        watcher.on = MagicMock()
        watcher.close = MagicMock()
        return watcher

    def test_bridge_initialization(self, bridge_config):
        """Test that bridge initializes with correct configuration."""
        # TDD: Write test first, implement after
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(bridge_config)

        assert bridge.config.vault_path == bridge_config["vault_path"]
        assert bridge.config.auto_tag_enabled
        assert bridge.config.knowledge_graph_enabled
        assert bridge.file_watcher is None  # Not started yet

    @pytest.mark.asyncio
    async def test_start_file_watching(self, bridge_config, mock_file_watcher):
        """Test that file watching starts correctly."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        with patch("chokidar.watch", return_value=mock_file_watcher):
            bridge = EnhancedObsidianBridge(bridge_config)
            await bridge.start_file_watching()

            assert bridge.file_watcher is not None
            mock_file_watcher.watch.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_change_detection(self, bridge_config, temp_vault_dir):
        """Test that file changes are detected and processed."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        # Create test file
        test_file = temp_vault_dir / "test_note.md"
        test_file.write_text("# Test Note\nThis is a test note.")

        bridge = EnhancedObsidianBridge(
            {**bridge_config, "vault_path": str(temp_vault_dir)},
        )

        # Simulate file change event
        sync_event = await bridge.handle_file_change("create", str(test_file))

        assert sync_event.type == "create"
        assert sync_event.filepath == str(test_file)
        assert sync_event.metadata is not None
        assert sync_event.metadata.word_count > 0

    @pytest.mark.asyncio
    async def test_auto_tag_generation(self, bridge_config, mock_mcp_server):
        """Test that auto-tagging works correctly."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(bridge_config)
        bridge.mcp_client = mock_mcp_server

        content = (
            "This document discusses machine learning and artificial intelligence."
        )
        tags = await bridge.generate_auto_tags(content, max_tags=5)

        assert isinstance(tags, list)
        assert len(tags) <= 5
        assert all(isinstance(tag, str) for tag in tags)
        mock_mcp_server.auto_tag.assert_called_once()

    @pytest.mark.asyncio
    async def test_metadata_extraction(self, bridge_config, mock_mcp_server):
        """Test enhanced metadata extraction."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(bridge_config)
        bridge.mcp_client = mock_mcp_server

        content = "Dr. John Smith published research at https://example.com/paper"
        metadata = await bridge.extract_metadata(content, include_entities=True)

        assert "basic_stats" in metadata
        assert metadata["basic_stats"]["word_count"] > 0
        mock_mcp_server.extract_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_knowledge_graph_update(self, bridge_config, mock_mcp_server):
        """Test knowledge graph node creation and updates."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(bridge_config)
        bridge.mcp_client = mock_mcp_server

        note_data = {
            "id": "test-note-123",
            "title": "Test Note",
            "type": "note",
            "connections": [],
            "metadata": {"confidence_score": 0.85},
        }

        result = await bridge.update_knowledge_graph(note_data)

        assert result.success
        assert result.node_id == "test-note-123"

    @pytest.mark.asyncio
    async def test_bidirectional_sync(
        self,
        bridge_config,
        temp_vault_dir,
        mock_mcp_server,
    ):
        """Test bidirectional synchronization between vault and MCP server."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(
            {**bridge_config, "vault_path": str(temp_vault_dir)},
        )
        bridge.mcp_client = mock_mcp_server

        # Test vault -> MCP sync
        note_file = temp_vault_dir / "sync_test.md"
        note_content = """---
pake_id: sync-test-123
title: Sync Test
tags: [test, sync]
---

# Sync Test
This is a synchronization test."""

        note_file.write_text(note_content)

        # Simulate file change
        sync_result = await bridge.sync_note_to_mcp(str(note_file))

        assert sync_result.success
        assert sync_result.pake_id == "sync-test-123"
        mock_mcp_server.ingest.assert_called_once()

    def test_enhanced_frontmatter_creation(self, bridge_config):
        """Test enhanced frontmatter generation."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(bridge_config)

        note_data = {
            "title": "Test Note",
            "content": "Test content",
            "type": "note",
            "tags": ["test", "example"],
        }

        frontmatter = bridge.create_enhanced_frontmatter(note_data)

        assert frontmatter.pake_id is not None
        assert frontmatter.title == "Test Note"
        assert frontmatter.type == "note"
        assert "test" in frontmatter.tags
        assert frontmatter.confidence_score >= 0.0
        assert frontmatter.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_enhanced_note_creation_api(self, bridge_config, temp_vault_dir):
        """Test enhanced note creation via API."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(
            {**bridge_config, "vault_path": str(temp_vault_dir)},
        )

        note_data = {
            "title": "API Test Note",
            "content": "This note was created via API",
            "type": "note",
            "auto_tag": True,
        }

        result = await bridge.create_enhanced_note(note_data)

        assert result.success
        assert result.pake_id is not None
        assert result.filepath is not None

        # Verify file was created
        created_file = Path(temp_vault_dir) / result.filepath
        assert created_file.exists()

    @pytest.mark.asyncio
    async def test_enhanced_search_integration(self, bridge_config, mock_mcp_server):
        """Test enhanced search with vault integration."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(bridge_config)
        bridge.mcp_client = mock_mcp_server

        search_params = {
            "query": "machine learning",
            "sources": ["web", "vault"],
            "semantic": True,
            "max_results": 10,
        }

        results = await bridge.perform_enhanced_search(search_params)

        assert "query" in results
        assert "results" in results
        assert "metrics" in results
        assert results["metrics"]["semanticEnabled"]
        mock_mcp_server.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_real_time_sync_monitoring(self, bridge_config):
        """Test real-time sync monitoring functionality."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(bridge_config)

        # Start monitoring
        monitoring_started = await bridge.start_sync_monitoring()
        assert monitoring_started

        # Check monitoring status
        status = bridge.get_sync_status()
        assert status.enabled
        assert status.vault_path == bridge_config["vault_path"]

        # Stop monitoring
        monitoring_stopped = await bridge.stop_sync_monitoring()
        assert monitoring_stopped

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_under_load(self, bridge_config, temp_vault_dir):
        """Test bridge performance under concurrent load."""
        import time

        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(
            {**bridge_config, "vault_path": str(temp_vault_dir)},
        )

        # Create multiple concurrent file operations
        start_time = time.time()

        tasks = []
        for i in range(10):
            note_data = {
                "title": f"Performance Test {i}",
                "content": f"Performance test content {i}",
                "type": "note",
            }
            tasks.append(bridge.create_enhanced_note(note_data))

        results = await asyncio.gather(*tasks)
        execution_time = time.time() - start_time

        assert len(results) == 10
        assert all(result.success for result in results)
        assert execution_time < 5.0  # Should complete in under 5 seconds

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, bridge_config):
        """Test error handling and recovery mechanisms."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(bridge_config)

        # Test invalid vault path
        with pytest.raises(ValueError, match="Invalid vault path"):
            await bridge.validate_vault_path("/nonexistent/path")

        # Test MCP server connection failure
        bridge.mcp_client = None
        result = await bridge.handle_mcp_connection_error()
        assert result.fallback_mode

    def test_configuration_validation(self):
        """Test configuration validation and error handling."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        # Test missing required configuration
        with pytest.raises(ValueError, match="vault_path is required"):
            EnhancedObsidianBridge({})

        # Test invalid configuration values
        invalid_config = {"vault_path": "", "bridge_port": "invalid_port"}

        with pytest.raises(ValueError):
            EnhancedObsidianBridge(invalid_config)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_integration_workflow(
        self,
        bridge_config,
        temp_vault_dir,
        mock_mcp_server,
    ):
        """Test complete integration workflow: create -> sync -> search -> analyze."""
        from src.bridge.enhanced_obsidian_bridge import EnhancedObsidianBridge

        bridge = EnhancedObsidianBridge(
            {**bridge_config, "vault_path": str(temp_vault_dir)},
        )
        bridge.mcp_client = mock_mcp_server

        # Step 1: Create note with auto-tagging
        note_data = {
            "title": "Integration Test Note",
            "content": "This note tests the complete integration workflow.",
            "type": "note",
            "auto_tag": True,
        }

        create_result = await bridge.create_enhanced_note(note_data)
        assert create_result.success

        # Step 2: Auto-sync to MCP server
        sync_result = await bridge.sync_note_to_mcp(create_result.filepath)
        assert sync_result.success

        # Step 3: Search should include the new note
        search_result = await bridge.perform_enhanced_search(
            {"query": "integration workflow", "sources": ["vault"], "semantic": True},
        )
        assert search_result["results"] is not None

        # Step 4: Knowledge graph should be updated
        graph_status = await bridge.get_knowledge_graph_status()
        assert graph_status.enabled
