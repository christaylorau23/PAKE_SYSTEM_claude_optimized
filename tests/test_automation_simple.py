#!/usr/bin/env python3
"""
PAKE System Automation Test - Simple Version
Tests the complete automation pipeline from note creation to analysis
"""

import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import frontmatter

# Add current directory to path
sys.path.append("scripts")

from automated_vault_watcher import (
    ConfidenceEngine,
    SimpleVectorEmbedding,
    VaultWatcher,
)


class SimpleAutomationTester:
    """Simple automation test suite for PAKE system"""

    def __init__(self):
        self.vault_path = Path("vault")
        self.test_results = {}

        # Initialize PAKE components
        self.confidence_engine = ConfidenceEngine()
        self.vector_engine = SimpleVectorEmbedding()

        print("PAKE System Automation Test Suite")
        print("=" * 50)

    async def test_components(self):
        """Test individual PAKE components"""
        print("\nTesting Component Functionality...")

        try:
            # Test content with good characteristics
            test_content = """# AI Automation System Test

            This is a comprehensive test of the automated processing system with multiple
            quality indicators that should result in a high confidence score.

            ## Features:
            - Multi-factor confidence analysis
            - Vector embedding generation
            - Knowledge graph integration
            - Automated metadata enhancement

            ## Code Example:
            ```python
            def calculate_score(content, metadata):
                return confidence_engine.analyze(content)
            ```

            ## References:
            - Link to related documents
            - Cross-references to other notes
            - Citations and sources
            """

            metadata = {
                "tags": ["automation", "ai", "testing", "knowledge-management"],
                "connections": ["ai-system", "automation-guide", "test-framework"],
                "source_uri": "arxiv.org/test-paper",
                "verification_status": "verified",
            }

            # Test confidence engine
            confidence_score = self.confidence_engine.calculate_confidence(
                test_content,
                metadata,
            )
            print(f"  Confidence Engine: {confidence_score:.3f}")

            # Test vector embedding
            embedding = self.vector_engine.create_embedding(test_content)
            print(f"  Vector Embedding: {len(embedding)} dimensions")

            self.test_results["component_tests"] = {
                "confidence_score": confidence_score,
                "vector_dimensions": len(embedding),
                "passed": confidence_score > 0.5 and len(embedding) == 128,
            }

            return True

        except Exception as e:
            print(f"  ERROR: Component test failed: {e}")
            self.test_results["component_tests"] = {"error": str(e)}
            return False

    async def test_note_creation(self):
        """Test creating and processing a new note"""
        print("\nTesting Note Creation and Processing...")

        try:
            # Create test note
            test_id = str(uuid.uuid4())[:8]
            test_content = f"""# Automated Test Note {test_id}

This is an automated test note to verify PAKE system processing.

## Test Parameters:
- Test ID: {test_id}
- Created: {datetime.now().isoformat()}
- Expected processing: Automatic detection and analysis

## Content Analysis Factors:
- Medium length content (should contribute to confidence)
- Structured with headers and lists
- Contains technical information
- Has code example below

### Code Example:
```python
def test_automation():
    return "system_working"
```

## Expected Results:
- Confidence score: 0.4-0.7
- Vector embedding: 128 dimensions
- Frontmatter updated with PAKE metadata
- Knowledge graph entry created

This note should trigger the automation system to:
1. Detect the new file
2. Calculate confidence score
3. Generate vector embedding
4. Update frontmatter with metadata
5. Add entry to knowledge graph
"""

            # Write to vault inbox
            inbox_path = self.vault_path / "00-Inbox"
            inbox_path.mkdir(exist_ok=True, parents=True)

            timestamp = datetime.now().strftime("%Y-%m-%d")
            filename = f"{timestamp}-test-{test_id}.md"
            note_path = inbox_path / filename

            with open(note_path, "w", encoding="utf-8") as f:
                f.write(test_content)

            print(f"  Created test note: {filename}")

            # Wait briefly for potential automation
            await asyncio.sleep(2)

            # Check if automated processing occurred
            with open(note_path, encoding="utf-8") as f:
                processed_content = f.read()

            try:
                parsed = frontmatter.loads(processed_content)
                metadata = parsed.metadata

                has_pake_id = "pake_id" in metadata
                has_confidence = "confidence_score" in metadata

                if has_pake_id:
                    print("  SUCCESS: Note was automatically processed!")
                    print(f"    PAKE ID: {metadata['pake_id'][:8]}...")
                    if has_confidence:
                        print(f"    Confidence: {metadata['confidence_score']:.3f}")
                    automation_active = True
                else:
                    print("  INFO: Note created but not automatically processed")
                    print("  INFO: This indicates automation system is not running")
                    automation_active = False

                self.test_results["note_creation"] = {
                    "note_created": True,
                    "automation_active": automation_active,
                    "has_pake_id": has_pake_id,
                    "confidence_score": metadata.get("confidence_score", None),
                    "note_path": str(note_path),
                }

                return note_path

            except Exception as e:
                print(f"  WARNING: Could not parse frontmatter: {e}")
                self.test_results["note_creation"] = {
                    "note_created": True,
                    "automation_active": False,
                    "parsing_error": str(e),
                }
                return note_path

        except Exception as e:
            print(f"  ERROR: Note creation failed: {e}")
            self.test_results["note_creation"] = {"error": str(e)}
            return None

    async def test_manual_processing(self, note_path):
        """Test manual processing using PAKE components"""
        print("\nTesting Manual Processing...")

        if not note_path or not note_path.exists():
            print("  ERROR: No test note available")
            return

        try:
            # Initialize vault watcher for manual processing
            watcher = VaultWatcher(str(self.vault_path))

            print("  Processing note manually...")
            start_time = time.time()

            # Process the file
            result = await watcher.process_file(note_path)

            processing_time = time.time() - start_time

            if result.error:
                print(f"  ERROR: Manual processing failed: {result.error}")
                self.test_results["manual_processing"] = {
                    "success": False,
                    "error": result.error,
                }
            else:
                print("  SUCCESS: Manual processing completed!")
                print(f"    PAKE ID: {result.pake_id[:8]}...")
                print(f"    Confidence: {result.confidence_score:.3f}")
                print(f"    Processing time: {result.processing_time:.2f}s")
                print(f"    Vector embedded: {result.vector_embedded}")
                print(f"    Knowledge graph updated: {result.knowledge_graph_updated}")

                self.test_results["manual_processing"] = {
                    "success": True,
                    "pake_id": result.pake_id,
                    "confidence_score": result.confidence_score,
                    "processing_time": result.processing_time,
                    "vector_embedded": result.vector_embedded,
                    "knowledge_graph_updated": result.knowledge_graph_updated,
                }

        except Exception as e:
            print(f"  ERROR: Manual processing test failed: {e}")
            self.test_results["manual_processing"] = {"error": str(e)}

    def check_data_files(self):
        """Check if data files are being created"""
        print("\nChecking Data Persistence...")

        try:
            # Check processing state
            state_file = Path("data/processing_state.json")
            if state_file.exists():
                with open(state_file) as f:
                    state_data = json.load(f)
                print(f"  Processing state file: {len(state_data)} files tracked")
            else:
                print("  Processing state file: Not found")

            # Check knowledge graph
            kg_file = Path("data/knowledge_graph.json")
            if kg_file.exists():
                with open(kg_file) as f:
                    kg_data = json.load(f)
                print(f"  Knowledge graph: {len(kg_data)} entries")
            else:
                print("  Knowledge graph: Not found")

            # Check vector storage
            vectors_dir = Path("data/vectors")
            if vectors_dir.exists():
                vector_files = list(vectors_dir.glob("*.json"))
                print(f"  Vector storage: {len(vector_files)} vector files")
            else:
                print("  Vector storage: Directory not found")

            self.test_results["data_persistence"] = {
                "state_file_exists": state_file.exists(),
                "kg_file_exists": kg_file.exists(),
                "vectors_dir_exists": vectors_dir.exists(),
                "vector_files_count": len(vector_files) if vectors_dir.exists() else 0,
            }

        except Exception as e:
            print(f"  ERROR: Data persistence check failed: {e}")
            self.test_results["data_persistence"] = {"error": str(e)}

    def check_automation_status(self):
        """Check automation system status"""
        print("\nChecking Automation System Status...")

        log_file = Path("logs/vault_automation.log")
        if log_file.exists():
            try:
                with open(log_file) as f:
                    lines = f.readlines()
                print(f"  Automation log: {len(lines)} log entries found")

                if lines:
                    print("  Recent log entries:")
                    for line in lines[-3:]:
                        print(f"    {line.strip()}")

                self.test_results["automation_status"] = {
                    "log_exists": True,
                    "log_entries": len(lines),
                }

            except Exception as e:
                print(f"  WARNING: Could not read log file: {e}")
                self.test_results["automation_status"] = {
                    "log_exists": True,
                    "read_error": str(e),
                }
        else:
            print("  Automation log: Not found")
            print("  INFO: Automation system may not have been started")
            self.test_results["automation_status"] = {"log_exists": False}

    def generate_report(self):
        """Generate test summary report"""
        print("\n" + "=" * 60)
        print("PAKE SYSTEM TEST REPORT")
        print("=" * 60)

        # Test Results Summary
        total_tests = 0
        passed_tests = 0

        print("\nTest Results:")

        # Component tests
        comp_test = self.test_results.get("component_tests", {})
        if comp_test.get("passed", False):
            print("  PASS - Component functionality")
            passed_tests += 1
        else:
            print("  FAIL - Component functionality")
        total_tests += 1

        # Note creation
        note_test = self.test_results.get("note_creation", {})
        if note_test.get("note_created", False):
            print("  PASS - Note creation")
            passed_tests += 1
        else:
            print("  FAIL - Note creation")
        total_tests += 1

        # Manual processing
        manual_test = self.test_results.get("manual_processing", {})
        if manual_test.get("success", False):
            print("  PASS - Manual processing")
            passed_tests += 1
        else:
            print("  FAIL - Manual processing")
        total_tests += 1

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(
            f"\nOverall Success Rate: {passed_tests}/{total_tests} ({
                success_rate:.1f}%)",
        )

        # System Status
        print("\nSystem Status:")
        automation_active = note_test.get("automation_active", False)
        if automation_active:
            print("  ACTIVE - Automation system is running")
        else:
            print("  INACTIVE - Automation system is not running")

        # Recommendations
        print("\nRecommendations:")
        if success_rate >= 80:
            print("  SUCCESS: PAKE system components are working correctly!")
        else:
            print("  WARNING: PAKE system needs attention")

        if not automation_active:
            print("  ACTION: Start automation system:")
            print("    python scripts/automated_vault_watcher.py")

        log_exists = self.test_results.get("automation_status", {}).get(
            "log_exists",
            False,
        )
        if not log_exists:
            print("  INFO: No automation log found - system may not have run")

        print("  INFO: Start API bridge:")
        print("    cd scripts && node obsidian_bridge.js")

        return self.test_results

    async def run_all_tests(self):
        """Run complete test suite"""
        print("Starting PAKE System Test Suite...")

        # Component tests
        await self.test_components()

        # Note creation test
        test_note = await self.test_note_creation()

        # Manual processing test
        await self.test_manual_processing(test_note)

        # Data persistence check
        self.check_data_files()

        # Automation status check
        self.check_automation_status()

        # Generate report
        return self.generate_report()


async def main():
    """Main test execution"""
    tester = SimpleAutomationTester()
    results = await tester.run_all_tests()

    # Save results
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nTest results saved to: test_results.json")


if __name__ == "__main__":
    asyncio.run(main())
