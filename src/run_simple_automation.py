#!/usr/bin/env python3
"""Simple PAKE Automation Test
Demonstrates the core automation without complex dependencies
"""

import json
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class SimpleAutomationHandler(FileSystemEventHandler):
    """Simple file handler for testing automation"""

    def __init__(self, vault_path):
        self.vault_path = Path(vault_path)
        self.processed = set()

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix == ".md":
            print(f"🔍 DETECTED: {file_path.name}")
            self.process_file(file_path)

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix == ".md" and str(file_path) not in self.processed:
            print(f"📝 MODIFIED: {file_path.name}")
            self.process_file(file_path)

    def process_file(self, file_path):
        """Simple processing demonstration"""
        try:
            print(f"⚙️  PROCESSING: {file_path.name}")

            # Read file
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Simple analysis
            word_count = len(content.split())
            line_count = len(content.splitlines())
            has_frontmatter = content.startswith("---")
            has_headers = "#" in content
            has_code = "```" in content

            # Calculate simple confidence
            confidence = 0.3  # Base score
            if word_count > 100:
                confidence += 0.2
            if has_headers:
                confidence += 0.2
            if has_code:
                confidence += 0.1
            if has_frontmatter:
                confidence += 0.2
            confidence = min(confidence, 1.0)

            # Create processing result
            result = {
                "file": str(file_path),
                "processed_at": datetime.now().isoformat(),
                "word_count": word_count,
                "line_count": line_count,
                "confidence_score": round(confidence, 3),
                "features": {
                    "has_frontmatter": has_frontmatter,
                    "has_headers": has_headers,
                    "has_code": has_code,
                },
            }

            print(f"✅ PROCESSED: {file_path.name}")
            print(f"   📊 Words: {word_count}, Confidence: {confidence:.3f}")
            print(f"   🎯 Features: Headers={has_headers}, Code={has_code}")

            # Save result
            results_dir = Path("D:/Projects/PAKE_SYSTEM/data")
            results_dir.mkdir(exist_ok=True)

            results_file = results_dir / "simple_processing_results.json"

            # Load existing results
            if results_file.exists():
                with open(results_file) as f:
                    all_results = json.load(f)
            else:
                all_results = []

            # Add new result
            all_results.append(result)

            # Save results
            with open(results_file, "w") as f:
                json.dump(all_results, f, indent=2)

            # Mark as processed
            self.processed.add(str(file_path))

            print(f"💾 SAVED: Processing result for {file_path.name}")
            print("=" * 50)

        except Exception as e:
            print(f"❌ ERROR processing {file_path.name}: {e}")


def main():
    vault_path = "D:/Knowledge-Vault"

    print("🚀 PAKE Simple Automation Starting...")
    print(f"📂 Monitoring: {vault_path}")
    print("=" * 50)

    # Create handler
    handler = SimpleAutomationHandler(vault_path)

    # Set up observer
    observer = Observer()
    observer.schedule(handler, vault_path, recursive=True)

    # Process existing files
    print("🔍 Processing existing files...")
    for md_file in Path(vault_path).rglob("*.md"):
        if not any(part.startswith(".") for part in md_file.parts):
            handler.process_file(md_file)

    # Start monitoring
    observer.start()
    print("👀 MONITORING ACTIVE - Add files to see automation in action!")
    print("Press Ctrl+C to stop...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping automation...")
        observer.stop()

    observer.join()
    print("✅ Automation stopped.")


if __name__ == "__main__":
    main()
