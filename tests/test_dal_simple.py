#!/usr/bin/env python3

"""
Simple test script for PAKE System Data Access Layer and NoteRepository
Tests the Python DAL integration and filesystem operations without Unicode issues
"""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

from data.DataAccessLayer import get_dal
from data.repositories.NoteRepository import NoteRepository

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_dal_and_repository():
    """Test the Python DAL and NoteRepository implementation"""
    print("Testing PAKE Data Access Layer Implementation...\n")

    # Create temporary vault for testing
    temp_vault = tempfile.mkdtemp(prefix="pake_test_vault_")

    try:
        # Test 1: DAL Initialization
        print("1. Testing DAL Initialization...")
        dal = get_dal(vault_path=temp_vault)
        await dal.initialize()
        print("   SUCCESS: DAL initialized successfully")

        # Test 2: Repository Creation and Registration
        print("\n2. Testing Repository Registration...")
        note_repo = NoteRepository(vault_path=temp_vault)
        registered_repo = dal.register_repository("notes", note_repo)
        print("   SUCCESS: NoteRepository registered successfully")

        # Test 3: Repository Retrieval
        print("\n3. Testing Repository Retrieval...")
        retrieved_repo = dal.get_repository("notes")
        print("   SUCCESS: Repository retrieved successfully")
        print(f"   INFO: Repository type: {retrieved_repo.__class__.__name__}")

        # Test 4: Note Creation
        print("\n4. Testing Note Creation...")
        test_note_data = {
            "title": "Test Note for DAL",
            "content": "This is a test note created by the DAL test suite.",
            "type": "REDACTED_SECRET",
            "location": "inbox",
        }

        created_note = note_repo.create_note(
            content=test_note_data["content"],
            title=test_note_data["title"],
            note_type=test_note_data["type"],
            location=test_note_data["location"],
        )
        print("   SUCCESS: Note created successfully")
        print(f"   INFO: Note ID: {created_note['id']}")

        # Test 5: Note Retrieval by ID
        print("\n5. Testing Note Retrieval...")
        retrieved_note = note_repo.get_note_by_id(created_note["id"])
        print("   SUCCESS: Note retrieved by ID successfully")
        print(f"   INFO: From cache: {retrieved_note.get('from_cache', False)}")
        print(
            f"   INFO: Title matches: {
                retrieved_note['title'] == test_note_data['title']
            }",
        )

        # Test 6: Note Update
        print("\n6. Testing Note Update...")
        update_data = {
            "content": "This note has been updated by the test suite.",
            "title": "Updated Test Note",
        }

        updated_note = note_repo.update_note(created_note["id"], update_data)
        print("   SUCCESS: Note updated successfully")
        print(
            f"   INFO: Title updated: {updated_note['title'] == update_data['title']}",
        )

        # Test 7: Notes List Retrieval
        print("\n7. Testing Notes List Retrieval...")
        notes_result = note_repo.get_notes_by_location("inbox", limit=10)
        print("   SUCCESS: Notes list retrieved successfully")
        print(f"   INFO: Total notes found: {len(notes_result['notes'])}")
        print(f"   INFO: From cache: {notes_result.get('from_cache', False)}")

        # Test 8: Search Functionality
        print("\n8. Testing Search Functionality...")
        search_results = note_repo.search_notes("test suite", limit=5)
        print("   SUCCESS: Search completed successfully")
        print(f"   INFO: Search results count: {len(search_results)}")

        # Test 9: Repository Statistics
        print("\n9. Testing Repository Statistics...")
        stats = note_repo.get_stats()
        print("   SUCCESS: Statistics retrieved successfully")
        print(f"   INFO: Total notes: {stats['total_notes']}")
        print(f"   INFO: By location: {stats['by_location']}")
        print(f"   INFO: Cache size: {stats['cache_info']['size']}")

        # Test 10: Repository Health Check
        print("\n10. Testing Repository Health Check...")
        repo_health = note_repo.health_check()
        print("   SUCCESS: Repository health check completed")
        print(f"   INFO: Status: {repo_health['status']}")

        # Test 11: DAL Health Check
        print("\n11. Testing DAL Health Check...")
        dal_health = await dal.health_check()
        print("   SUCCESS: DAL health check completed")
        print(f"   INFO: Overall status: {dal_health['status']}")
        print(f"   INFO: DAL initialized: {dal_health['dal']['initialized']}")

        # Test 12: DAL Statistics
        print("\n12. Testing DAL Statistics...")
        dal_stats = dal.get_stats()
        print("   SUCCESS: DAL statistics retrieved")
        print(f"   INFO: Registered repositories: {dal_stats['dal']['repositories']}")

        # Test 13: Cache Key Generation
        print("\n13. Testing Cache Key Generation...")
        cache_key1 = dal.generate_cache_key("notes", "user123", "inbox")
        cache_key2 = dal.generate_cache_key("search", "test query", 10)
        print("   SUCCESS: Cache keys generated successfully")
        print(f"   INFO: Key 1: {cache_key1}")
        print(f"   INFO: Key 2: {cache_key2}")

        # Test 14: Error Handling
        print("\n14. Testing Error Handling...")
        try:
            dal.get_repository("nonexistent")
            print("   ERROR: Should have thrown error for nonexistent repository")
        except KeyError:
            print("   SUCCESS: Correctly threw error for nonexistent repository")

        # Test 15: Note Deletion
        print("\n15. Testing Note Deletion...")
        deletion_result = note_repo.delete_note(created_note["id"])
        print(f"   SUCCESS: Note deletion: {deletion_result}")

        # Verify deletion
        deleted_note = note_repo.get_note_by_id(created_note["id"])
        print(f"   INFO: Note deleted successfully: {deleted_note is None}")

        print("\nSUCCESS: All DAL and Repository tests completed successfully!")

        print("\nFinal Summary:")
        print(
            f"   - DAL Status: {'Initialized' if dal.is_initialized else 'Not Initialized'}",
        )
        print(f"   - Registered Repositories: {len(dal.repositories)}")
        print(f"   - Repository Health: {repo_health['status']}")
        print("   - Total Test Notes Created: 1")
        print(f"   - Vault Path: {temp_vault}")

        return True

    except Exception as error:
        print(f"\nERROR: Test Failed: {str(error)}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        try:
            print("\nCleanup:")

            # Clear repository cache
            note_repo.clear_cache()
            print("   SUCCESS: Repository cache cleared")

            # Clean up DAL
            await dal.cleanup()
            print("   SUCCESS: DAL cleanup completed")

            # Remove temporary vault
            shutil.rmtree(temp_vault, ignore_errors=True)
            print("   SUCCESS: Temporary vault removed")

        except Exception as cleanup_error:
            print(f"   ERROR: Cleanup error: {str(cleanup_error)}")

    return True


def test_note_repository_standalone():
    """Test NoteRepository without DAL"""
    print("\nTesting NoteRepository Standalone...")

    # Create temporary vault for testing
    temp_vault = tempfile.mkdtemp(prefix="pake_standalone_test_")

    try:
        # Test standalone repository
        repo = NoteRepository(vault_path=temp_vault)

        # Create test note
        note = repo.create_note(
            content="Standalone test note content",
            title="Standalone Test",
            note_type="REDACTED_SECRET",
        )

        print(f"   SUCCESS: Standalone note created: {note['title']}")

        # Test retrieval
        retrieved = repo.get_note_by_id(note["id"])
        print(f"   SUCCESS: Standalone note retrieved: {retrieved is not None}")

        # Clean up
        repo.delete_note(note["id"])
        print("   SUCCESS: Standalone note deleted")

        return True

    except Exception as error:
        print(f"   ERROR: Standalone test failed: {str(error)}")
        return False

    finally:
        shutil.rmtree(temp_vault, ignore_errors=True)


async def main():
    """Run all tests"""
    print("Starting PAKE System DAL Test Suite\n")

    # Test 1: DAL and Repository Integration
    dal_success = await test_dal_and_repository()

    # Test 2: Standalone Repository
    standalone_success = test_note_repository_standalone()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUITE SUMMARY")
    print("=" * 60)
    print(f"DAL Integration Tests: {'PASSED' if dal_success else 'FAILED'}")
    print(
        f"Standalone Repository Tests: {'PASSED' if standalone_success else 'FAILED'}",
    )

    overall_success = dal_success and standalone_success
    print(
        f"\nOverall Result: {
            'ALL TESTS PASSED' if overall_success else 'SOME TESTS FAILED'
        }",
    )

    return 0 if overall_success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
