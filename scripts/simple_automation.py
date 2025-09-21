#!/usr/bin/env python3
"""
PAKE+ Simple Automation System
Processes all markdown files in vault and monitors for changes
"""

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import frontmatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SimpleAutomation:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.processed_files = {}  # file -> hash mapping
        self.state_file = Path("data/simple_automation_state.json")

        # Create directories
        os.makedirs("data", exist_ok=True)
        os.makedirs("data/vectors", exist_ok=True)
        os.makedirs("logs", exist_ok=True)

        self.load_state()

    def load_state(self):
        """Load processed files state"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    self.processed_files = json.load(f)
                logger.info(f"Loaded {len(self.processed_files)} processed files")
            except Exception as e:
                logger.error(f"Error loading state: {e}")

    def save_state(self):
        """Save processed files state"""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.processed_files, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def get_file_hash(self, file_path: Path) -> str:
        """Get hash of file content"""
        try:
            with open(file_path, encoding="utf-8") as f:
                return hashlib.sha256(f.read().encode()).hexdigest()
        except Exception:
            return ""

    def calculate_confidence(self, content: str, metadata: dict) -> float:
        """Calculate confidence score"""
        score = 0.0

        # Content length (0.2)
        length = len(content)
        if length > 1000:
            score += 0.2
        elif length > 500:
            score += 0.15
        elif length > 100:
            score += 0.1

        # Structure (0.2)
        if "# " in content:
            score += 0.1
        if content.count("\n\n") > 2:
            score += 0.05
        if any(marker in content for marker in ["- ", "* ", "1. "]):
            score += 0.05

        # Technical content (0.15)
        if "```" in content:
            score += 0.1
        if "[" in content and "](" in content:
            score += 0.05

        # Tags (0.1)
        tags = metadata.get("tags", [])
        if len(tags) > 3:
            score += 0.1
        elif len(tags) > 1:
            score += 0.05

        # Default local source (0.15)
        score += 0.15

        # Base quality (0.1)
        score += 0.1

        return min(score, 1.0)

    def create_vector_embedding(self, text: str) -> list:
        """Create simple vector embedding"""
        # Basic features
        features = [
            min(len(text) / 10000, 1.0),  # length
            min(len(text.split()) / 1000, 1.0),  # words
            min(text.count("# ") / 10, 1.0),  # headers
            1.0 if "```" in text else 0.0,  # code
            1.0 if "[" in text else 0.0,  # links
            sum(1 for c in text if c.isupper()) / max(len(text), 1),  # uppercase ratio
        ]

        # Hash-based features to fill 128 dimensions
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        hash_features = [int(text_hash[i : i + 2], 16) / 255.0 for i in range(0, 30, 2)]

        # Combine and pad to 128
        embedding = features + hash_features
        while len(embedding) < 128:
            embedding.append(0.0)

        return embedding[:128]

    def generate_ai_summary(self, content: str) -> str:
        """Generate simple AI summary"""
        lines = content.split("\n")

        # Extract title
        title = ""
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Count features
        word_count = len(content.split())
        has_code = "```" in content
        has_links = "[" in content and "](" in content
        has_lists = any(line.strip().startswith(("- ", "* ", "1. ")) for line in lines)

        # Build summary
        parts = []
        if title:
            parts.append(f"Topic: {title}")
        parts.append(f"~{word_count} words")

        if has_code:
            parts.append("contains code")
        if has_links:
            parts.append("has links")
        if has_lists:
            parts.append("includes lists")

        return " | ".join(parts)

    def process_file(self, file_path: Path) -> bool:
        """Process a single markdown file"""
        try:
            logger.info(f"Processing: {file_path}")

            # Read file
            with open(file_path, encoding="utf-8") as f:
                file_content = f.read()

            # Parse frontmatter
            try:
                post = frontmatter.loads(file_content)
                content = post.content
                metadata = post.metadata.copy()
            except BaseException:
                # No frontmatter, create new
                content = file_content
                metadata = {}

            # Add/update automated fields
            pake_id = metadata.get("pake_id", str(uuid.uuid4()))
            confidence_score = self.calculate_confidence(content, metadata)
            ai_summary = self.generate_ai_summary(content)
            embedding = self.create_vector_embedding(content)

            # Update metadata
            metadata.update(
                {
                    "pake_id": pake_id,
                    "confidence_score": confidence_score,
                    "ai_summary": ai_summary,
                    "last_processed": datetime.now().isoformat(),
                    "vector_dimensions": len(embedding),
                    "automated_processing": True,
                },
            )

            # Create updated file content
            updated_post = frontmatter.Post(content, **metadata)
            updated_content = frontmatter.dumps(updated_post)

            # Write back to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            # Save vector embedding
            vector_file = Path(f"data/vectors/{pake_id}.json")
            with open(vector_file, "w") as f:
                json.dump(
                    {
                        "pake_id": pake_id,
                        "embedding": embedding,
                        "created_at": datetime.now().isoformat(),
                        "file_path": str(file_path),
                    },
                    f,
                )

            # Update processed hash
            new_hash = self.get_file_hash(file_path)
            self.processed_files[str(file_path)] = new_hash

            logger.info(f"[SUCCESS] {file_path}: confidence={confidence_score:.2f}")
            return True

        except Exception as e:
            logger.error(f"[ERROR] Processing {file_path}: {e}")
            return False

    def scan_and_process(self):
        """Scan vault and process all changed files"""
        processed = 0
        skipped = 0

        for file_path in self.vault_path.rglob("*.md"):
            # Skip template and system files
            if any(part.startswith(("_", ".")) for part in file_path.parts):
                continue

            # Check if file needs processing
            current_hash = self.get_file_hash(file_path)
            stored_hash = self.processed_files.get(str(file_path))

            if current_hash and current_hash != stored_hash:
                if self.process_file(file_path):
                    processed += 1
                else:
                    logger.error(f"Failed to process: {file_path}")
            else:
                skipped += 1

        self.save_state()
        logger.info(f"Scan complete: {processed} processed, {skipped} skipped")
        return processed

    def run_continuous(self, interval: int = 5):
        """Run continuous monitoring"""
        logger.info("Starting PAKE+ Simple Automation System")
        logger.info(f"Vault: {self.vault_path}")
        logger.info(f"Scan interval: {interval} seconds")
        logger.info("Monitoring for changes...")

        try:
            while True:
                processed = self.scan_and_process()
                if processed > 0:
                    logger.info(f"Processed {processed} files")
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Stopping automation...")

    def run_once(self):
        """Run one-time processing of all files"""
        logger.info("Running one-time vault processing...")
        processed = self.scan_and_process()
        logger.info(f"One-time processing complete: {processed} files processed")


if __name__ == "__main__":
    import sys

    vault_path = os.environ.get("VAULT_PATH", "vault")
    automation = SimpleAutomation(vault_path)

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        automation.run_once()
    else:
        automation.run_continuous()
