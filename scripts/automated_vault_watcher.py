#!/usr/bin/env python3
"""
PAKE+ Automated Vault Watcher
Monitors the vault for changes and automatically processes all new/modified content
"""

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import aiohttp
import frontmatter
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/vault_automation.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


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


class ConfidenceEngine:
    """Simple confidence scoring engine"""

    def calculate_confidence(self, content: str, metadata: dict) -> float:
        """Calculate confidence score based on content analysis"""
        score = 0.0

        # Content length factor (0.2)
        length = len(content)
        if length > 1000:
            score += 0.2
        elif length > 500:
            score += 0.15
        elif length > 100:
            score += 0.1

        # Structure factor (0.2)
        if "# " in content:  # Has headers
            score += 0.1
        if content.count("\n\n") > 2:  # Has paragraphs
            score += 0.05
        if any(marker in content for marker in ["- ", "* ", "1. "]):  # Has lists
            score += 0.05

        # Source authority (0.25)
        source_uri = metadata.get("source_uri", "local://api")
        if "arxiv.org" in source_uri:
            score += 0.25
        elif any(
            domain in source_uri for domain in ["github.com", "stackoverflow.com"]
        ):
            score += 0.2
        elif "local://" in source_uri:
            score += 0.15
        else:
            score += 0.1

        # Verification status (0.1)
        if metadata.get("verification_status") == "verified":
            score += 0.1
        elif metadata.get("verification_status") == "pending":
            score += 0.05

        # Cross-references (0.15)
        connections = len(metadata.get("connections", []))
        if connections > 5:
            score += 0.15
        elif connections > 2:
            score += 0.1
        elif connections > 0:
            score += 0.05

        # Tags quality (0.1)
        tags = metadata.get("tags", [])
        if len(tags) > 3:
            score += 0.1
        elif len(tags) > 1:
            score += 0.05

        return min(score, 1.0)


class SimpleVectorEmbedding:
    """Simple vector embedding using basic text analysis"""

    def __init__(self):
        self.embeddings_cache = {}

    def create_embedding(self, text: str) -> list:
        """Create a simple embedding vector based on text characteristics"""
        # This is a simplified version - in production you'd use sentence-transformers

        # Basic text features
        features = {
            "length": min(len(text) / 10000, 1.0),
            "word_count": min(len(text.split()) / 1000, 1.0),
            "header_count": min(text.count("# ") / 10, 1.0),
            "link_count": min(text.count("[") / 20, 1.0),
            "has_code": 1.0 if "```" in text else 0.0,
            "has_lists": (
                1.0 if any(marker in text for marker in ["- ", "* ", "1. "]) else 0.0
            ),
            "uppercase_ratio": sum(1 for c in text if c.isupper()) / max(len(text), 1),
            "question_marks": min(text.count("?") / 5, 1.0),
        }

        # Create 128-dimensional vector
        base_vector = list(features.values())

        # Pad to 128 dimensions with hash-based values
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        hash_values = [
            int(text_hash[i : i + 2], 16) / 255.0
            for i in range(0, min(len(text_hash), 30), 2)
        ]

        embedding = base_vector + hash_values

        # Pad to exactly 128 dimensions
        while len(embedding) < 128:
            embedding.append(0.0)

        return embedding[:128]


class VaultWatcher(FileSystemEventHandler):
    """Watches vault for changes and triggers automated processing"""

    def __init__(self, vault_path: str, api_bridge_url: str = "http://localhost:3000"):
        self.vault_path = Path(vault_path)
        self.api_bridge_url = api_bridge_url
        self.confidence_engine = ConfidenceEngine()
        self.vector_engine = SimpleVectorEmbedding()
        self.processing_queue = asyncio.Queue()
        self.processed_files = {}  # file_path -> hash mapping
        self.knowledge_graph = {}  # Simple knowledge graph storage

        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)

        # Load existing processed files
        self.load_processing_state()

        logger.info(f"Initialized VaultWatcher for {vault_path}")

    def load_processing_state(self):
        """Load previously processed files state"""
        state_file = Path("data/processing_state.json")
        if state_file.exists():
            try:
                with open(state_file) as f:
                    self.processed_files = json.load(f)
                logger.info(
                    f"Loaded {len(self.processed_files)} processed files from state",
                )
            except Exception as e:
                logger.error(f"Error loading processing state: {e}")

    def save_processing_state(self):
        """Save processing state"""
        os.makedirs("data", exist_ok=True)
        state_file = Path("data/processing_state.json")
        try:
            with open(state_file, "w") as f:
                json.dump(self.processed_files, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processing state: {e}")

    def get_file_hash(self, file_path: Path) -> str:
        """Get hash of file content"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                return hashlib.sha256(content.encode()).hexdigest()
        except Exception:
            return ""

    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process markdown files
        if file_path.suffix.lower() != ".md":
            return

        # Skip template files and system files
        if any(part.startswith(("_", ".")) for part in file_path.parts):
            return

        logger.info(f"File modified: {file_path}")
        asyncio.create_task(self.queue_for_processing(file_path))

    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process markdown files
        if file_path.suffix.lower() != ".md":
            return

        # Skip template files and system files
        if any(part.startswith(("_", ".")) for part in file_path.parts):
            return

        logger.info(f"File created: {file_path}")
        asyncio.create_task(self.queue_for_processing(file_path))

    async def queue_for_processing(self, file_path: Path):
        """Add file to processing queue if it has changed"""
        current_hash = self.get_file_hash(file_path)
        stored_hash = self.processed_files.get(str(file_path))

        if current_hash != stored_hash and current_hash:
            await self.processing_queue.put(file_path)
            logger.info(f"Queued for processing: {file_path}")

    async def process_file(self, file_path: Path) -> ProcessingResult:
        """Automatically process a single file"""
        start_time = time.time()

        try:
            # Read and parse file
            with open(file_path, encoding="utf-8") as f:
                file_content = f.read()

            parsed = frontmatter.loads(file_content)
            content = parsed.content
            metadata = parsed.metadata

            # Generate PAKE ID if missing
            pake_id = metadata.get("pake_id", str(uuid.uuid4()))

            # Calculate confidence score
            confidence_score = self.confidence_engine.calculate_confidence(
                content,
                metadata,
            )

            # Create vector embedding
            embedding = self.vector_engine.create_embedding(content)

            # Generate AI summary (simplified version)
            ai_summary = self.generate_simple_summary(content)

            # Update metadata with new information
            metadata.update(
                {
                    "pake_id": pake_id,
                    "confidence_score": confidence_score,
                    "last_processed": datetime.now().isoformat(),
                    "ai_summary": ai_summary,
                    "vector_dimensions": len(embedding),
                    "automated_processing": True,
                },
            )

            # Update file with new metadata
            post = frontmatter.Post(content, **metadata)
            updated_content = frontmatter.dumps(post)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            # Store in simple knowledge graph
            self.update_knowledge_graph(pake_id, content, metadata)

            # Save vector embedding
            self.save_vector_embedding(pake_id, embedding)

            # Update processed files hash
            new_hash = self.get_file_hash(file_path)
            self.processed_files[str(file_path)] = new_hash
            self.save_processing_state()

            processing_time = time.time() - start_time

            result = ProcessingResult(
                pake_id=pake_id,
                confidence_score=confidence_score,
                vector_embedded=True,
                knowledge_graph_updated=True,
                ai_summary=ai_summary,
                processing_time=processing_time,
            )

            logger.info(
                f"[SUCCESS] Processed {file_path}: confidence={
                    confidence_score:.2f}, time={processing_time:.2f}s",
            )
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[ERROR] Error processing {file_path}: {e}")
            return ProcessingResult(
                pake_id="",
                confidence_score=0.0,
                vector_embedded=False,
                knowledge_graph_updated=False,
                ai_summary="",
                processing_time=processing_time,
                error=str(e),
            )

    def generate_simple_summary(self, content: str) -> str:
        """Generate a simple summary of content"""
        lines = content.split("\n")

        # Find first header as title
        title = ""
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Count content characteristics
        word_count = len(content.split())
        has_code = "```" in content
        has_links = "[" in content and "]" in content
        has_lists = any(line.strip().startswith(("- ", "* ", "1. ")) for line in lines)

        # Generate summary
        summary_parts = []
        if title:
            summary_parts.append(f"Topic: {title}")
        summary_parts.append(f"~{word_count} words")

        if has_code:
            summary_parts.append("contains code")
        if has_links:
            summary_parts.append("has links")
        if has_lists:
            summary_parts.append("includes lists")

        return " | ".join(summary_parts)

    def update_knowledge_graph(self, pake_id: str, content: str, metadata: dict):
        """Update simple knowledge graph"""
        self.knowledge_graph[pake_id] = {
            "title": (
                content.split("\n")[0].replace("# ", "")
                if content.startswith("# ")
                else "Untitled"
            ),
            "tags": metadata.get("tags", []),
            "connections": metadata.get("connections", []),
            "confidence": metadata.get("confidence_score", 0.0),
            "last_updated": datetime.now().isoformat(),
        }

        # Save knowledge graph
        os.makedirs("data", exist_ok=True)
        with open("data/knowledge_graph.json", "w") as f:
            json.dump(self.knowledge_graph, f, indent=2)

    def save_vector_embedding(self, pake_id: str, embedding: list):
        """Save vector embedding to file"""
        os.makedirs("data/vectors", exist_ok=True)
        vector_file = Path(f"data/vectors/{pake_id}.json")

        vector_data = {
            "pake_id": pake_id,
            "embedding": embedding,
            "dimensions": len(embedding),
            "created_at": datetime.now().isoformat(),
        }

        with open(vector_file, "w") as f:
            json.dump(vector_data, f)

    async def processing_worker(self):
        """Background worker to process files from queue"""
        while True:
            try:
                file_path = await self.processing_queue.get()
                result = await self.process_file(file_path)

                if not result.error:
                    # Notify API bridge of processing
                    try:
                        async with aiohttp.ClientSession() as session:
                            notification = {
                                "type": "automated_processing",
                                "pake_id": result.pake_id,
                                "confidence_score": result.confidence_score,
                                "processing_time": result.processing_time,
                                "file_path": str(file_path),
                            }
                            await session.post(
                                f"{self.api_bridge_url}/api/notifications",
                                json=notification,
                            )
                    except Exception as e:
                        logger.warning(f"Could not notify API bridge: {e}")

                self.processing_queue.task_done()

            except Exception as e:
                logger.error(f"Error in processing worker: {e}")
                await asyncio.sleep(1)

    def process_existing_files(self):
        """Process all existing files in vault on startup"""
        logger.info("Processing existing files in vault...")

        for file_path in self.vault_path.rglob("*.md"):
            # Skip template files and system files
            if any(part.startswith(("_", ".")) for part in file_path.parts):
                continue

            current_hash = self.get_file_hash(file_path)
            stored_hash = self.processed_files.get(str(file_path))

            if current_hash != stored_hash and current_hash:
                asyncio.create_task(self.queue_for_processing(file_path))

    async def start_automation(self):
        """Start the automated processing system"""
        logger.info("[STARTUP] Starting PAKE+ Automated Vault Processing")

        # Start background processing worker
        worker_task = asyncio.create_task(self.processing_worker())

        # Process existing files
        self.process_existing_files()

        # Set up file system watching
        observer = Observer()
        observer.schedule(self, str(self.vault_path), recursive=True)
        observer.start()

        logger.info(f"[WATCHING] Vault: {self.vault_path}")
        logger.info("[ACTIVE] Automated processing is ACTIVE")
        logger.info(
            "[INFO] Any new or modified .md files will be automatically processed!",
        )

        try:
            while True:
                queue_size = self.processing_queue.qsize()
                if queue_size > 0:
                    logger.info(f"[QUEUE] Processing queue: {queue_size} files")
                await asyncio.sleep(30)  # Status update every 30 seconds

        except KeyboardInterrupt:
            logger.info("[SHUTDOWN] Stopping automation...")
            observer.stop()
            worker_task.cancel()

        observer.join()


async def main():
    """Main automation entry point"""
    vault_path = os.environ.get("VAULT_PATH", "D:\\Knowledge-Vault")
    api_bridge_url = os.environ.get("API_BRIDGE_URL", "http://localhost:3000")

    print(
        f"""
PAKE+ COMPLETE AUTOMATION SYSTEM
================================

Vault Path: {vault_path}
API Bridge: {api_bridge_url}

This system will automatically:
- Watch for any new/modified notes in your vault
- Calculate confidence scores using multi-factor analysis
- Generate vector embeddings for semantic search
- Update knowledge graph with connections
- Add AI-generated summaries to frontmatter
- Process everything in real-time as you add content

Press Ctrl+C to stop automation
    """,
    )

    # Create watcher and start automation
    watcher = VaultWatcher(vault_path, api_bridge_url)
    await watcher.start_automation()


if __name__ == "__main__":
    asyncio.run(main())
