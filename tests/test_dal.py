#!/usr/bin/env python3

"""
Test script for PAKE System Data Access Layer and NoteRepository
Tests the Python DAL integration and filesystem operations
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
    print("🧪 Testing PAKE Data Access Layer Implementation...\n")

    # Create temporary vault for testing
    temp_vault = tempfile.mkdtemp(prefix="pake_test_vault_")

    try:
        # Test 1: DAL Initialization
        print("1️⃣ Testing DAL Initialization...")
        dal = get_dal(vault_path=temp_vault)
        await dal.initialize()
        print("   ✅ DAL initialized successfully")

        # Test 2: Repository Creation and Registration
        print("\n2️⃣ Testing Repository Registration...")
        note_repo = NoteRepository(vault_path=temp_vault)
        registered_repo = dal.register_repository("notes", note_repo)
        print("   ✅ NoteRepository registered successfully")

        # Test 3: Repository Retrieval
        print("\n3️⃣ Testing Repository Retrieval...")
        retrieved_repo = dal.get_repository("notes")
        print("   ✅ Repository retrieved successfully")
        print(f"   📊 Repository type: {retrieved_repo.__class__.__name__}")

        # Test 4: Note Creation
        print("\n4️⃣ Testing Note Creation...")
        test_note_data = {
            "title": "Test Note for DAL",
            "content": "This is a test note created by the DAL test suite.",
            "type": "secure_default_value",
            "location": "inbox",
        }

        created_note = note_repo.create_note(
            content=test_note_data["content"],
            title=test_note_data["title"],
            note_type=test_note_data["type"],
            location=test_note_data["location"],
        )
        print("   ✅ Note created successfully")
        print(f"   📊 Note ID: {created_note['id']}")
        print(f"   📊 File path: {created_note['file_path']}")

        # Test 5: Note Retrieval by ID
        print("\n5️⃣ Testing Note Retrieval...")
        retrieved_note = note_repo.get_note_by_id(created_note["id"])
        print("   ✅ Note retrieved by ID successfully")
        print(f"   📊 From cache: {retrieved_note.get('from_cache', False)}")
        print(
            f"   📊 Title matches: {
                retrieved_note['title'] == test_note_data['title']
            }",
        )

        # Test 6: Note Update
        print("\n6️⃣ Testing Note Update...")
        update_data = {
            "content": "This note has been updated by the test suite.",
            "title": "Updated Test Note",
        }

        updated_note = note_repo.update_note(created_note["id"], update_data)
        print("   ✅ Note updated successfully")
        print(f"   📊 Title updated: {updated_note['title'] == update_data['title']}")

        # Test 7: Notes List Retrieval
        print("\n7️⃣ Testing Notes List Retrieval...")
        notes_result = note_repo.get_notes_by_location("inbox", limit=10)
        print("   ✅ Notes list retrieved successfully")
        print(f"   📊 Total notes found: {len(notes_result['notes'])}")
        print(f"   📊 From cache: {notes_result.get('from_cache', False)}")

        # Test 8: Search Functionality
        print("\n8️⃣ Testing Search Functionality...")
        search_results = note_repo.search_notes("test suite", limit=5)
        print("   ✅ Search completed successfully")
        print(f"   📊 Search results count: {len(search_results)}")

        # Test 9: Repository Statistics
        print("\n9️⃣ Testing Repository Statistics...")
        stats = note_repo.get_stats()
        print("   ✅ Statistics retrieved successfully")
        print(f"   📊 Total notes: {stats['total_notes']}")
        print(f"   📊 By location: {stats['by_location']}")
        print(f"   📊 Cache size: {stats['cache_info']['size']}")

        # Test 10: Repository Health Check
        print("\n🔟 Testing Repository Health Check...")
        repo_health = note_repo.health_check()
        print("   ✅ Repository health check completed")
        print(f"   📊 Status: {repo_health['status']}")

        # Test 11: DAL Health Check
        print("\n1️⃣1️⃣ Testing DAL Health Check...")
        dal_health = await dal.health_check()
        print("   ✅ DAL health check completed")
        print(f"   📊 Overall status: {dal_health['status']}")
        print(f"   📊 DAL initialized: {dal_health['dal']['initialized']}")

        # Test 12: DAL Statistics
        print("\n1️⃣2️⃣ Testing DAL Statistics...")
        dal_stats = dal.get_stats()
        print("   ✅ DAL statistics retrieved")
        print(f"   📊 Registered repositories: {dal_stats['dal']['repositories']}")

        # Test 13: Cache Key Generation
        print("\n1️⃣3️⃣ Testing Cache Key Generation...")
        cache_key1 = dal.generate_cache_key("notes", "user123", "inbox")
        cache_key2 = dal.generate_cache_key("search", "test query", 10)
        print("   ✅ Cache keys generated successfully")
        print(f"   📊 Key 1: {cache_key1}")
        print(f"   📊 Key 2: {cache_key2}")

        # Test 14: Error Handling
        print("\n1️⃣4️⃣ Testing Error Handling...")
        try:
            dal.get_repository("nonexistent")
            print("   ❌ Should have thrown error for nonexistent repository")
        except KeyError:
            print("   ✅ Correctly threw error for nonexistent repository")

        # Test 15: Note Deletion
        print("\n1️⃣5️⃣ Testing Note Deletion...")
        deletion_result = note_repo.delete_note(created_note["id"])
        print(f"   ✅ Note deletion: {deletion_result}")

        # Verify deletion
        deleted_note = note_repo.get_note_by_id(created_note["id"])
        print(f"   📊 Note deleted successfully: {deleted_note is None}")

        print("\n🎉 All DAL and Repository tests completed successfully!")

        print("\n📊 Final Summary:")
        print(
            f"   - DAL Status: {'Initialized' if dal.is_initialized else 'Not Initialized'}",
        )
        print(f"   - Registered Repositories: {len(dal.repositories)}")
        print(f"   - Repository Health: {repo_health['status']}")
        print("   - Total Test Notes Created: 1")
        print(f"   - Vault Path: {temp_vault}")

    except Exception as error:
        print(f"\n❌ Test Failed: {str(error)}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        try:
            print("\n🧹 Cleaning up...")

            # Clear repository cache
            note_repo.clear_cache()
            print("   ✅ Repository cache cleared")

            # Clean up DAL
            await dal.cleanup()
            print("   ✅ DAL cleanup completed")

            # Remove temporary vault
            shutil.rmtree(temp_vault, ignore_errors=True)
            print("   ✅ Temporary vault removed")

        except Exception as cleanup_error:
            print(f"   ❌ Cleanup error: {str(cleanup_error)}")

    return True


def test_note_repository_standalone():
    """Test NoteRepository without DAL"""
    print("\n🔬 Testing NoteRepository Standalone...")

    # Create temporary vault for testing
    temp_vault = tempfile.mkdtemp(prefix="pake_standalone_test_")

    try:
        # Test standalone repository
        repo = NoteRepository(vault_path=temp_vault)

        # Create test note
        note = repo.create_note(
            content="Standalone test note content",
            title="Standalone Test",
            note_type="secure_default_value",
        )

        print(f"   ✅ Standalone note created: {note['title']}")

        # Test retrieval
        retrieved = repo.get_note_by_id(note["id"])
        print(f"   ✅ Standalone note retrieved: {retrieved is not None}")

        # Clean up
        repo.delete_note(note["id"])
        print("   ✅ Standalone note deleted")

        return True

    except Exception as error:
        print(f"   ❌ Standalone test failed: {str(error)}")
        return False

    finally:
        shutil.rmtree(temp_vault, ignore_errors=True)


async def main():
    """Run all tests"""
    print("🚀 Starting PAKE System DAL Test Suite\n")

    # Test 1: DAL and Repository Integration
    dal_success = await test_dal_and_repository()

    # Test 2: Standalone Repository
    standalone_success = test_note_repository_standalone()

    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUITE SUMMARY")
    print("=" * 60)
    print(f"DAL Integration Tests: {'✅ PASSED' if dal_success else '❌ FAILED'}")
    print(
        f"Standalone Repository Tests: {
            '✅ PASSED' if standalone_success else '❌ FAILED'
        }",
    )

    overall_success = dal_success and standalone_success
    print(
        f"\nOverall Result: {
            '🎉 ALL TESTS PASSED' if overall_success else '💥 SOME TESTS FAILED'
        }",
    )

    return 0 if overall_success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Test suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
