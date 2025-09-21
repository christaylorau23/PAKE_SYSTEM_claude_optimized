#!/usr/bin/env python3
"""
PAKE Automation Test - Working Version
Tests the automation system without encoding issues
"""

import json
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class WorkingAutomationHandler(FileSystemEventHandler):
    """Working file handler for automation testing"""

    def __init__(self, vault_path):
        self.vault_path = Path(vault_path)
        self.processed = set()
        print(f"Automation handler initialized for: {vault_path}")

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix == ".md":
            print(f"DETECTED NEW FILE: {file_path.name}")
            self.process_file(file_path)

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix == ".md" and str(file_path) not in self.processed:
            print(f"DETECTED MODIFIED FILE: {file_path.name}")
            self.process_file(file_path)

    def process_file(self, file_path):
        """Process and analyze file"""
        try:
            print(f"PROCESSING: {file_path.name}")

            # Read file content
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Analyze content
            word_count = len(content.split())
            line_count = len(content.splitlines())
            has_frontmatter = content.startswith("---")
            has_headers = "#" in content
            has_code = "```" in content
            has_lists = any(
                line.strip().startswith(("-", "*", "1."))
                for line in content.splitlines()
            )

            # Calculate confidence score
            confidence = 0.2  # Base score
            if word_count > 50:
                confidence += 0.1
            if word_count > 100:
                confidence += 0.2
            if word_count > 200:
                confidence += 0.1
            if has_headers:
                confidence += 0.2
            if has_code:
                confidence += 0.1
            if has_lists:
                confidence += 0.1
            if has_frontmatter:
                confidence += 0.1
            confidence = min(confidence, 1.0)

            # Create processing result
            result = {
                "file": file_path.name,
                "full_path": str(file_path),
                "processed_at": datetime.now().isoformat(),
                "analysis": {
                    "word_count": word_count,
                    "line_count": line_count,
                    "confidence_score": round(confidence, 3),
                    "features": {
                        "has_frontmatter": has_frontmatter,
                        "has_headers": has_headers,
                        "has_code": has_code,
                        "has_lists": has_lists,
                    },
                },
            }

            # Display results
            print(f"SUCCESS: {file_path.name} processed!")
            print(f"  Words: {word_count}")
            print(f"  Confidence: {confidence:.3f}")
            print(
                f"  Features: Headers={has_headers}, Code={has_code}, Lists={
                    has_lists
                }",
            )

            # Save processing result
            self.save_result(result)

            # Mark as processed
            self.processed.add(str(file_path))

            print(f"SAVED: Processing complete for {file_path.name}")
            print("-" * 50)

        except Exception as e:
            print(f"ERROR processing {file_path.name}: {e}")

    def save_result(self, result):
        """Save processing result to file"""
        try:
            results_dir = Path("D:/Projects/PAKE_SYSTEM/data")
            results_dir.mkdir(exist_ok=True)

            results_file = results_dir / "automation_test_results.json"

            # Load existing results
            if results_file.exists():
                with open(results_file) as f:
                    all_results = json.load(f)
            else:
                all_results = []

            # Add new result
            all_results.append(result)

            # Save updated results
            with open(results_file, "w") as f:
                json.dump(all_results, f, indent=2)

        except Exception as e:
            print(f"ERROR saving result: {e}")


def test_single_file():
    """Test processing a single file"""
    print("TESTING SINGLE FILE PROCESSING...")

    test_file = Path("D:/Knowledge-Vault/00-Inbox/ultra-automation-test.md")
    if test_file.exists():
        handler = WorkingAutomationHandler("D:/Knowledge-Vault")
        handler.process_file(test_file)
        print("Single file test completed.")
    else:
        print("Test file not found, creating it...")

        test_content = """---
title: "Automation Test"
tags: ["test", "automation"]
---

# Test File

This is a test of the PAKE automation system.

## Features
- Automatic detection
- Content analysis
- Confidence scoring

```python
print("automation working")
```

End of test file.
"""

        test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        print(f"Created test file: {test_file}")
        handler = WorkingAutomationHandler("D:/Knowledge-Vault")
        handler.process_file(test_file)


def start_monitoring():
    """Start continuous file monitoring"""
    vault_path = "D:/Knowledge-Vault"

    print("PAKE AUTOMATION STARTING...")
    print(f"Monitoring: {vault_path}")
    print("=" * 40)

    # Test single file first
    test_single_file()

    print("\nStarting continuous monitoring...")
    print("Add or modify .md files to see automation in action!")

    # Create handler and observer
    handler = WorkingAutomationHandler(vault_path)
    observer = Observer()
    observer.schedule(handler, vault_path, recursive=True)

    # Start monitoring
    observer.start()
    print("MONITORING ACTIVE!")
    print("Press Ctrl+C to stop...")

    try:
        counter = 0
        while True:
            time.sleep(5)
            counter += 1
            if counter % 12 == 0:  # Every minute
                print(f"Monitoring active... ({counter // 12} minutes)")
    except KeyboardInterrupt:
        print("\nStopping automation...")
        observer.stop()

    observer.join()
    print("Automation stopped.")


if __name__ == "__main__":
    start_monitoring()
