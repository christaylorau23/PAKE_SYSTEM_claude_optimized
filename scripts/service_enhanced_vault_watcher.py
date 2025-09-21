#!/usr/bin/env python3
"""
PAKE+ Service-Enhanced Automated Vault Watcher
Enhanced version designed for Windows Service operation with error recovery
"""

import asyncio
import gc
import hashlib
import json
import logging
import os
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import frontmatter
import psutil
from watchdog.events import FileSystemEventHandler

# Configure service-aware logging


def setup_service_logging():
    """Setup logging configuration for service operation"""
    log_dir = Path("D:/Projects/PAKE_SYSTEM/logs")
    log_dir.mkdir(exist_ok=True)

    # Create both service and vault logs
    handlers = [
        logging.FileHandler(log_dir / "vault_automation.log"),
        logging.FileHandler(log_dir / "service_vault.log"),
    ]

    # Add console handler if not running as service
    if not os.environ.get("RUNNING_AS_SERVICE"):
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    return logging.getLogger(__name__)


logger = setup_service_logging()


@dataclass
class ProcessingResult:
    """Result of automated processing"""

    pake_id: str
    confidence_score: float
    vector_embedded: bool
    knowledge_graph_updated: bool
    ai_summary: str
    processing_time: float
    error: str = None


@dataclass
class ServiceHealth:
    """Service health status tracking"""

    last_activity: datetime
    files_processed_today: int
    queue_size: int
    error_count: int
    memory_usage_mb: float
    uptime_hours: float
    status: str = "healthy"


class EnhancedConfidenceEngine:
    """Enhanced confidence scoring with error recovery"""

    def __init__(self):
        self.fallback_scores = {
            "minimal": 0.3,
            "basic": 0.5,
            "good": 0.7,
            "excellent": 0.9,
        }

    def calculate_confidence(self, content: str, metadata: dict) -> float:
        """Calculate confidence score with error handling"""
        try:
            score = 0.0

            # Length factor (robust)
            word_count = len(content.split())
            if word_count > 500:
                score += 0.25
            elif word_count > 200:
                score += 0.15
            elif word_count > 50:
                score += 0.10

            # Structure factor (safe checking)
            try:
                lines = content.split("\n")
                has_headers = any(line.strip().startswith("#") for line in lines)
                has_lists = any(
                    line.strip().startswith(("-", "*", "1.")) for line in lines
                )
                has_code = "```" in content or "`" in content

                structure_score = 0
                if has_headers:
                    structure_score += 0.1
                if has_lists:
                    structure_score += 0.05
                if has_code:
                    structure_score += 0.05
                score += min(structure_score, 0.2)

            except Exception:
                score += 0.1  # Default structure bonus

            # Metadata quality (safe)
            try:
                if metadata.get("tags"):
                    score += min(len(metadata["tags"]) * 0.02, 0.1)
                if metadata.get("source_uri"):
                    score += 0.05
                if metadata.get("verification_status") == "verified":
                    score += 0.1
            except Exception:
                score += 0.05  # Default metadata bonus

            # Content quality indicators (robust)
            try:
                quality_indicators = [
                    "analysis",
                    "conclusion",
                    "summary",
                    "implementation",
                    "research",
                    "study",
                ]
                found_indicators = sum(
                    1
                    for indicator in quality_indicators
                    if indicator.lower() in content.lower()
                )
                score += min(found_indicators * 0.03, 0.15)
            except Exception:
                pass

            # Ensure score is within bounds
            return max(0.1, min(1.0, score))

        except Exception as e:
            logger.error(f"Confidence calculation error: {e}")
            return self.fallback_scores["basic"]


class RobustVectorEmbedding:
    """Robust vector embedding with fallback"""

    def __init__(self, dimensions=128):
        self.dimensions = dimensions

    def create_embedding(self, content: str) -> list:
        """Create vector embedding with error handling"""
        try:
            # Simple hash-based embedding (production would use proper embeddings)
            words = content.lower().split()

            # Create vocabulary hash
            vocab_hash = {}
            for i, word in enumerate(
                set(words[:1000]),
            ):  # Limit to prevent memory issues
                vocab_hash[word] = hash(word) % self.dimensions

            # Create embedding vector
            embedding = [0.0] * self.dimensions
            for word in words:
                if word in vocab_hash:
                    embedding[vocab_hash[word]] += 1.0

            # Normalize
            magnitude = sum(x * x for x in embedding) ** 0.5
            if magnitude > 0:
                embedding = [x / magnitude for x in embedding]

            return embedding

        except Exception as e:
            logger.error(f"Vector embedding error: {e}")
            # Return random normalized vector as fallback
            import random

            embedding = [random.uniform(-1, 1) for _ in range(self.dimensions)]
            magnitude = sum(x * x for x in embedding) ** 0.5
            return (
                [x / magnitude for x in embedding]
                if magnitude > 0
                else [0.0] * self.dimensions
            )


class ServiceEnhancedVaultWatcher(FileSystemEventHandler):
    """Enhanced vault watcher designed for Windows Service operation"""

    def __init__(self, vault_path: str, api_bridge_url: str = None):
        super().__init__()
        self.vault_path = Path(vault_path)
        self.api_bridge_url = api_bridge_url
        self.processing_queue = asyncio.Queue()
        self.processed_files = {}
        self.service_start_time = datetime.now()

        # Enhanced components
        self.confidence_engine = EnhancedConfidenceEngine()
        self.vector_engine = RobustVectorEmbedding()

        # Service health tracking
        self.health = ServiceHealth(
            last_activity=datetime.now(),
            files_processed_today=0,
            queue_size=0,
            error_count=0,
            memory_usage_mb=0.0,
            uptime_hours=0.0,
        )

        # Error recovery
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10
        self.error_recovery_delay = 5  # seconds

        # Load previous state
        self.load_processing_state()
        self.load_knowledge_graph()

        # Ensure data directories exist
        self.setup_data_directories()

        logger.info(f"Enhanced vault watcher initialized for service: {vault_path}")

    def setup_data_directories(self):
        """Ensure all required directories exist"""
        dirs = [
            Path("D:/Projects/PAKE_SYSTEM/data"),
            Path("D:/Projects/PAKE_SYSTEM/data/vectors"),
            Path("D:/Projects/PAKE_SYSTEM/logs"),
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    def load_processing_state(self):
        """Load processing state with error handling"""
        try:
            state_file = Path("D:/Projects/PAKE_SYSTEM/data/processing_state.json")
            if state_file.exists():
                with open(state_file) as f:
                    self.processed_files = json.load(f)
                logger.info(
                    f"Loaded processing state: {len(self.processed_files)} files",
                )
        except Exception as e:
            logger.error(f"Error loading processing state: {e}")
            self.processed_files = {}

    def save_processing_state(self):
        """Save processing state with error handling"""
        try:
            state_file = Path("D:/Projects/PAKE_SYSTEM/data/processing_state.json")
            with open(state_file, "w") as f:
                json.dump(self.processed_files, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processing state: {e}")

    def load_knowledge_graph(self):
        """Load knowledge graph with error handling"""
        try:
            kg_file = Path("D:/Projects/PAKE_SYSTEM/data/knowledge_graph.json")
            if kg_file.exists():
                with open(kg_file) as f:
                    self.knowledge_graph = json.load(f)
                logger.info(
                    f"Loaded knowledge graph: {len(self.knowledge_graph)} entries",
                )
            else:
                self.knowledge_graph = {}
        except Exception as e:
            logger.error(f"Error loading knowledge graph: {e}")
            self.knowledge_graph = {}

    def update_health_status(self):
        """Update service health metrics"""
        try:
            process = psutil.Process()
            self.health.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            self.health.uptime_hours = (
                datetime.now() - self.service_start_time
            ).total_seconds() / 3600
            self.health.queue_size = self.processing_queue.qsize()

            # Reset daily counter if new day
            if datetime.now().date() > self.health.last_activity.date():
                self.health.files_processed_today = 0

            self.health.last_activity = datetime.now()

        except Exception as e:
            logger.error(f"Error updating health status: {e}")

    def get_file_hash(self, file_path: Path) -> str | None:
        """Get file hash with error handling"""
        try:
            if not file_path.exists():
                return None
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error getting file hash for {file_path}: {e}")
            return None

    async def run_monitoring_cycle(self):
        """Run one cycle of monitoring - called by service"""
        try:
            self.update_health_status()

            # Process queue if not empty
            if not self.processing_queue.empty():
                await self.process_queue_batch()

            # Periodic health tasks
            if self.health.last_activity.minute % 10 == 0:  # Every 10 minutes
                await self.perform_health_maintenance()

            # Reset error counter on successful cycle
            self.consecutive_errors = 0

        except Exception as e:
            self.consecutive_errors += 1
            logger.error(f"Monitoring cycle error ({self.consecutive_errors}): {e}")

            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.critical(
                    "Maximum consecutive errors reached, entering recovery mode",
                )
                await asyncio.sleep(self.error_recovery_delay * self.consecutive_errors)

    async def process_queue_batch(self):
        """Process a batch of files from the queue"""
        batch_size = min(3, self.processing_queue.qsize())  # Process up to 3 files

        for _ in range(batch_size):
            try:
                if self.processing_queue.empty():
                    break

                file_path = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0,
                )

                result = await self.process_file(file_path)

                if result and not result.error:
                    self.health.files_processed_today += 1
                    logger.info(f"Successfully processed: {file_path.name}")
                else:
                    logger.warning(f"Processing failed: {file_path.name}")

                self.processing_queue.task_done()

            except TimeoutError:
                logger.warning("Queue processing timeout")
                break
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                break

    async def perform_health_maintenance(self):
        """Perform periodic health maintenance"""
        try:
            # Memory cleanup
            gc.collect()

            # Save state
            self.save_processing_state()

            # Check disk space
            vault_disk = psutil.disk_usage(str(self.vault_path))
            if vault_disk.free < 1024 * 1024 * 100:  # Less than 100MB
                logger.warning(
                    f"Low disk space: {vault_disk.free / 1024 / 1024:.1f}MB free",
                )

            # Update health status
            self.health.status = (
                "healthy" if self.consecutive_errors < 3 else "degraded"
            )

            logger.debug(
                f"Health maintenance: {self.health.memory_usage_mb:.1f}MB, "
                f"{self.health.files_processed_today} files today",
            )

        except Exception as e:
            logger.error(f"Health maintenance error: {e}")

    # ... [include rest of the methods from original vault watcher with enhanced error handling]

    async def process_file(self, file_path: Path) -> ProcessingResult:
        """Process a single file with enhanced error recovery"""
        start_time = time.time()

        try:
            # Validate file exists and is accessible
            if not file_path.exists():
                return ProcessingResult(
                    "",
                    0.0,
                    False,
                    False,
                    "File not found",
                    0.0,
                    "File not found",
                )

            # Read and parse file with encoding fallback
            try:
                with open(file_path, encoding="utf-8") as f:
                    file_content = f.read()
            except UnicodeDecodeError:
                with open(file_path, encoding="latin-1") as f:
                    file_content = f.read()

            parsed = frontmatter.loads(file_content)
            content = parsed.content
            metadata = parsed.metadata

            # Generate PAKE ID if missing
            pake_id = metadata.get("pake_id", str(uuid.uuid4()))

            # Calculate confidence score with fallback
            confidence_score = self.confidence_engine.calculate_confidence(
                content,
                metadata,
            )

            # Create vector embedding with error handling
            try:
                embedding = self.vector_engine.create_embedding(content)
            except Exception as e:
                logger.warning(f"Vector embedding failed, using fallback: {e}")
                embedding = [0.0] * 128  # Fallback empty vector

            # Generate simple AI summary
            ai_summary = self.generate_simple_summary(content)

            # Update metadata
            metadata.update(
                {
                    "pake_id": pake_id,
                    "confidence_score": confidence_score,
                    "last_processed": datetime.now().isoformat(),
                    "ai_summary": ai_summary,
                    "vector_dimensions": len(embedding),
                    "automated_processing": True,
                    "service_processed": True,
                },
            )

            # Save updated file with backup
            try:
                # Create backup
                backup_path = file_path.with_suffix(".md.backup")
                backup_path.write_text(file_content, encoding="utf-8")

                # Update original
                post = frontmatter.Post(content, **metadata)
                updated_content = frontmatter.dumps(post)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)

                # Remove backup on success
                if backup_path.exists():
                    backup_path.unlink()

            except Exception as e:
                logger.error(f"File update failed: {e}")
                # Restore from backup if it exists
                backup_path = file_path.with_suffix(".md.backup")
                if backup_path.exists():
                    backup_path.rename(file_path)
                raise

            # Update knowledge graph and save vector
            self.update_knowledge_graph(pake_id, content, metadata)
            self.save_vector_embedding(pake_id, embedding)

            # Update processed files hash
            new_hash = self.get_file_hash(file_path)
            if new_hash:
                self.processed_files[str(file_path)] = new_hash

            processing_time = time.time() - start_time

            return ProcessingResult(
                pake_id=pake_id,
                confidence_score=confidence_score,
                vector_embedded=True,
                knowledge_graph_updated=True,
                ai_summary=ai_summary,
                processing_time=processing_time,
            )

        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            logger.error(f"File processing error for {file_path}: {error_msg}")
            logger.error(traceback.format_exc())

            return ProcessingResult(
                pake_id="",
                confidence_score=0.0,
                vector_embedded=False,
                knowledge_graph_updated=False,
                ai_summary="Processing failed",
                processing_time=time.time() - start_time,
                error=error_msg,
            )

    def generate_simple_summary(self, content: str) -> str:
        """Generate simple summary with error handling"""
        try:
            sentences = content.replace("\n", " ").split(".")
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

            if len(sentences) >= 3:
                return ". ".join(sentences[:3]) + "."
            if len(sentences) >= 1:
                return sentences[0] + "."
            words = content.split()[:50]
            return " ".join(words) + ("..." if len(content.split()) > 50 else "")

        except Exception:
            return "Content summary unavailable."

    def update_knowledge_graph(self, pake_id: str, content: str, metadata: dict):
        """Update knowledge graph with error handling"""
        try:
            self.knowledge_graph[pake_id] = {
                "title": metadata.get("title", "Untitled"),
                "tags": metadata.get("tags", []),
                "connections": metadata.get("connections", []),
                "last_updated": datetime.now().isoformat(),
                "content_preview": content[:200]
                + ("..." if len(content) > 200 else ""),
                "confidence_score": metadata.get("confidence_score", 0.0),
            }

            # Save knowledge graph periodically
            if len(self.knowledge_graph) % 10 == 0:  # Every 10 updates
                kg_file = Path("D:/Projects/PAKE_SYSTEM/data/knowledge_graph.json")
                with open(kg_file, "w") as f:
                    json.dump(self.knowledge_graph, f, indent=2)

        except Exception as e:
            logger.error(f"Knowledge graph update error: {e}")

    def save_vector_embedding(self, pake_id: str, embedding: list):
        """Save vector embedding with error handling"""
        try:
            vector_file = Path(f"D:/Projects/PAKE_SYSTEM/data/vectors/{pake_id}.json")
            vector_data = {
                "pake_id": pake_id,
                "vector": embedding,
                "dimensions": len(embedding),
                "created": datetime.now().isoformat(),
            }

            with open(vector_file, "w") as f:
                json.dump(vector_data, f)

        except Exception as e:
            logger.error(f"Vector save error for {pake_id}: {e}")

    def on_created(self, event):
        """Handle file creation with error recovery"""
        try:
            if event.is_directory or not event.src_path.endswith(".md"):
                return

            file_path = Path(event.src_path)

            # Skip system files
            if any(part.startswith(("_", ".")) for part in file_path.parts):
                return

            logger.info(f"File created: {file_path}")
            # Queue for processing (will be handled in monitoring cycle)
            asyncio.create_task(self.processing_queue.put(file_path))

        except Exception as e:
            logger.error(f"File creation handler error: {e}")

    def on_modified(self, event):
        """Handle file modification with error recovery"""
        try:
            if event.is_directory or not event.src_path.endswith(".md"):
                return

            file_path = Path(event.src_path)

            # Skip system files
            if any(part.startswith(("_", ".")) for part in file_path.parts):
                return

            # Check if file actually changed
            current_hash = self.get_file_hash(file_path)
            stored_hash = self.processed_files.get(str(file_path))

            if current_hash and current_hash != stored_hash:
                logger.info(f"File modified: {file_path}")
                asyncio.create_task(self.processing_queue.put(file_path))

        except Exception as e:
            logger.error(f"File modification handler error: {e}")


# Alias for backward compatibility
VaultWatcher = ServiceEnhancedVaultWatcher
